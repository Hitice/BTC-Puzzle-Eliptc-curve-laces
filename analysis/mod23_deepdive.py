"""
Deep dive no unico sinal sobrevivente: bias modular mod 23.
Tres perguntas:
  1. mod 23 e unicamente anomalo, ou faz parte de um cluster? (testar primos ate 50)
  2. Qual o histograma de residuos mod 23? Que residuos desviam?
  3. O sinal e CONSISTENTE entre segmentos? (split por faixa de puzzle)
     -> aborda diretamente: puzzles iniciais podem ter geracao diferente (escolha humana)
"""
import json
import os
import math
import random
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

with open(os.path.join(DATA, "puzzles.json")) as f:
    PUZZLES = json.load(f)["puzzles"]

SOLVED = {p["puzzle"]: p["privkey_int"] for p in PUZZLES if p["status"] == "solved"}

def chi2_mod(keys, p):
    counts = Counter(k % p for k in keys)
    exp = len(keys) / p
    return sum((counts.get(r, 0) - exp) ** 2 / exp for r in range(p))

def mc_pvalue(keys, ranges_list, p, n_sim=200_000, seed=7):
    rng = random.Random(seed)
    obs = chi2_mod(keys, p)
    exceed = sum(1 for _ in range(n_sim)
                 if chi2_mod([rng.randint(lo, hi) for lo, hi in ranges_list], p) >= obs)
    return obs, exceed / n_sim

PRIMES = [3,5,7,11,13,17,19,23,29,31,37,41,43,47]

# ============================================================
# 1. mod 23 e unico? Varredura de primos
# ============================================================
print("=" * 72)
print("1. VARREDURA DE PRIMOS (mod 23 e unico ou parte de cluster?)")
print("=" * 72)

# usar n>=30 (sem distorcao de range pequeno, conforme alerta metodologico)
big = {n: k for n, k in SOLVED.items() if n >= 30}
keys = list(big.values())
ranges_list = [(1 << (n-1), (1 << n) - 1) for n in big]

print(f"\n  Amostra: {len(keys)} puzzles (n>=30)")
print(f"  {'p':>4}  {'chi2':>8}  {'p-value':>8}  {'flag'}")
print(f"  {'-'*4}  {'-'*8}  {'-'*8}  {'-'*6}")
flagged = []
for p in PRIMES:
    obs, pval = mc_pvalue(keys, ranges_list, p, n_sim=100_000, seed=p)
    flag = "<<<" if pval < 0.05 else ""
    if pval < 0.05:
        flagged.append((p, pval))
    print(f"  {p:>4}  {obs:>8.2f}  {pval:>8.4f}  {flag}")

print(f"\n  Primos com p<0.05: {[p for p,_ in flagged]}")
print(f"  Testamos {len(PRIMES)} primos. Esperado ~{len(PRIMES)*0.05:.1f} falsos positivos por acaso.")
print(f"  Bonferroni alpha = {0.05/len(PRIMES):.5f}")
truly_sig = [p for p, pv in flagged if pv < 0.05/len(PRIMES)]
print(f"  Sobrevivem a Bonferroni: {truly_sig if truly_sig else 'NENHUM'}")

# ============================================================
# 2. Histograma de residuos mod 23
# ============================================================
print(f"\n{'='*72}")
print("2. HISTOGRAMA DE RESIDUOS mod 23 (n>=30)")
print(f"{'='*72}")

counts = Counter(k % 23 for k in keys)
exp = len(keys) / 23
print(f"\n  Esperado por residuo: {exp:.2f}")
print(f"  {'res':>4}  {'obs':>4}  {'desvio':>7}  bar")
for r in range(23):
    c = counts.get(r, 0)
    dev = c - exp
    bar = "#" * c
    flag = " <<<" if abs(dev) > 2.5 else ""
    print(f"  {r:>4}  {c:>4}  {dev:>+7.2f}  {bar}{flag}")

# ============================================================
# 3. CONSISTENCIA ENTRE SEGMENTOS (ponto do usuario)
# ============================================================
print(f"\n{'='*72}")
print("3. CONSISTENCIA ENTRE SEGMENTOS - o sinal replica?")
print("   Se for propriedade real do gerador, aparece em TODOS os segmentos.")
print("   Se vem de geracao humana inicial ou outliers, NAO replica.")
print(f"{'='*72}")

segments = {
    "pequenos #1-15 (suspeitos de escolha humana)": [n for n in SOLVED if n <= 15],
    "medios   #16-50": [n for n in SOLVED if 16 <= n <= 50],
    "grandes  #51-130": [n for n in SOLVED if n >= 51],
}

print()
for label, nums in segments.items():
    ks = [SOLVED[n] for n in nums]
    rng_list = [(1 << (n-1), (1 << n) - 1) for n in nums]
    if len(ks) < 5:
        print(f"  {label}: amostra pequena demais ({len(ks)})")
        continue
    obs, pval = mc_pvalue(ks, rng_list, 23, n_sim=100_000, seed=23)
    print(f"  {label}")
    print(f"     n={len(ks)}  chi2(mod23)={obs:.2f}  p-value={pval:.4f}  "
          f"{'SINAL PRESENTE' if pval < 0.05 else 'sem sinal'}")

# Split-half dos grandes: o sinal e difuso ou concentrado?
print(f"\n  Split-half dos puzzles n>=30:")
big_sorted = sorted(big.keys())
half = len(big_sorted) // 2
for label, subset in [("primeira metade", big_sorted[:half]),
                      ("segunda metade", big_sorted[half:])]:
    ks = [SOLVED[n] for n in subset]
    rng_list = [(1 << (n-1), (1 << n) - 1) for n in subset]
    obs, pval = mc_pvalue(ks, rng_list, 23, n_sim=100_000, seed=99)
    print(f"     {label} ({subset[0]}-{subset[-1]}, n={len(ks)}): "
          f"chi2={obs:.2f}  p={pval:.4f}  {'SINAL' if pval < 0.05 else 'limpo'}")

# ============================================================
# Veredito
# ============================================================
print(f"\n{'='*72}")
print("VEREDITO")
print(f"{'='*72}")
print(f"""
  Interpretacao:
  - Se mod 23 sobrevive a Bonferroni E replica nos dois split-halves
    => sinal real, merece investigacao do gerador.
  - Se NAO sobrevive a Bonferroni OU so aparece em um segmento
    => artefato de comparacao multipla / outliers. Fechado.

  Lembrete: mesmo um bias modular real NAO da, por si so, as chaves.
  Reduziria o espaco por um fator ~constante (ex: log2(23)~4.5 bits),
  insuficiente para tornar #71 (2^70) factivel. Seria pista de gerador
  fraco a investigar, nao uma solucao direta.
""")
