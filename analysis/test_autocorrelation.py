import math
import random

SOLVED_PUZZLES = {
    1:  0x1, 2: 0x3, 3: 0x7, 4: 0x8, 5: 0x15,
    6:  0x31, 7: 0x4c, 8: 0xe0, 9: 0x1d3, 10: 0x202,
    11: 0x483, 12: 0xa7b, 13: 0x1460, 14: 0x2930, 15: 0x68f3,
    16: 0xc936, 17: 0x1764f, 18: 0x3080d, 19: 0x5749f, 20: 0xd2c55,
    21: 0x1ba534, 22: 0x2de40f, 23: 0x556e52, 24: 0xdc2a04, 25: 0x1fa5ee5,
    26: 0x340326e, 27: 0x6ac3875, 28: 0xd916ce8, 29: 0x17e2551e, 30: 0x3d94cd64,
    31: 0x7d4fe747, 32: 0xb862a62e, 33: 0x1a96ca8d8, 34: 0x34a65911d, 35: 0x4aed21170,
    36: 0x9de820a7c, 37: 0x1757756a93, 38: 0x22382facd0, 39: 0x4b5f8303e9, 40: 0xe9ae4933d6,
    41: 0x153869acc5b, 42: 0x2a221c58d8f, 43: 0x6bd3b27c591, 44: 0xe02b35a358f, 45: 0x122fca143c05,
    46: 0x2ec18388d544, 47: 0x6cd610b53cba, 48: 0xade6d7ce3b9b, 49: 0x174176b015f4d, 50: 0x22bd43c2e9354,
    51: 0x75070a1a009d4, 52: 0xefae164cb9e3c, 53: 0x180788e47e326c, 54: 0x236fb6d5ad1f43, 55: 0x6abe1f9b67e114,
    56: 0x9d18b63ac4ffdf, 57: 0x1eb25c90795d61c, 58: 0x2c675b852189a21, 59: 0x7496cbb87cab44f, 60: 0xfc07a1825367bbe,
    61: 0x13c96a3742f64906, 62: 0x363d541eb611abee, 63: 0x7cce5efdaccf6808, 64: 0xf7051f27b09112d4,
    65: 0x1a838b13505b26867, 66: 0x2832ed74f2b5e35ee, 67: 0x730fc235c1942c1ae, 68: 0xbebb3940cd0fc1491,
    69: 0x101d83275fb2bc7e0c, 70: 0x349b84b6431a6c4ef1,
}

def norm_pos(n, key):
    lo = 1 << (n - 1)
    hi = (1 << n) - 1
    if hi == lo:
        return 0.5
    return (key - lo) / (hi - lo)

def autocorr(series, lag):
    n = len(series)
    avg = sum(series) / n
    var = sum((x - avg)**2 for x in series)
    if var == 0:
        return 0
    cov = sum((series[i] - avg) * (series[i + lag] - avg) for i in range(n - lag))
    return cov / var

seq_keys = sorted(k for k in SOLVED_PUZZLES if k <= 70)
seq_pos = [norm_pos(k, SOLVED_PUZZLES[k]) * 100 for k in seq_keys]
N = len(seq_pos)
observed_lag3 = autocorr(seq_pos, 3)

print("=" * 70)
print("TESTE DEFINITIVO: AUTOCORRELACAO LAG-3")
print("=" * 70)
print(f"\n  Valor observado:  r(3) = {observed_lag3:+.6f}")
print(f"  Amostra:          N = {N} puzzles consecutivos (#1-#70)")

# =====================================================
# TESTE 1: Intervalo de confianca analitico (Bartlett)
# =====================================================
print(f"\n{'='*70}")
print("TESTE 1: Limites de Bartlett (IC 95%)")
print(f"{'='*70}")

# Under H0 (white noise), Var(r(k)) ≈ 1/N
se = 1 / math.sqrt(N)
ci_low = -1.96 * se
ci_high = +1.96 * se

print(f"  Erro padrao (1/sqrt(N)):  {se:.4f}")
print(f"  IC 95%:  [{ci_low:+.4f}, {ci_high:+.4f}]")
print(f"  r(3) = {observed_lag3:+.4f}  {'FORA do IC -> significativo' if abs(observed_lag3) > 1.96 * se else 'DENTRO do IC -> NAO significativo'}")
print(f"  Z-score:  {observed_lag3 / se:+.3f}  (precisa > 1.96 para significancia)")

# =====================================================
# TESTE 2: Ljung-Box Q statistic
# =====================================================
print(f"\n{'='*70}")
print("TESTE 2: Ljung-Box Q (testa lags 1 a 5 conjuntamente)")
print(f"{'='*70}")

Q = 0
max_lag = 5
for k in range(1, max_lag + 1):
    rk = autocorr(seq_pos, k)
    Q += (rk ** 2) / (N - k)
    print(f"  r({k}) = {rk:+.4f}   contribuicao Q = {N*(N+2) * (rk**2)/(N-k):.4f}")

Q *= N * (N + 2)
chi2_crit = 11.07

print(f"\n  Q = {Q:.4f}")
print(f"  Graus de liberdade: {max_lag}")
print(f"  Valor critico chi2(5, 0.05): {chi2_crit}")
print(f"  {'REJEITA H0 -> autocorrelacao significativa' if Q > chi2_crit else 'NAO REJEITA H0 -> sem autocorrelacao'}")

# =====================================================
# TESTE 3: Monte Carlo (o mais robusto)
# =====================================================
print(f"\n{'='*70}")
print("TESTE 3: Monte Carlo - 1.000.000 simulacoes")
print(f"{'='*70}")

random.seed(42)
N_SIM = 1_000_000
count_greater = 0
count_greater_abs = 0
sim_lag3s = []

for _ in range(N_SIM):
    fake = [random.uniform(0, 100) for _ in range(N)]
    r3 = autocorr(fake, 3)
    sim_lag3s.append(r3)
    if r3 >= observed_lag3:
        count_greater += 1
    if abs(r3) >= abs(observed_lag3):
        count_greater_abs += 1

p_one_tail = count_greater / N_SIM
p_two_tail = count_greater_abs / N_SIM

sim_lag3s.sort()
pct_2_5 = sim_lag3s[int(N_SIM * 0.025)]
pct_97_5 = sim_lag3s[int(N_SIM * 0.975)]
pct_0_5 = sim_lag3s[int(N_SIM * 0.005)]
pct_99_5 = sim_lag3s[int(N_SIM * 0.995)]
sim_mean = sum(sim_lag3s) / N_SIM
sim_std = (sum((x - sim_mean)**2 for x in sim_lag3s) / N_SIM) ** 0.5

print(f"  Distribuicao nula de r(3) sob aleatoriedade:")
print(f"    Media:  {sim_mean:+.6f}  (esperado ~0)")
print(f"    Std:    {sim_std:.6f}")
print(f"    IC 95%: [{pct_2_5:+.4f}, {pct_97_5:+.4f}]")
print(f"    IC 99%: [{pct_0_5:+.4f}, {pct_99_5:+.4f}]")
print(f"\n  Valor observado: r(3) = {observed_lag3:+.6f}")
print(f"  P-value (unicaudal, r >= obs):  {p_one_tail:.6f}  ({p_one_tail*100:.3f}%)")
print(f"  P-value (bicaudal, |r| >= obs): {p_two_tail:.6f}  ({p_two_tail*100:.3f}%)")
print(f"\n  {'SIGNIFICATIVO a 5%' if p_two_tail < 0.05 else 'NAO SIGNIFICATIVO a 5%'}")
print(f"  {'SIGNIFICATIVO a 1%' if p_two_tail < 0.01 else 'NAO SIGNIFICATIVO a 1%'}")

# =====================================================
# TESTE 4: Permutation test (preserva distribuicao marginal)
# =====================================================
print(f"\n{'='*70}")
print("TESTE 4: Teste de Permutacao - 500.000 shuffles")
print(f"{'='*70}")

N_PERM = 500_000
count_perm = 0
perm_lag3s = []

for _ in range(N_PERM):
    shuffled = seq_pos[:]
    random.shuffle(shuffled)
    r3 = autocorr(shuffled, 3)
    perm_lag3s.append(r3)
    if abs(r3) >= abs(observed_lag3):
        count_perm += 1

p_perm = count_perm / N_PERM
perm_lag3s.sort()
perm_95 = (perm_lag3s[int(N_PERM * 0.025)], perm_lag3s[int(N_PERM * 0.975)])

print(f"  Distribuicao de r(3) sob permutacao dos dados reais:")
print(f"    IC 95%: [{perm_95[0]:+.4f}, {perm_95[1]:+.4f}]")
print(f"  Valor observado: {observed_lag3:+.4f}")
print(f"  P-value (bicaudal): {p_perm:.6f}  ({p_perm*100:.3f}%)")
print(f"\n  {'SIGNIFICATIVO a 5%' if p_perm < 0.05 else 'NAO SIGNIFICATIVO a 5%'}")

# =====================================================
# TESTE 5: Robustez - remover outliers e retestar
# =====================================================
print(f"\n{'='*70}")
print("TESTE 5: Robustez - remocao de outliers")
print(f"{'='*70}")

avg = sum(seq_pos) / len(seq_pos)
std = (sum((p - avg)**2 for p in seq_pos) / len(seq_pos)) ** 0.5

filtered_keys = []
filtered_pos = []
removed = []
for i, k in enumerate(seq_keys):
    if abs(seq_pos[i] - avg) <= 2 * std:
        filtered_keys.append(k)
        filtered_pos.append(seq_pos[i])
    else:
        removed.append((k, seq_pos[i]))

if len(filtered_pos) > 3:
    r3_filtered = autocorr(filtered_pos, 3)
    print(f"  Removidos (>2 sigma): {len(removed)} puzzles")
    for k, p in removed:
        print(f"    #{k}: {p:.1f}%")
    print(f"  r(3) original:   {observed_lag3:+.4f}")
    print(f"  r(3) filtrado:   {r3_filtered:+.4f}")
    print(f"  Diferenca:       {abs(r3_filtered - observed_lag3):.4f}")
    if abs(r3_filtered) < abs(observed_lag3) * 0.5:
        print(f"  -> r(3) CAI drasticamente sem outliers = ARTEFATO dos outliers")
    else:
        print(f"  -> r(3) se mantem = SINAL robusto")
else:
    print(f"  Dados insuficientes apos filtragem")

# =====================================================
# TESTE 6: Bonferroni - correcao para multiplos testes
# =====================================================
print(f"\n{'='*70}")
print("TESTE 6: Correcao de Bonferroni (multiplos lags testados)")
print(f"{'='*70}")

# We tested 5 lags, so need to correct
bonferroni_alpha = 0.05 / 5
print(f"  Lags testados: 5")
print(f"  Alpha original: 0.05")
print(f"  Alpha corrigido (Bonferroni): {bonferroni_alpha:.3f}")
print(f"  P-value do lag-3 (Monte Carlo): {p_two_tail:.6f}")
print(f"  {'SIGNIFICATIVO apos correcao' if p_two_tail < bonferroni_alpha else 'NAO SIGNIFICATIVO apos correcao de Bonferroni'}")

# =====================================================
# VEREDITO FINAL
# =====================================================
print(f"\n{'='*70}")
print("VEREDITO FINAL")
print(f"{'='*70}")

tests_passed = 0
total_tests = 4
results = []

if abs(observed_lag3) > 1.96 * se:
    results.append(("Bartlett", "SIGNIFICATIVO"))
    tests_passed += 1
else:
    results.append(("Bartlett", "NAO significativo"))

if p_two_tail < 0.05:
    results.append(("Monte Carlo", f"SIGNIFICATIVO (p={p_two_tail:.4f})"))
    tests_passed += 1
else:
    results.append(("Monte Carlo", f"NAO significativo (p={p_two_tail:.4f})"))

if p_perm < 0.05:
    results.append(("Permutacao", f"SIGNIFICATIVO (p={p_perm:.4f})"))
    tests_passed += 1
else:
    results.append(("Permutacao", f"NAO significativo (p={p_perm:.4f})"))

if p_two_tail < bonferroni_alpha:
    results.append(("Bonferroni", "SIGNIFICATIVO"))
    tests_passed += 1
else:
    results.append(("Bonferroni", "NAO significativo"))

for name, result in results:
    print(f"  {name:15s}: {result}")

print(f"\n  Testes que indicam significancia: {tests_passed}/{total_tests}")

if tests_passed >= 3:
    print(f"\n  >>> CONCLUSAO: A autocorrelacao lag-3 E REAL.")
    print(f"  >>> Existe um padrao de dependencia entre chaves separadas por 3 posicoes.")
    print(f"  >>> Isso sugere que o gerador deterministic tem ciclo ou estrutura interna.")
elif tests_passed >= 1:
    print(f"\n  >>> CONCLUSAO: EVIDENCIA FRACA / INCONCLUSIVO.")
    print(f"  >>> O sinal e marginal e pode ser ruido estatistico.")
    print(f"  >>> Com apenas 70 amostras, nao ha poder estatistico suficiente.")
else:
    print(f"\n  >>> CONCLUSAO: A autocorrelacao lag-3 E RUIDO.")
    print(f"  >>> Nao ha evidencia de padrao. As chaves sao independentes.")
    print(f"  >>> Nao e possivel prever posicoes futuras a partir das anteriores.")

print()


def _chi2_cdf_approx(x, k):
    """Rough chi-squared CDF via normal approximation for display only."""
    z = ((x/k)**(1/3) - (1 - 2/(9*k))) / math.sqrt(2/(9*k))
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))
