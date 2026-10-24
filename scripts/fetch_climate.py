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
"""
import csv
import gzip
import io
import json
import statistics
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sources"
URL = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR&community=AG"
       "&latitude={lat}&longitude={lon}&start=19910101&end=20201231&format=JSON")
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
    return json.loads(get(URL.format(lat=lat, lon=lon)))["properties"]["parameter"]["PRECTOTCORR"]


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


if __name__ == "__main__":
    main()
