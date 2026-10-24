"""Ramadi-Cycle Streamlit interface. Run: streamlit run app.py"""
import inspect

import altair as alt
import pandas as pd
import streamlit as st

import ramadi as r

st.set_page_config(page_title="Ramadi-Cycle | رمادي", page_icon="assets/mark.svg", layout="wide")
st.markdown(
    """<style>
    [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
    .rc-rtl { direction: rtl; text-align: right; }
    .rc-badge { display:inline-block; padding:4px 10px; border-radius:4px; font-weight:600;
                background:#E3EBDD; color:#3F5222; border:1px solid #9CAF7A; }
    .rc-warn { border-left:3px solid #B5562B; padding:2px 0 2px 12px; margin:6px 0; }
    .rc-rtl .rc-warn { border-left:none; border-right:3px solid #B5562B; padding:2px 12px 2px 0; }
    </style>""",
    unsafe_allow_html=True,
)

rain, shares, catalog, plants, assumptions = r.load_tables()
a = r.assumption_values(assumptions)

# ---------------------------------------------------------------- sidebar

with st.sidebar:
    st.image("assets/logo.svg", width=180)
    gov = st.selectbox("Governorate", rain["governorate"], index=0)
    rain_mm = float(rain.set_index("governorate").at[gov, "annual_mm"])
    roof = st.slider("Roof area (m²)", 0, 400, 120, 10)
    people = st.slider("People in the household", 1, 12, 5)
    showers = st.slider("Showers per person per week", 0, 14, 5)
    laundry = st.slider("Laundry loads per week", 0, 14, 4)
    capacity = st.slider("Harvest tank capacity (m³)", 0.5, 10.0, 2.0, 0.5)
    budget = st.radio("Budget", ["low", "full"], format_func={"low": "Low-cost DIY", "full": "Full retrofit"}.get)
    year = st.radio("Year type", ["dry", "average", "wet"], index=1, horizontal=True)
    lang = st.radio("Blueprint language", ["en", "ar"], format_func={"en": "English", "ar": "العربية"}.get,
                    horizontal=True)
    models = r.list_models()
    model = st.selectbox("Local model", models) if models else None
    if not models:
        st.caption("Ollama is not running. Blueprints use the built-in template.")
    go = st.button("Generate blueprint", type="primary", width="stretch")

profile = {"governorate": gov, "rain_mm": rain_mm, "roof_m2": roof, "people": people, "showers_pp": showers,
           "laundry_loads": laundry, "capacity_m3": capacity, "year": year}
res = r.simulate(profile, shares, a)

# Plan inputs that change the blueprint; a stale plan is dropped when they change.
plan_key = (gov, roof, people, capacity, budget, lang)
if st.session_state.get("plan_key") != plan_key:
    st.session_state.pop("plan", None)
if go:
    with st.spinner(f"Asking {model} on this laptop…" if model else "Building template plan…"):
        bp, source, notes = r.generate(profile, res, catalog, plants, budget, lang, model)
    st.session_state.update(plan=(bp, source, notes, model), plan_key=plan_key)

# Payback uses the generated plan if there is one, otherwise the template plan for this budget.
plan_bp = st.session_state["plan"][0] if "plan" in st.session_state else r.template_blueprint(profile, budget, lang)
bom = r.price(plan_bp, catalog)
cost = bom["total_jod"].sum()
imp = r.impact(res["water"], cost, a)

# ---------------------------------------------------------------- metric row

st.markdown("### Ramadi-Cycle  <span style='color:#6B7175;font-weight:400'>رمادي</span>", unsafe_allow_html=True)
st.caption(f"{gov} · {rain_mm:.0f} mm/yr · {year} year · {roof} m² roof · {people} people")
c = st.columns(5)
c[0].metric("Water reused", f"{res['water']:.1f} m³/yr")
c[1].metric("Tanker trips avoided", f"{imp['trips']:.1f} /yr")
c[2].metric("Saved", f"{imp['jod']:.0f} JOD/yr")
c[3].metric("CO₂ cut", f"{imp['co2']:.0f} kg/yr")
c[4].metric("Payback", f"{imp['payback_months']:.0f} months" if imp["payback_months"] else "n/a",
            help=f"System cost {cost:.0f} JOD from the catalog")

impact_tab, plan_tab, method_tab, data_tab = st.tabs(["Impact", "Blueprint", "Safety & method", "Assumptions & sources"])

# ---------------------------------------------------------------- impact

with impact_tab:
    bal = res["balance"].set_index("month")
    month_x = alt.X("month:N", sort=r.MONTHS, title=None)  # keep Jan..Dec, not alphabetical
    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Harvest tank level by month (m³)**")
        st.altair_chart(alt.Chart(res["balance"]).mark_line(point=True, color="#1E5B7A")
                        .encode(month_x, alt.Y("level:Q", title=None)), width="stretch")
        st.markdown("**Non-potable demand: covered by rain vs still bought (m³)**")
        stacked = res["balance"].melt("month", ["met", "shortfall"], "source", "m3").replace(
            {"met": "From rain", "shortfall": "Still bought"})
        st.altair_chart(alt.Chart(stacked).mark_bar().encode(
            month_x, alt.Y("m3:Q", title=None),
            alt.Color("source:N", title=None, scale=alt.Scale(range=["#1E5B7A", "#C9C6BF"]),
                      legend=alt.Legend(orient="top"))), width="stretch")
        st.caption(f"{res['dry_months']} dry months · {res['overflow']:.1f} m³ overflow · "
                   f"roof potential {res['potential']:.1f} m³/yr, of which {res['rain_used']:.1f} m³ used. "
                   "Tank starts empty in January.")
    with right:
        st.markdown("**Sareef counter** · صهريج")
        after = st.toggle("With Ramadi-Cycle", value=True)
        demand = bal["demand"].sum() + res["greywater"]  # water these uses need today, all bought
        before = r.impact(demand, 0, a)
        now = r.impact(demand - res["water"], 0, a) if after else before
        st.metric("Tanker trips a year", f"{now['trips']:.1f}",
                  delta=f"{now['trips'] - before['trips']:.1f}" if after else None, delta_color="inverse")
        st.metric("JOD a year on this water", f"{now['jod']:.0f}",
                  delta=f"{now['jod'] - before['jod']:.0f}" if after else None, delta_color="inverse")
        st.metric("kg CO₂ a year", f"{now['co2']:.0f}",
                  delta=f"{now['co2'] - before['co2']:.0f}" if after else None, delta_color="inverse")
        st.caption("Covers toilet flushing, cleaning and garden water only. Drinking and cooking water are unchanged.")
        st.divider()
        homes = st.slider("Scale to homes in a neighbourhood", 1, 1000, 1)
        if homes > 1:
            st.write(f"{homes} homes: **{res['water'] * homes:,.0f} m³**, **{imp['trips'] * homes:,.0f}** tanker "
                     f"trips and **{imp['co2'] * homes / 1000:,.1f} t** CO₂ a year.")

# ---------------------------------------------------------------- blueprint

with plan_tab:
    if "plan" not in st.session_state:
        st.info("Set up the household in the sidebar, then press **Generate blueprint**.")
    else:
        bp, source, notes, used_model = st.session_state["plan"]
        checks = r.safety_checks(bp)
        passed = sum(ok for _, ok in checks)
        if source == "model":
            st.caption(f"Generated on this laptop by {used_model}. Prices and checks by code.")
        else:
            st.warning("Showing the built-in template plan. "
                       + ("The model output failed validation: " + "; ".join(notes) if notes else
                          "No local model was available."))
        st.markdown(f"<span class='rc-badge'>Safety checks passed: {passed} of {len(checks)}</span>",
                    unsafe_allow_html=True)

        rtl = "rc-rtl" if bp.language == "ar" else ""
        L = {"en": ("Rainwater", "Greywater", "Plants for greywater", "Safety rules"),
             "ar": ("مياه الأمطار", "المياه الرمادية", "نباتات تُسقى بالمياه الرمادية", "قواعد السلامة")}[bp.language]
        steps = lambda xs: "".join(f"<li>{x}</li>" for x in xs)
        st.markdown(
            f"<div class='{rtl}'><p>{bp.summary}</p>"
            f"<h4>{L[0]}</h4><ol>{steps(bp.rainwater_steps)}</ol>"
            f"<h4>{L[1]}</h4><ol>{steps(bp.greywater_steps)}</ol></div>",
            unsafe_allow_html=True)
        st.markdown("**Bill of materials** (catalog prices, unverified)")
        st.dataframe(bom, hide_index=True, width="stretch",
                     column_config={"unit_jod": st.column_config.NumberColumn("JOD each", format="%.0f"),
                                    "total_jod": st.column_config.NumberColumn("JOD", format="%.0f")})
        st.markdown(f"**Total: {cost:.0f} JOD**")
        pl = plants.set_index("plant_id")
        name_col = "name_ar" if bp.language == "ar" else "name_en"
        st.markdown(
            f"<div class='{rtl}'><h4>{L[2]}</h4><ul>"
            + "".join(f"<li><b>{pl.at[p.plant_id, name_col]}</b>: {p.reason}</li>" for p in bp.plants)
            + f"</ul><h4>{L[3]}</h4>"
            + "".join(f"<div class='rc-warn'>{w}</div>" for w in r.WARNINGS[bp.language])
            + f"<p><i>{r.DISCLAIMER[bp.language]}</i></p></div>",
            unsafe_allow_html=True)
        st.download_button("Download plan (.md)", r.to_markdown(bp, bom, profile, res),
                           file_name=f"ramadi-plan-{bp.language}.md", mime="text/markdown")

# ---------------------------------------------------------------- method

with method_tab:
    st.markdown("#### Who does what")
    st.table(pd.DataFrame({
        "Task": ["Rainfall, water balance, trips, JOD, CO₂, payback", "Prices and quantity limits",
                 "Safety warnings and banned terms", "Choosing catalog items, ordering steps, explaining why",
                 "Rejecting invalid or unsafe output"],
        "Done by": ["Python engine", "catalog.csv", "Hard-coded rules", "Local model", "Validation code"]}))
    st.markdown("#### Fixed rules")
    for w in r.WARNINGS["en"]:
        st.markdown(f"<div class='rc-warn'>{w}</div>", unsafe_allow_html=True)
    st.caption("Banned terms in model text: " + ", ".join(r.BANNED_TERMS))
    st.markdown("#### Formulas")
    st.latex(r"I_m = A \times (R \times s_m \times k) \times C \times (1 - f)")
    st.latex(r"L_m = \min\left(K,\; \max\left(0,\; L_{m-1} + I_m - D_m\right)\right)")
    st.latex(r"G_{week} = (P\,n_{shower}\,l_{shower} + n_{laundry}\,l_{laundry} + P\,l_{sink}) \times r")
    st.latex(r"\text{Trips} = \frac{W s}{T} \quad \text{JOD} = \text{Trips}\,p_{trip} + W(1-s)\,p_{tariff}")
    st.latex(r"\text{CO}_2 = \text{Trips}\,d_{trip}\,e_{diesel} + W\,E_{pump}\,e_{grid}")
    st.markdown("#### Output schema the model must match")
    st.code(inspect.getsource(r.PlanItem) + "\n" + inspect.getsource(r.PlantPick) + "\n"
            + inspect.getsource(r.Blueprint), language="python")
    st.markdown(f"#### Model\n{model or 'None running. Template plan only.'}  \nRuns through Ollama at "
                f"`{r.OLLAMA_URL}`. Nothing leaves this machine.")
    with st.expander("Prompt sent to the model"):
        st.code(r.build_prompt(profile, res, catalog, plants, budget, lang), language="text")

# ---------------------------------------------------------------- assumptions

with data_tab:
    st.markdown("Every constant the app uses. None is verified yet. Fix one with a pull request to `data/`.")
    st.dataframe(assumptions, hide_index=True, width="stretch")
    st.markdown("**Rainfall by governorate**")
    st.dataframe(rain, hide_index=True, width="stretch")
    st.markdown("**Catalog**")
    st.dataframe(catalog, hide_index=True, width="stretch")
    st.markdown("**Plants**")
    st.dataframe(plants, hide_index=True, width="stretch")
