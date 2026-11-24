#!/usr/bin/env python3
"""
make_diagrams.py - architecture, topology, workflow and flowchart figures.
Requires Graphviz (the `dot` program). The PNGs are already included, so this
is only needed if you want to edit a diagram:  python diagrams/make_diagrams.py
"""
import os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
NAVY, TEAL, AMBER, SLATE, LIGHT, RED = "#1f3a5f", "#2a7f7a", "#b7791f", "#4a5568", "#eef2f6", "#b83232"
BASE = f'''graph [fontname="Helvetica" fontsize=12 bgcolor="white" pad=0.3 nodesep=0.35 ranksep=0.45];
node [fontname="Helvetica" fontsize=11 style="filled,rounded" shape=box color="{NAVY}" fillcolor="{NAVY}" fontcolor="white" penwidth=1.2];
edge [fontname="Helvetica" fontsize=10 color="{SLATE}" fontcolor="{SLATE}" arrowsize=0.8];'''

D = {}

D["fig_dsr_stages"] = f'''digraph G {{ {BASE} rankdir=LR;
n1 [label="1. Problem\\nidentification\\n(Ch. 1)"]; n2 [label="2. Objectives &\\nrequirements\\n(Ch. 1, 3.2)" fillcolor="{TEAL}" color="{TEAL}"];
n3 [label="3. Design the\\nsimulation model\\n(Ch. 3.3-3.5)"]; n4 [label="4. Implement in\\nPython\\n(Ch. 4)" fillcolor="{TEAL}" color="{TEAL}"];
n5 [label="5. Verify &\\nvalidate model\\n(tests, Ch. 4)"]; n6 [label="6. Run 80-run\\nexperiment\\n(Ch. 3.6, 4)" fillcolor="{TEAL}" color="{TEAL}"];
n7 [label="7. Evaluate &\\ncommunicate\\n(Ch. 5-6)"];
n1->n2->n3->n4->n5->n6->n7; n7->n3 [label="iterate" style=dashed color="{AMBER}" fontcolor="{AMBER}" constraint=false];
}}'''

D["fig_topology"] = None   # drawn with matplotlib below

D["fig_architecture"] = f'''digraph G {{ {BASE} rankdir=TB; compound=true;
subgraph cluster_in {{ label="Inputs" style="rounded,filled" fillcolor="{LIGHT}" color="{NAVY}" fontcolor="{NAVY}";
  cfg [label="config.py\\nparameters, thresholds,\\nseed 2026"]; des [label="experiment.py\\n80-run design\\n(paired seeds)"]; }}
subgraph cluster_model {{ label="Simulation model (per run, per branch)" style="rounded,filled" fillcolor="#f7f7f5" color="{TEAL}" fontcolor="{TEAL}";
  cond [label="network.py: Conditions\\nP0-A, P0-B, P1, P2 schedule" fillcolor="{SLATE}" color="{SLATE}"];
  mon [label="monitor.py\\nprobes + SLA windows" fillcolor="{TEAL}" color="{TEAL}"];
  pol [label="Path policy\\nstatic failover | dynamic SLA" fillcolor="{TEAL}" color="{TEAL}"];
  txn [label="transactions.py\\nPoisson arrivals, queues,\\nloss, retransmission, timeout" fillcolor="{TEAL}" color="{TEAL}"];
  met [label="run.py\\nrun-level metrics,\\n3 availability measures"];
  cond->mon; cond->txn; mon->pol; pol->txn [label=" selected path"]; txn->met; pol->met; }}
subgraph cluster_out {{ label="Outputs" style="rounded,filled" fillcolor="{LIGHT}" color="{NAVY}" fontcolor="{NAVY}";
  csv [label="CSV datasets\\nrun-level, time series,\\nswitch events" fillcolor="{AMBER}" color="{AMBER}"];
  ana [label="analysis.py\\ntables + Wilcoxon/Holm"]; fig [label="figures.py\\ngraphs"]; dash [label="dashboard.html"]; }}
cfg->cond [lhead=cluster_model]; des->mon [lhead=cluster_model]; met->csv; csv->ana; csv->fig; ana->dash; fig->dash;
}}'''

D["fig_workflow"] = f'''digraph G {{ {BASE} rankdir=TB;
s [label="Start: python run_simulation.py" shape=box fillcolor="{SLATE}" color="{SLATE}"];
a [label="Load parameters and master seed (2026)"]; b [label="Build 80-run design\\n2 policies x 4 loads x (5 steady + 3 brownout + 2 blackout)"];
c [label="For each run: derive seed from (load, condition, repetition)\\nidentical for both policies"];
d [label="Pre-roll 30 s so monitors fill their windows"];
e [label="Run monitor and policy on a 0.2 s grid\\n-> selected-path timeline per branch" fillcolor="{TEAL}" color="{TEAL}"];
f [label="Generate Poisson transactions; send each attempt on the\\nselected path; apply delay, queueing, loss, retransmission" fillcolor="{TEAL}" color="{TEAL}"];
g [label="Fault schedule: P1 or P2 on Path A at 240-360 s\\n(180-300 s of the measurement window)" fillcolor="{AMBER}" color="{AMBER}"];
h [label="Discard 60 s warm-up; reduce 420 s window to run-level metrics"];
i [label="Write CSV: run-level results, per-second series, switch events"];
j [label="Analysis: aggregate, paired Wilcoxon + sign test, Holm"];
k [label="Figures + dashboard.html + results_workbook.xlsx" fillcolor="{SLATE}" color="{SLATE}"];
s->a->b->c->d->e->f->h->i->j->k; g->e [style=dashed color="{AMBER}"]; g->f [style=dashed color="{AMBER}"];
i->c [label=" next run" style=dashed constraint=false];
}}'''

D["fig_static_flow"] = f'''digraph G {{ {BASE} rankdir=TB;
s [label="Every 1 s: send reachability probe on Path A and Path B" fillcolor="{SLATE}" color="{SLATE}"];
r [label="Reply within 1 s?" shape=diamond style=filled fillcolor="{AMBER}" color="{AMBER}"];
ok [label="Count consecutive replies"]; lost [label="Count consecutive losses"];
dn [label="3 losses in a row?" shape=diamond style=filled fillcolor="{AMBER}" color="{AMBER}"];
up [label="3 replies in a row?" shape=diamond style=filled fillcolor="{AMBER}" color="{AMBER}"];
mdn [label="Mark path DOWN"]; mup [label="Mark path UP"];
q [label="Primary Path A UP?" shape=diamond style=filled fillcolor="{AMBER}" color="{AMBER}"];
ua [label="Send traffic on Path A\\n(even if slow, jittery or lossy)" fillcolor="{TEAL}" color="{TEAL}"];
q2 [label="Backup Path B UP?" shape=diamond style=filled fillcolor="{AMBER}" color="{AMBER}"];
ub [label="Fail over: traffic on Path B" fillcolor="{TEAL}" color="{TEAL}"];
none [label="No path: transactions wait for\\nretransmission or time out" fillcolor="{RED}" color="{RED}"];
s->r; r->ok [label="yes"]; r->lost [label="no"]; ok->up; lost->dn; dn->mdn [label="yes"]; up->mup [label="yes"];
dn->q [label="no"]; up->q [label="no"]; mdn->q; mup->q;
q->ua [label="yes"]; q->q2 [label="no"]; q2->ub [label="yes"]; q2->none [label="no"];
}}'''

D["fig_dps_flow"] = f'''digraph G {{ {BASE} rankdir=TB;
s [label="Every 0.2 s: send SLA probe on Path A and Path B" fillcolor="{SLATE}" color="{SLATE}"];
k [label="Result known when the reply arrives\\nor after the 0.5 s probe timeout"];
w [label="Update per path:\\nlatency = mean RTT, last 30 probes\\njitter = mean |RTT change|, last 30\\nloss = % lost, last 100\\nDEAD after 5 losses / ALIVE after 10 replies"];
a [label="Path A alive AND latency <= 60 ms\\nAND jitter <= 10 ms AND loss <= 1 %?" shape=diamond style=filled fillcolor="{AMBER}" color="{AMBER}"];
ua [label="Traffic on Path A (preferred)" fillcolor="{TEAL}" color="{TEAL}"];
b [label="Path B in SLA?" shape=diamond style=filled fillcolor="{AMBER}" color="{AMBER}"];
ub [label="Steer traffic to Path B\\n(switch event logged)" fillcolor="{TEAL}" color="{TEAL}"];
c [label="Any path alive?" shape=diamond style=filled fillcolor="{AMBER}" color="{AMBER}"];
ul [label="Use first alive path in priority\\norder A, B (degraded, logged)"];
none [label="No path" fillcolor="{RED}" color="{RED}"];
s->k->w->a; a->ua [label="yes"]; a->b [label="no"]; b->ub [label="yes"]; b->c [label="no"]; c->ul [label="yes"]; c->none [label="no"];
ua->s [style=dashed label=" next probe" constraint=false];
}}'''

D["fig_sequence"] = None   # drawn with matplotlib below

D["fig_conceptual"] = f'''digraph G {{ {BASE} rankdir=LR;
iv [label="INDEPENDENT VARIABLE\\nPath-selection policy\\nStatic (with failover) vs Dynamic (SLA-based)"];
ctl [label="CONTROLLED FACTORS\\nTopology, path profiles, offered load,\\nmessage size, fault schedule, seeds" fillcolor="{AMBER}" color="{AMBER}"];
dv1 [label="PRIMARY DEPENDENT VARIABLES\\nTransaction response time (p95)\\nData availability: transaction, service,\\nSLA-compliant time" fillcolor="{TEAL}" color="{TEAL}"];
dv2 [label="SECONDARY MEASURES\\nLatency, jitter, message loss, throughput,\\nfailover / recovery / fail-back time,\\npath-switching frequency" fillcolor="{SLATE}" color="{SLATE}"];
ism [label="DeLone & McLean constructs\\nsystem quality, information quality,\\nservice quality" fillcolor="white" fontcolor="{NAVY}"];
iv->dv1 [label=" affects"]; iv->dv2 [label=" affects" style=dashed]; ctl->dv1 [label=" held constant" style=dashed color="{AMBER}" fontcolor="{AMBER}"];
dv1->ism [label=" indicators of" style=dotted]; }}'''


def sequence(path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=200)
    lanes = ["Branch client", "Branch edge\n(path policy)", "Selected WAN path\n(A or B)", "HQ edge", "Core banking\nservice"]
    xs = [0.8, 2.8, 4.8, 6.8, 8.8]
    for x, l in zip(xs, lanes):
        ax.add_patch(plt.Rectangle((x - 0.8, 9.2), 1.6, 0.7, color=NAVY))
        ax.text(x, 9.55, l, color="white", ha="center", va="center", fontsize=8.5)
        ax.plot([x, x], [0.4, 9.2], color="#b5b4ad", linestyle=":", linewidth=1)
    msgs = [(0, 1, 8.6, "1. request (ISO 8583-style 0200)"), (1, 1, 8.0, "2. look up path selected at send time"),
            (1, 2, 7.3, "3. queue + serialise + delay D + jitter; lost w.p. L"), (2, 3, 6.6, "4. arrives at HQ"),
            (3, 4, 5.9, "5. hand to service"), (4, 4, 5.2, "6. processing time P (lognormal)"),
            (4, 3, 4.5, "7. response (0210)"), (3, 2, 3.8, "8. HQ queue + delay; lost w.p. L"),
            (2, 1, 3.1, "9. arrives at branch"), (1, 0, 2.4, "10. response received")]
    for a, b, y, t in msgs:
        if a == b:
            ax.annotate("", xy=(xs[a] + 0.35, y - 0.25), xytext=(xs[a] + 0.02, y + 0.05),
                        arrowprops=dict(arrowstyle="->", color=TEAL, connectionstyle="arc3,rad=-0.6"))
            ax.text(xs[a] + 0.45, y - 0.05, t, fontsize=8, color=SLATE, va="center")
        else:
            ax.annotate("", xy=(xs[b], y), xytext=(xs[a], y), arrowprops=dict(arrowstyle="->", color=NAVY if b > a else TEAL, lw=1.3))
            ax.text((xs[a] + xs[b]) / 2, y + 0.12, t, fontsize=8, color=SLATE, ha="center")
    ax.annotate("", xy=(0.15, 2.4), xytext=(0.15, 8.6), arrowprops=dict(arrowstyle="<->", color=AMBER, lw=1.5))
    ax.text(0.1, 5.5, "response time RT", rotation=90, color=AMBER, ha="right", va="center", fontsize=9)
    ax.text(5.0, 1.3, "If the request or response is lost: retransmit after 0.25, 0.5, 1, 2, 4 s (each attempt uses the path selected then).\n"
            "Transaction fails if no response within 10 s.   RT = retransmission wait + d_up + P + d_down",
            ha="center", fontsize=8.3, color=INK if (INK := "#0b0b0b") else None)
    ax.set_xlim(-0.3, 10.9); ax.set_ylim(0.3, 10.1); ax.axis("off")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def topology(path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Ellipse
    fig, ax = plt.subplots(figsize=(11, 5.6), dpi=200)
    def box(x, y, w, h, text, fc, fs=9, tc="white"):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=fc))
        ax.text(x, y, text, ha="center", va="center", color=tc, fontsize=fs)
    ax.add_patch(FancyBboxPatch((0.1, 0.4), 3.3, 5.0, boxstyle="round,pad=0.02,rounding_size=0.2", fc=LIGHT, ec=NAVY))
    ax.text(1.75, 5.15, "Branches (simulated: 3)", ha="center", color=NAVY, fontsize=10, weight="bold")
    ax.add_patch(FancyBboxPatch((7.7, 1.6), 3.1, 2.6, boxstyle="round,pad=0.02,rounding_size=0.2", fc=LIGHT, ec=NAVY))
    ax.text(9.25, 3.95, "Headquarters data centre", ha="center", color=NAVY, fontsize=10, weight="bold")
    ys = [4.2, 2.9, 1.6]
    for i, y in enumerate(ys, 1):
        box(0.95, y, 1.4, 0.8, f"Tellers / ATM / POS\nPoisson load\n50-450 tps", TEAL, 7.5)
        box(2.55, y, 1.35, 0.8, f"Branch {i} edge\nmonitor +\npath policy", NAVY, 7.5)
        ax.annotate("", xy=(1.87, y), xytext=(1.66, y), arrowprops=dict(arrowstyle="<->", color=SLATE))
    box(8.5, 2.9, 1.2, 1.2, "HQ edge\n(downstream\nqueues)", NAVY, 8)
    box(9.95, 2.9, 1.3, 1.2, "Core banking\nservice\nprocessing P", TEAL, 8)
    ax.annotate("", xy=(9.3, 2.9), xytext=(9.1, 2.9), arrowprops=dict(arrowstyle="<->", color=SLATE))
    ax.add_patch(Ellipse((5.55, 4.1), 3.4, 1.5, fc=AMBER, ec=AMBER))
    ax.text(5.55, 4.1, "Path A: private, MPLS-like\n10 +/- 1 ms one way, 2.56 Mbit/s\nfaults injected here:\nP1 brownout | P2 blackout", ha="center", va="center", color="white", fontsize=8)
    ax.add_patch(Ellipse((5.55, 1.7), 3.4, 1.3, fc=SLATE, ec=SLATE))
    ax.text(5.55, 1.7, "Path B: broadband\n25 +/- 3 ms one way, 10.24 Mbit/s", ha="center", va="center", color="white", fontsize=8)
    for y in ys:
        ax.annotate("", xy=(3.9, 4.1), xytext=(3.23, y + 0.15), arrowprops=dict(arrowstyle="<->", color=AMBER, lw=1.2))
        ax.annotate("", xy=(3.9, 1.75), xytext=(3.23, y - 0.15), arrowprops=dict(arrowstyle="<->", color=SLATE, lw=1.2))
    ax.annotate("", xy=(7.9, 3.2), xytext=(7.2, 4.0), arrowprops=dict(arrowstyle="<->", color=AMBER, lw=1.6))
    ax.annotate("", xy=(7.9, 2.6), xytext=(7.2, 1.8), arrowprops=dict(arrowstyle="<->", color=SLATE, lw=1.6))
    ax.text(7.25, 0.6, "Each branch has its own Path A and Path B access link (one FIFO queue per direction).\n"
            "Python model of a simplified network: not a reproduction of any bank's infrastructure.",
            ha="center", fontsize=8, color=SLATE)
    ax.set_xlim(0, 11); ax.set_ylim(0.2, 5.5); ax.axis("off")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def main():
    for name, src in D.items():
        out = os.path.join(HERE, f"{name}.png")
        if name == "fig_topology":
            topology(out); continue
        if src is None:
            sequence(out)
            continue
        with open(os.path.join(HERE, f"{name}.dot"), "w") as f:
            f.write(src)
        subprocess.run(["dot", "-Tpng", "-Gdpi=200", "-o", out], input=src, text=True, check=True)
        print("wrote", out)


if __name__ == "__main__":
    main()
