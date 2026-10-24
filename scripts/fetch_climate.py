"""Refresh rainfall statistics from free open APIs. Run by hand: python scripts/fetch_climate.py

The app never calls this: it stays offline and reads the CSVs in data/. Writes data/sources/:

nasa_power_rainfall.csv - NASA POWER daily corrected precipitation (PRECTOTCORR, MERRA-2 based, public
domain, no API key), one point per governorate, 1991-2020:
- power_annual_mm: mean calendar-year total. The 0.5 deg grid reads low in the highlands and several
  governorates share a cell, so annual totals in rainfall.csv come from stations, not from here.
- dry_ratio, wet_ratio: 10th and 90th percentile rain-season total (Sep-Aug) over the mean season.
  Ratios, so the grid's bias against station totals cancels. The "national (median)" row feeds the
  year multipliers in assumptions.csv.

ghcn_first_flush.csv - NOAA GHCN-Daily measured station days, 1991-2020: share of rain lost to a 1 mm
first-flush diverter that resets every rain day, sum(min(P, 1 mm)) / sum(P). Station days, because the
reanalysis has too many drizzle days and nearly doubles this figure.

Also writes data/et0.csv, read by the garden planner: mean monthly reference evapotranspiration per
governorate, FAO-56 Penman-Monteith (Allen et al. 1998, eq. 6) on NASA POWER daily max/min temperature,
solar radiation, humidity and 2 m wind, 1991-2020.
"""
import csv
import gzip
import io
import json
import math
import statistics
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sources"
URL = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters={params}&community=AG"
       "&latitude={lat}&longitude={lon}&start=19910101&end=20201231&format=JSON")
ET0_PARAMS = ["T2M_MAX", "T2M_MIN", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M"]
ET0_CSV = ROOT / "data" / "et0.csv"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
GHCN_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/{station}.csv.gz"
# Jordanian GHCN stations with 1991-2020 rain days. The record has gaps; a ratio over the reported days
# is unaffected by missing days as long as they are missing at random.
GHCN_STATIONS = {"JOM00040265": "Mafraq (King Hussein Air Base)"}
FLUSH_MM = 1.0  # first flush per rain event; IS 15998 gives 0.5 to 1 mm, IS 11082 0.5 to 2 mm

# Governorate -> (lat, lon). JMD station coordinates where the annual total comes from a JMD station,
# otherwise the town centre.
POINTS = {
    "Amman (west)": (32.013, 35.872),   # University of Jordan station
    "Amman (east)": (31.972, 35.992),   # Amman Civil Airport (Marka)
    "Zarqa": (32.072, 36.088),
    "Irbid": (32.556, 35.850),
    "Ajloun": (32.333, 35.752),
    "Jerash": (32.281, 35.899),
    "Balqa (Salt)": (32.039, 35.727),
    "Madaba": (31.716, 35.794),
    "Mafraq": (32.356, 36.259),         # King Hussein Air Base station
    "Karak": (31.270, 35.750),          # Rabba station
    "Tafilah": (30.837, 35.604),
    "Ma'an": (30.167, 35.783),          # Ma'an station
    "Aqaba": (29.532, 35.006),
}


def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=300) as resp:
                return resp.read()
        except OSError:
            if attempt == 3:
                raise
            time.sleep(5 * 2 ** attempt)


def fetch(lat, lon):
    return json.loads(get(URL.format(params="PRECTOTCORR", lat=lat, lon=lon)))["properties"]["parameter"]["PRECTOTCORR"]


def et0_day(tmax, tmin, rs, rh, u2, lat_deg, elev_m, doy):
    """FAO-56 Penman-Monteith reference ET in mm/day from daily weather (°C, MJ/m²/day, %, m/s)."""
    t = (tmax + tmin) / 2
    sat = lambda x: 0.6108 * math.exp(17.27 * x / (x + 237.3))  # kPa, eq. 11
    es = (sat(tmax) + sat(tmin)) / 2
    ea = es * rh / 100
    delta = 4098 * sat(t) / (t + 237.3) ** 2  # eq. 13
    gamma = 0.000665 * 101.3 * ((293 - 0.0065 * elev_m) / 293) ** 5.26  # eq. 7-8
    lat = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)  # eq. 23-25
    dec = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)
    ws = math.acos(-math.tan(lat) * math.tan(dec))
    ra = 24 * 60 / math.pi * 0.0820 * dr * (ws * math.sin(lat) * math.sin(dec)
                                             + math.cos(lat) * math.cos(dec) * math.sin(ws))  # eq. 21
    rso = (0.75 + 2e-5 * elev_m) * ra  # eq. 37
    rnl = 4.903e-9 * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (0.34 - 0.14 * math.sqrt(ea)) \
        * (1.35 * min(rs / rso, 1.0) - 0.35)  # eq. 39
    rn = 0.77 * rs - rnl  # eq. 38, 40; soil heat flux G = 0 for daily steps
    return (0.408 * delta * rn + gamma * 900 / (t + 273) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))


def monthly_et0(lat, lon):
    """Mean monthly ET0 in mm over 1991-2020. Days with any missing value are skipped."""
    d = json.loads(get(URL.format(params=",".join(ET0_PARAMS), lat=lat, lon=lon)))
    p, elev = d["properties"]["parameter"], d["geometry"]["coordinates"][2]
    per_day = {m: [] for m in range(1, 13)}
    for day in p["T2M_MAX"]:
        vals = [p[k][day] for k in ET0_PARAMS]
        if any(v <= -999 for v in vals):
            continue
        dt = date(int(day[:4]), int(day[4:6]), int(day[6:]))
        per_day[dt.month].append(et0_day(*vals, lat, elev, dt.timetuple().tm_yday))
    days_in = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return [round(statistics.fmean(per_day[m]) * days_in[m - 1], 1) for m in range(1, 13)]


def first_flush(station):
    """Flush loss over the station's unflagged 1991-2020 daily PRCP reports (tenths of mm)."""
    lost = total = 0.0
    days = 0
    for row in csv.reader(io.StringIO(gzip.decompress(get(GHCN_URL.format(station=station))).decode())):
        if row[2] == "PRCP" and not row[5] and "1991" <= row[1][:4] <= "2020":
            mm = int(row[3]) / 10
            lost += min(mm, FLUSH_MM)
            total += mm
            days += mm > 0
    return {"first_flush_fraction": round(lost / total, 3), "rain_days": days, "total_mm": round(total)}


def stats(daily):
    """daily: {'YYYYMMDD': mm}, negative = missing. Returns the derived columns for one point."""
    years, seasons = {}, {}
    for day, mm in daily.items():
        if mm < 0:
            raise ValueError(f"missing value on {day}")
        y, m = int(day[:4]), int(day[4:6])
        years[y] = years.get(y, 0.0) + mm
        season = y if m >= 9 else y - 1  # Sep-Aug, named by the starting year
        seasons[season] = seasons.get(season, 0.0) + mm
    full = [seasons[s] for s in sorted(seasons) if s + 1 in years and s in years]  # drop the two half seasons
    mean = statistics.fmean(full)
    deciles = statistics.quantiles(full, n=10)
    return {"power_annual_mm": round(statistics.fmean(years.values()), 1),
            "dry_ratio": round(deciles[0] / mean, 3), "wet_ratio": round(deciles[-1] / mean, 3),
            "seasons": len(full)}


def write(name, rows, source):
    path = OUT / name
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, [*rows[0], "period", "source", "retrieved"])
        w.writeheader()
        for row in rows:
            w.writerow(row | {"period": "1991-2020", "source": source, "retrieved": date.today().isoformat()})
    print(f"wrote {path.relative_to(ROOT)}", file=sys.stderr)


def main():
    OUT.mkdir(exist_ok=True)
    rows = []
    for gov, (lat, lon) in POINTS.items():
        rows.append({"governorate": gov, "lat": lat, "lon": lon, **stats(fetch(lat, lon))})
        print(rows[-1], file=sys.stderr)
    rows.append({"governorate": "national (median)", "lat": "", "lon": "", "power_annual_mm": "",
                 **{k: round(statistics.median(r[k] for r in rows), 3) for k in ("dry_ratio", "wet_ratio")},
                 "seasons": rows[0]["seasons"]})
    write("nasa_power_rainfall.csv", rows, "NASA POWER daily PRECTOTCORR")
    flush = [{"station": s, "name": name, **first_flush(s)} for s, name in GHCN_STATIONS.items()]
    write("ghcn_first_flush.csv", flush, "NOAA GHCN-Daily PRCP, unflagged reports")
    with ET0_CSV.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["governorate", *MONTHS, "source", "status"])
        for gov, (lat, lon) in POINTS.items():
            w.writerow([gov, *monthly_et0(lat, lon),
                        "FAO-56 Penman-Monteith on NASA POWER daily weather 1991-2020 (scripts/fetch_climate.py)",
                        "sourced"])
            print(f"et0 {gov}", file=sys.stderr)
    print(f"wrote {ET0_CSV.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
