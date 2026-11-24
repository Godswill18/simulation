"""
dashboard.py - one self-contained HTML results dashboard (images embedded),
built only from the generated tables and figures. Opens in any browser offline.
"""
import base64, html, json, os
import pandas as pd

TITLE = ("Enhancing Data Availability and Transaction Response Time in Multi-Branch Core Banking "
         "Information Systems through SD-WAN Dynamic Path Selection")


def _img(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def _table(df, max_rows=60):
    return df.head(max_rows).to_html(index=False, border=0, classes="t", escape=True, na_rep="n/a")


def build(out_dir, runs, tables, figs):
    m = json.load(open(os.path.join(out_dir, "run_manifest.json")))
    g = runs.groupby(["condition", "treatment"])

    def v(cond, tr, col, nd=1):
        x = g.get_group((cond, tr))[col].mean()
        return "n/a" if pd.isna(x) else f"{x:,.{nd}f}"

    kpis = [
        ("Brownout p95 response time", f"{v('brownout','static','rt_p95_ms')} ms", f"{v('brownout','dps','rt_p95_ms')} ms"),
        ("Brownout SLA-compliant time (fault)", f"{v('brownout','static','fault_sla_compliant_time_pct')} %", f"{v('brownout','dps','fault_sla_compliant_time_pct')} %"),
        ("Blackout failover time", f"{v('blackout','static','failover_time_s_median',2)} s", f"{v('blackout','dps','failover_time_s_median',2)} s"),
        ("Blackout service availability (fault)", f"{v('blackout','static','fault_service_availability_pct',2)} %", f"{v('blackout','dps','fault_service_availability_pct',2)} %"),
        ("Transaction availability (all runs)", f"{runs[runs.treatment=='static'].txn_availability_pct.mean():.3f} %", f"{runs[runs.treatment=='dps'].txn_availability_pct.mean():.3f} %"),
        ("Steady 450 tps switches/branch-hour", f"{runs[(runs.condition=='steady')&(runs.load_tps==450)&(runs.treatment=='static')].switches_per_branch_hour.mean():.0f}", f"{runs[(runs.condition=='steady')&(runs.load_tps==450)&(runs.treatment=='dps')].switches_per_branch_hour.mean():.0f}"),
    ]
    cards = "".join(f"<div class='card'><div class='k'>{html.escape(k)}</div>"
                    f"<div class='row'><span class='s'>Static</span><b>{s}</b></div>"
                    f"<div class='row'><span class='d'>Dynamic</span><b>{d}</b></div></div>" for k, s, d in kpis)
    sections = [
        ("Response time", ["rt_p95", "rt_p99", "components"], ["response_time_by_load", "rt_components"]),
        ("Data availability", ["availability", "unavailable"], ["availability"]),
        ("Failover performance", ["failover", "ts_brownout", "ts_blackout", "monitor"], ["failover"]),
        ("Network performance", ["loss", "throughput", "switching"], ["network"]),
        ("Statistical tests", [], ["tests_confirmatory", "tests_H03", "hypothesis_decisions"]),
        ("Sensitivity analysis (supplementary, not part of the 80 runs)", ["sensitivity"], ["sensitivity"]),
    ]
    body = []
    for title, fkeys, tkeys in sections:
        body.append(f"<h2>{html.escape(title)}</h2>")
        for k in fkeys:
            if k in figs:
                body.append(f"<img src='{_img(figs[k])}' alt='{k}'>")
        for k in tkeys:
            if k in tables:
                body.append(f"<h3>{k.replace('_', ' ').capitalize()}</h3><div class='tw'>{_table(tables[k])}</div>")
    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>SD-WAN DPS simulation dashboard</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#fcfcfb;color:#0b0b0b}}
header{{background:#1f3a5f;color:#fff;padding:18px 24px}} header h1{{font-size:18px;margin:0 0 6px}}
.banner{{background:#fff4e5;border-left:4px solid #eda100;padding:10px 24px;font-size:13px}}
main{{padding:16px 24px;max-width:1200px;margin:auto}} h2{{border-bottom:2px solid #e4e3dd;padding-bottom:4px;margin-top:32px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}}
.card{{background:#fff;border:1px solid #e4e3dd;border-radius:8px;padding:12px}} .k{{font-size:12px;color:#52514e;margin-bottom:6px}}
.row{{display:flex;justify-content:space-between;font-size:14px;margin:2px 0}} .s{{color:#c4501f}} .d{{color:#1f63b8}}
img{{max-width:100%;border:1px solid #e4e3dd;border-radius:6px;margin:8px 0;background:#fff}}
.tw{{overflow-x:auto}} table.t{{border-collapse:collapse;font-size:12px;margin:6px 0 14px;background:#fff}}
table.t th{{background:#eef2f6;text-align:left;padding:5px 8px;border-bottom:1px solid #d5dbe2}}
table.t td{{padding:4px 8px;border-bottom:1px solid #eee}} footer{{font-size:12px;color:#52514e;padding:20px 24px}}
</style></head><body>
<header><h1>{html.escape(TITLE)}</h1><div>Results dashboard: Static vs Dynamic Path Selection, {m['runs']} runs, seed {m['master_seed']}</div></header>
<div class="banner"><b>Python model-based simulation results.</b> These values come from a simplified model of a multi-branch
banking network. They are not measurements from any bank's production network or from physical network devices.</div>
<main><h2>Headline results (mean of runs)</h2><div class="cards">{cards}</div>
{''.join(body)}</main>
<footer>Generated {m['generated']} by run_simulation.py (Python {m['python']}, numpy {m['numpy']}, pandas {m['pandas']}).
Run-level data: outputs/data/run_level_results.csv. Parameters: outputs/parameters.json.</footer></body></html>"""
    path = os.path.join(out_dir, "dashboard.html")
    open(path, "w", encoding="utf-8").write(page)
    print(f"Dashboard written to {path}")
    return path
