"""
Verificacao rigorosa dos 2 sinais que apareceram no gap_analysis:
  A. Bias modular mod 23 (chi2=43.66) - real ou artefato?
  B. MSB de r no ECDSA (p=0.035) - real ou comparacao multipla?

Metodo: Monte Carlo que replica EXATAMENTE os ranges de cada puzzle
(puzzles pequenos sao deterministicamente nao-uniformes mod p - isso
precisa estar no modelo nulo, senao inflamos o chi2 artificialmente).
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

random.seed(2024)
N_SIM = 300_000

# ============================================================
# A. BIAS MODULAR mod 23
# ============================================================
print("=" * 72)
print("A. BIAS MODULAR mod 23 - verificacao Monte Carlo")
print("=" * 72)

# ranges de cada puzzle resolvido
ranges = {n: (1 << (n - 1), (1 << n) - 1) for n in SOLVED}
keys_all = list(SOLVED.values())

# Teste 1: TODOS os puzzles (inclui pequenos, deterministicamente nao-uniformes)
print("\n  [A1] Todos os puzzles resolvidos (n=%d)" % len(keys_all))
for p in [17, 19, 23]:
    obs = chi2_mod(keys_all, p)
    exceed = 0
    for _ in range(N_SIM):
        sim = [random.randint(lo, hi) for (lo, hi) in ranges.values()]
        if chi2_mod(sim, p) >= obs:
            exceed += 1
    pval = exceed / N_SIM
    print(f"    mod {p}: chi2_obs={obs:.2f}  p-value(MC)={pval:.4f}  "
          f"{'SIGNIFICATIVO' if pval < 0.05 else 'ruido'}")

# Teste 2: SO puzzles grandes (n>=30, range >> 23 -> mod realmente uniforme)
big = {n: k for n, k in SOLVED.items() if n >= 30}
keys_big = list(big.values())
ranges_big = {n: (1 << (n - 1), (1 << n) - 1) for n in big}
print(f"\n  [A2] So puzzles n>=30 (n={len(keys_big)}) - sem distorcao de range pequeno")
for p in [17, 19, 23]:
    obs = chi2_mod(keys_big, p)
    exceed = 0
    for _ in range(N_SIM):
        sim = [random.randint(lo, hi) for (lo, hi) in ranges_big.values()]
        if chi2_mod(sim, p) >= obs:
            exceed += 1
    pval = exceed / N_SIM
    print(f"    mod {p}: chi2_obs={obs:.2f}  p-value(MC)={pval:.4f}  "
          f"{'SIGNIFICATIVO' if pval < 0.05 else 'ruido'}")

# Bonferroni: testamos 8 primos no gap_analysis
print(f"\n  Correcao Bonferroni (8 primos testados): alpha = 0.05/8 = 0.00625")
print(f"  -> mod 23 precisa de p-value < 0.00625 para ser significativo de verdade.")

# ============================================================
# B. MSB de r no ECDSA
# ============================================================
print(f"\n{'='*72}")
print("B. MSB de r (ECDSA) - contexto de comparacao multipla")
print(f"{'='*72}")

with open(os.path.join(DATA, "signatures.json")) as f:
    sigs_data = json.load(f)

all_r = [int(s["r"], 16) for sigs in sigs_data.values() for s in sigs]
n_sig = len(all_r)
msb_high = sum(1 for r in all_r if r.to_bytes(32, 'big')[0] >= 0x80)

# binomial exato
def binom_two_tailed(k, n, p=0.5):
    obs = abs(k - n * p)
    return min(1.0, sum(math.comb(n, i) * p**i * (1-p)**(n-i)
                        for i in range(n+1) if abs(i - n*p) >= obs - 1e-9))

p_msb = binom_two_tailed(msb_high, n_sig)
print(f"\n  MSB(r)>=0x80: {msb_high}/{n_sig}  p-value binomial = {p_msb:.4f}")

# Tambem testar bit 0 (paridade de r) e segundo bit, para ver se MSB e cherry-picking
print(f"\n  Para contexto, outros bits de r (se varios derem p<0.05 = ruido multiplo):")
for bitpos, label in [(255, "MSB"), (0, "LSB(paridade)"), (254, "bit254"),
                      (128, "bit128"), (64, "bit64")]:
    ones = sum(1 for r in all_r if (r >> bitpos) & 1)
    pv = binom_two_tailed(ones, n_sig)
    print(f"    {label:>14}: {ones}/{n_sig} um  p={pv:.4f}  {'<-- <0.05' if pv < 0.05 else ''}")

print(f"""
  Nota interpretativa:
  - r e a coordenada x de k*G (publica). Bias em r NAO revela a chave privada.
  - Exploravel apenas com MULTIPLAS assinaturas/chave + nonce enviesado (lattice).
  - Alvos 135-160 tem 1 assinatura cada -> mesmo se real, INEXPLORAVEL.
  - Conclusao independe de p: a via ECDSA continua fechada para os alvos.
""")
