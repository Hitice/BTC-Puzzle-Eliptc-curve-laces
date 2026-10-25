#!/usr/bin/env python3
"""Tabela de bits das chaves conhecidas + exclusoes EXATAS de familias de geracao.

Aviso de poder (BRIEFING secao 3): estatistica sobre as 82 chaves nao distingue seed
fraca de seed forte. Esta tabela NAO tenta isso. Ela serve para dois usos:

1. Visualizar, lado a lado, os n-1 bits de informacao de cada puzzle resolvido.
2. Rodar testes EXATOS (nao estatisticos) que matam ou mantem familias inteiras de
   geracao em milissegundos, antes de qualquer varredura:
     T1  um unico segredo S mascarado por baixo: key_n mod 2^(m-1) == key_m mod 2^(m-1)
     T2  um unico segredo S mascarado por cima (ou cadeia por deslocamento): key_n >> (n-m) == key_m
     T3  gerador de 53 bits (random()*largura, Math.random, nextDouble): bits baixos zerados em n > 54
     T4  gerador de 64 bits reutilizado (nextLong, uint64): bits baixos zerados em n > 65
     T5  mesma palavra de 32 bits alinhada em duas chaves (fluxo PRNG reaproveitado)
     T6  mesmo filho mascarado duas vezes (indice repetido): bits baixos iguais entre dois puzzles
     T7  chave de puzzle n igual a 2^(n-1) + key_m (reuso de sorteio pequeno)
   Cada teste imprime o primeiro puzzle que o contradiz, ou "consistente".

    python3 analysis/known_keys_bit_table.py            # tabela + testes
    python3 analysis/known_keys_bit_table.py --no-table # so os testes
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    with open(os.path.join(HERE, "..", "data", "puzzles.json")) as f:
        puz = json.load(f)["puzzles"]
    return {p["puzzle"]: p["privkey_int"] for p in puz if p["status"] == "solved"}


def tz(x):
    return (x & -x).bit_length() - 1 if x else 0


def table(solved):
    print("%4s %4s  %-66s %7s %4s %4s  %s" % ("n", "bits", "chave (hex)", "pos", "tz", "pop", "n-1 bits de informacao (binario, sem o bit lider)"))
    for n in sorted(solved):
        k = solved[n]
        info = k - (1 << (n - 1))
        b = format(info, "0%db" % (n - 1)) if n > 1 else "-"
        if len(b) > 72:
            b = b[:34] + ".." + b[-34:]
        pos = info / float(1 << (n - 1)) if n > 1 else 0.5
        print("%4d %4d  %-66x %7.4f %4d %4d  %s" % (n, n, k, pos, tz(info) if info else n - 1, bin(k).count("1"), b))


def tests(solved):
    ns = sorted(solved)
    out = []

    # T1: unico segredo, mascara baixa
    bad = None
    for i, m in enumerate(ns):
        for n in ns[i + 1:]:
            if (solved[n] & ((1 << (m - 1)) - 1)) != (solved[m] & ((1 << (m - 1)) - 1)):
                bad = (m, n)
                break
        if bad:
            break
    out.append(("T1 um segredo, mascara baixa (key_n low == key_m low)", bad))

    # T2: unico segredo, mascara alta / cadeia por deslocamento
    bad = None
    for i, m in enumerate(ns):
        for n in ns[i + 1:]:
            if (solved[n] >> (n - m)) != solved[m]:
                bad = (m, n)
                break
        if bad:
            break
    out.append(("T2 um segredo, mascara alta / deslocamento (key_n >> (n-m) == key_m)", bad))

    # T3: 53 bits de mantissa
    bad = None
    for n in ns:
        if n - 1 > 53:
            info = solved[n] - (1 << (n - 1))
            if info and tz(info) < (n - 1 - 53):
                bad = (n, "tz=%d < %d" % (tz(info), n - 1 - 53))
                break
    out.append(("T3 gerador de 53 bits (random()*2^(n-1), Math.random, nextDouble)", bad))

    # T4: 64 bits
    bad = None
    for n in ns:
        if n - 1 > 64:
            info = solved[n] - (1 << (n - 1))
            if info and tz(info) < (n - 1 - 64):
                bad = (n, "tz=%d < %d" % (tz(info), n - 1 - 64))
                break
    out.append(("T4 gerador de 64 bits (nextLong, uint64) deslocado para a faixa", bad))

    # T5: palavras de 32 bits alinhadas repetidas entre chaves (so palavras completas e nao nulas)
    seen = {}
    rep = []
    for n in ns:
        k = solved[n]
        words = (n - 1) // 32  # palavras completas dentro da informacao
        info = k - (1 << (n - 1))
        for w in range(words):
            v = (info >> (32 * w)) & 0xFFFFFFFF
            if v == 0:
                continue
            if v in seen and seen[v][0] != n:
                rep.append((seen[v], (n, w), v))
            seen[v] = (n, w)
    out.append(("T5 palavra de 32 bits alinhada repetida em duas chaves", rep if rep else None, "lista"))

    # T6: mesmo filho mascarado duas vezes: bits baixos iguais entre puzzles distintos (m >= 16)
    rep = []
    for i, m in enumerate(ns):
        if m < 16:
            continue
        for n in ns[i + 1:]:
            if (solved[n] & ((1 << (m - 1)) - 1)) == (solved[m] & ((1 << (m - 1)) - 1)):
                rep.append((m, n))
    out.append(("T6 mesmo filho mascarado duas vezes (bits baixos iguais, m >= 16)", rep if rep else None, "lista"))

    # T7: key_n - 2^(n-1) == key_m para algum m (reuso)
    rep = []
    vals = {solved[m]: m for m in ns}
    for n in ns:
        info = solved[n] - (1 << (n - 1))
        # so conta quando key_m tem >= 16 bits: para m pequeno a coincidencia e esperada
        # (ex.: 3 = 2 + key_1 e 7 = 4 + key_2 acontecem com 50% e 25% por acaso)
        if info in vals and vals[info] != n and vals[info] >= 16:
            rep.append((vals[info], n))
    out.append(("T7 key_n == 2^(n-1) + key_m, m >= 16 (reuso de sorteio)", rep if rep else None, "lista"))

    print("\nTESTES EXATOS (nao estatisticos; cada um exclui ou mantem uma familia inteira)")
    for row in out:
        name, bad = row[0], row[1]
        if len(row) == 3:
            if bad:
                print("  [SINAL ] %s: %s" % (name, bad))
            else:
                print("  [nada  ] %s: nenhuma coincidencia (esperado por acaso: ~0)" % name)
        else:
            if bad:
                print("  [MORTO ] %s: contradito em %s" % (name, bad))
            else:
                print("  [vivo  ] %s: consistente com todas as chaves conhecidas" % name)
    print("\n  Leitura: MORTO = a familia nao gerou estas chaves, em nenhuma seed. 'vivo' nao e")
    print("  evidencia a favor. SINAL = coincidencia improvavel por acaso; investigar antes de concluir.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-table", action="store_true")
    args = ap.parse_args()
    solved = load()
    if not args.no_table:
        table(solved)
    tests(solved)
    bits = sum(n - 1 for n in solved)
    print("\n  %d chaves conhecidas, %d bits de informacao no total; #130 sozinha tem 129." % (len(solved), bits))


if __name__ == "__main__":
    main()
