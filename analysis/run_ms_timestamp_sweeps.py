#!/usr/bin/env python3
"""Fila do H3 ramo de timestamp em MILISSEGUNDOS, via master_seed_sweep.py.

A cobertura de inteiros do repo vai ate 2^32 e cobre timestamps em SEGUNDOS.
Um timestamp de 2015 em ms e ~1.42e12 (41 bits): fora de tudo que foi varrido.
Motivacao no BRIEFING secao 8 -- H5/H6 cobrem esses PRNGs como fonte da CHAVE e
anotam que nao os testam como fonte da SEED. Date.now() do V8 e milissegundos.

Janela ancorada no block_time da tx de financiamento de 2015 (1421345234).
"""
import json, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TX_2015 = 1421345234
SWEEP = HERE/'master_seed_sweep.py'
COMBOS = [
    ('ascii',  ['--family', 'hashseq', '--hash', 'sha256', '--index-enc', 'be4']),
    ('ascii',  ['--family', 'hashseq', '--hash', 'sha256', '--index-enc', 'str']),
    ('raw8be', ['--family', 'hashseq', '--hash', 'sha256', '--index-enc', 'be4']),
    ('raw8be', ['--family', 'hashseq', '--hash', 'sha256', '--index-enc', 'str']),
    ('sha256', ['--family', 'hashseq', '--hash', 'sha256', '--index-enc', 'be4']),
    ('sha256', ['--family', 'hashseq', '--hash', 'sha256', '--index-enc', 'str']),
]


def main():
    days = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
    hi = TX_2015*1000
    lo = hi - int(days*86400*1000)
    log = open(HERE/'ms-timestamp-sweep.log', 'w')

    def say(m):
        print(m, flush=True); log.write(m+'\n'); log.flush()

    say(f'janela: [{lo}, {hi}) = {days} dias antes da tx de 2015, '
        f'{hi-lo:,} candidatos por combinacao')
    rows, started = [], time.time()
    outdir = HERE/'sweeps'
    outdir.mkdir(exist_ok=True)
    for encoder, famargs in COMBOS:
        # master_seed_sweep imprime dois cabecalhos antes do JSON em stdout;
        # --output grava o JSON limpo, entao lemos o arquivo.
        tag = f"ms-{encoder}-{'-'.join(a.lstrip('-') for a in famargs[1::2])}"
        dest = outdir/f'{tag}.json'
        cmd = [sys.executable, '-B', str(SWEEP), '--encoder', encoder,
               '--mask', 'low', '--range', f'{lo}-{hi}',
               '--output', str(dest)] + famargs
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not dest.exists():
            say(f'FALHOU {encoder} {famargs}: {proc.stderr.strip()[:300]}')
            continue
        r = json.loads(dest.read_text())
        rows.append({'encoder': encoder, 'family_args': famargs, **{
            k: r[k] for k in ('candidates', 'anchor_puzzle', 'anchor_bits',
                              'confirm_puzzles', 'elapsed_s', 'rate_per_s', 'hits')}})
        say(f"{encoder:8s} {' '.join(famargs[1:]):34s} {r['candidates']:>13,} cand  "
            f"{r['rate_per_s']:>11,.0f}/s  {r['elapsed_s']:7.1f}s  hits={len(r['hits'])}")
    report = {
        'hypothesis': 'H3 ramo timestamp em milissegundos (nunca coberto)',
        'anchor_tx_block_time': TX_2015,
        'window': {'lo_ms': lo, 'hi_ms': hi, 'days_before_tx': days},
        'anchor': 'puzzle #130, 129 bits, falso positivo 2^-129',
        'positive_control': 'herdado de master_seed_sweep.py --self-test (8/8) e de '
                            'timestamp_ms_sweep.py --self-test (6 combinacoes x 3 assercoes)',
        'combinations': len(rows),
        'candidates_per_combination': hi-lo,
        'total_candidates': sum(r['candidates'] for r in rows),
        'total_hits': sum(len(r['hits']) for r in rows),
        'results': rows,
        'seconds': round(time.time()-started, 1),
        'limitations': [
            'Mascara low apenas; familias hashseq apenas. BIP32 (~800k/s) fica para a etapa 2.',
            'Janela ancorada no block_time da tx; a carteira pode ser bem anterior.',
            'Ausencia de acerto exclui o espaco enumerado, NAO a hipotese.']}
    (HERE/'ms-timestamp-sweep-results.json').write_text(json.dumps(report, indent=2)+'\n')
    say(f"TOTAL {report['total_candidates']:,} candidatos, {report['total_hits']} hits, "
        f"{report['seconds']}s")
    log.close()


if __name__ == '__main__':
    main()
