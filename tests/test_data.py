"""Every CSV in data/: required columns, no blanks or duplicates, numbers in sane ranges, sources on every row."""
import pandas as pd
import pytest

import ramadi as r

TABLES = list(r.COLUMNS)


def raw(name):
    return pd.read_csv(r.DATA / name, dtype=str, keep_default_na=False, encoding="utf-8")


@pytest.mark.parametrize("name", TABLES)
def test_columns_present_no_blank_required_cells_no_duplicate_keys(name):
    df = raw(name)
    assert set(r.COLUMNS[name]) <= set(df.columns)
    blank = [(i + 2, c) for c in r.COLUMNS[name] for i, v in enumerate(df[c]) if not str(v).strip()]
    assert not blank, f"{name}: blank cells at (line, column) {blank}"
    keys = df[r.KEYS[name]]
    assert not keys.duplicated().any(), f"{name}: duplicate {keys[keys.duplicated()].tolist()}"


@pytest.mark.parametrize("name", TABLES)
def test_every_row_has_a_source_and_a_known_status(name):
    df = raw(name)
    statuses = {"verified", "sourced", "estimate", "unverified", "placeholder", "unknown"}
    assert (df["source"].str.strip() != "").all()
    bad = df.loc[~df["status"].isin(statuses), [r.KEYS[name], "status"]].values.tolist()
    assert not bad, f"{name}: unknown status {bad}"


def test_rainfall_in_sane_range():
    mm = r.read_table("rainfall.csv")["annual_mm"]
    assert mm.between(0, 1500).all(), mm[~mm.between(0, 1500)].tolist()


def test_monthly_shares_between_0_and_1_and_sum_to_1():
    s = r.read_table("monthly_share.csv")["share_of_annual_rain"]
    assert s.between(0, 1).all() and s.sum() == pytest.approx(1.0, abs=0.001)


def test_catalog_items_complete_and_priced_above_zero():
    cat = r.read_table("catalog.csv")
    assert (cat["price_jod"] > 0).all(), cat.loc[cat["price_jod"] <= 0, "item_id"].tolist()
    assert set(cat["budget_level"]) <= {"low", "full", "both"}
    for col in ("name_en", "name_ar", "unit"):
        assert (cat[col].str.strip() != "").all()


def test_every_plant_has_a_greywater_flag():
    plants = raw("plants.csv")
    assert plants["greywater_ok"].str.lower().isin(["true", "false"]).all()


def test_fractions_and_positives_in_assumptions():
    a = r.assumption_values(r.read_table("assumptions.csv"))
    for p in r.FRACTIONS + ["drip_efficiency"]:
        assert 0 <= a[p] <= 1, p
    for p in ("tanker_volume", "tanker_price", "diesel_co2", "grid_co2", "litres_per_shower", "litres_per_laundry_load"):
        assert a[p] > 0, p


def test_et0_and_humidity_in_physical_ranges():
    et0 = r.read_table("et0.csv")[r.MONTHS]
    rh = r.read_table("humidity.csv")[r.MONTHS]
    assert ((et0 > 0) & (et0 < 400)).all().all()  # mm per month; Jordan's July peaks near 260
    assert (et0[["Jun", "Jul", "Aug"]].mean(axis=1) > et0[["Dec", "Jan", "Feb"]].mean(axis=1)).all()
    assert ((rh > 0) & (rh <= 100)).all().all()


def test_soil_shares_add_up_and_ph_is_plausible():
    soil = r.read_table("soil.csv")
    total = soil["sand_pct"] + soil["silt_pct"] + soil["clay_pct"]
    assert total.between(97, 103).all() and soil["ph"].between(4, 10).all()
    assert set(soil["texture"]) <= set(r.SOIL_GROUPS)


def test_garden_plant_factors_in_fao_range():
    gp = r.read_table("garden_plants.csv")
    for col in ("kc_ini", "kc_mid", "kc_end"):
        assert gp[col].between(0, 1.3).all(), col
    assert (gp["canopy_m2"] > 0).all()
    assert set(gp["salt"]) <= {"tolerant", "moderately tolerant", "moderately sensitive", "sensitive"}
