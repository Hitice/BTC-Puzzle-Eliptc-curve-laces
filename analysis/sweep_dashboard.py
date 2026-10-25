#!/usr/bin/env python3
"""Painel de terminal das varreduras: processos, item atual, progresso, ETA, acertos.

    python3 analysis/sweep_dashboard.py            # atualiza a cada 10 s (Ctrl-C sai)
    python3 analysis/sweep_dashboard.py --once     # imprime uma vez
    python3 analysis/sweep_dashboard.py -n 30      # intervalo em segundos
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SW = os.path.join(HERE, "sweeps")

QUEUES = [  # (log, rotulo, padrao do processo)
    ("run-h9-mi.log", "H9 C  bx2.0 nao endurecido (m/i, m/0/i, m/0h/i)", "bx2_mi_sweep --path m/"),
    ("run-h9-mih-mt.log", "H9 C  bx2.0 m/ih mt19937 (Windows)", "bx2_mi_sweep --path m/ih --encoder bx2-mt19937"),
    ("run-h9.log", "H9 Py bx2.0 m/ih", "master_seed_sweep.py --jobs 8 --family bip32 --path m/ih --encoder bx2"),
    ("run-h10.log", "H10 Armory", "master_seed_sweep.py --jobs 8 --family armory"),
    ("run-rerun.log", "Reruns anchor_only", "rerun_old_sweeps.py"),
    ("run.log", "Fila base", "master_seed_sweep.py --jobs 8 --family (hashseq|bip32 --path \"?m/(ih|0h/i|0/i|i)\"? --encoder (mt256|raw4be|ascii))"),
    ("run-h2.log", "H2 mascaras/indices", "master_seed_sweep.py --jobs 8 .*--(mask|index-map)"),
    ("run-h11.log", "H11 pyrandom", "pyrandom_range_sweep.py"),
    ("run-prng.log", "H12 PRNG direto (C)", "prng_layout_sweep"),
    ("run-degenerate.log", "H3b seeds degeneradas", "degenerate_seed_sweep.py"),
    ("run-fast.log", "Fila rapida", "run_sweeps_fast.sh"),
]


def ps():
    out = subprocess.run(["ps", "-Ao", "pid,stat,etime,pcpu,args"], capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines()[1:]:
        if re.search(r"bx2_mi_sweep|prng_layout_sweep|master_seed_sweep|pyrandom_range|degenerate_seed|rerun_old|run_chain|run_sweeps|run_h9_mi|run_prng", line) and "grep" not in line:
            rows.append(line)
    return rows


def tail(path, n=600):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - n))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def last_item(path):
    """ultimo cabecalho ### e ultima linha de progresso."""
    try:
        with open(path, "rb") as f:
            data = f.read().decode("utf-8", "replace")
    except OSError:
        return None, None, None
    heads = [l for l in data.splitlines() if l.startswith("###")]
    head = heads[-1] if heads else ""
    fim = head.startswith("### FIM") or "CHAIN END" in head
    prog = [l for l in tail(path, 1500).replace("\r", "\n").splitlines() if "cand/s" in l or "est/s" in l]
    return head, (prog[-1].strip() if prog else ""), fim


def short_head(h):
    h = re.sub(r"^### ", "", h)
    h = re.sub(r" :: \d{4}-\d\d-\d\dT[\d:]+Z", "", h)
    h = re.sub(r"--output \S+", "", h).replace("--family ", "").replace("--encoder ", "").replace("--path ", "").replace("--range ", "")
    return h.strip()[:70]


def hits():
    n = 0
    for p in glob.glob(os.path.join(SW, "**", "*.txt"), recursive=True):
        try:
            n += sum(1 for l in open(p) if l.startswith("HIT"))
        except OSError:
            pass
    for p in glob.glob(os.path.join(SW, "**", "*.json"), recursive=True):
        try:
            d = json.load(open(p))
            n += len(d.get("hits", [])) + len(d.get("anchor_only", []))
        except Exception:
            pass
    return n


def ledger():
    try:
        h = json.load(open(os.path.join(ROOT, "HYPOTHESES.json")))
        hy = h["hypotheses"] if isinstance(h, dict) else h
        n_sw = len(glob.glob(os.path.join(SW, "*.json")))
        return len(hy), n_sw
    except Exception:
        return 0, 0


def render():
    procs = ps()
    running = {}
    for q in QUEUES:
        running[q[0]] = any(re.search(q[2], r) for r in procs)
    lines = []
    load = os.getloadavg()
    lines.append("VARREDURAS  %s   load %.0f/%.0f/%.0f   processos de varredura: %d" % (
        time.strftime("%Y-%m-%d %H:%M:%S"), load[0], load[1], load[2], sum(1 for r in procs if "zsh" not in r)))
    lines.append("=" * 118)
    lines.append("%-4s %-40s %-52s %s" % ("", "fila", "item atual", "progresso"))
    for log, label, _ in QUEUES:
        head, prog, fim = last_item(os.path.join(SW, log))
        if head is None:
            continue
        state = "RUN " if running[log] else ("FIM " if fim else "stop")
        m = re.search(r"(\d+\.\d+)%.*?(\d+) cand/s.*?hits=(\d+)(?:.*?eta=(\d+) min)?", prog or "")
        if m:
            eta = ("eta %sm" % m.group(4)) if m.group(4) else ""
            p = "%6s%%  %9s/s  hits=%s %s" % (m.group(1), m.group(2), m.group(3), eta)
        else:
            p = (prog or "")[:36]
        if fim and not running[log]:
            p = "concluida"
        lines.append("%-4s %-40s %-52s %s" % (state, label[:40], short_head(head)[:52], p))
    lines.append("=" * 118)
    nh, cov = ledger()
    lines.append("acertos (HIT/hits/anchor_only em todas as saidas): %d     ledger: %d hipoteses, %d varreduras registradas" % (hits(), nh, cov))
    done_c = len([p for p in glob.glob(os.path.join(SW, "h9mi-*.txt")) if "DONE" in tail(p, 400)])
    done_p = len([p for p in glob.glob(os.path.join(SW, "prng", "*.txt")) if "DONE" in tail(p, 400)])
    lines.append("itens C concluidos: H9 m/i-family %d/16   PRNG direto %d/30     parar tudo: ./analysis/sweep_ctl.sh stop; pkill -f 'bx2_mi_sweep|run_h9_mi|run_chain|run_sweeps_h11|pyrandom_range'" % (done_c, done_p))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("-n", type=int, default=10)
    a = ap.parse_args()
    while True:
        s = render()
        if a.once:
            print(s)
            return
        sys.stdout.write("\x1b[2J\x1b[H" + s + "\n")
        sys.stdout.flush()
        try:
            time.sleep(a.n)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    main()
