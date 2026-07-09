"""
Teste de derivação: analisar se os bits inferiores das chaves dos puzzles
consecutivos revelam o esquema de geração da wallet determinística.

Se wallet_key_n e wallet_key_{n+1} são chaves consecutivas da wallet:
  puzzle_n mod 2^(n-1) = wallet_key_n mod 2^(n-1)
  puzzle_{n+1} mod 2^n = wallet_key_{n+1} mod 2^n

Portanto, conhecemos os bits baixos de cada chave original.
Se a derivação tem estrutura, as diferenças entre esses bits baixos
NÃO serão aleatórias.
"""
import math
import random
from collections import Counter

SOLVED = {
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

def unmask(puzzle_num, puzzle_key):
    """Recupera os bits baixos da chave original da wallet."""
    return puzzle_key & ((1 << (puzzle_num - 1)) - 1)

print("=" * 70)
print("TESTE DE DERIVACAO - BITS COMPARTILHADOS ENTRE PUZZLES")
print("=" * 70)

# =====================================================================
# TESTE 1: Diferença modular entre bits baixos de chaves consecutivas
# =====================================================================
print(f"\n{'='*70}")
print("TESTE 1: Diferenca (wallet_key_{n+1} - wallet_key_n) mod 2^(n-1)")
print("Se key_i = seed + i, diferenca seria = 1 para todo n")
print("Se key_i = seed * i, diferenca seria = seed mod 2^(n-1)")
print("Se key_i = hash(seed||i), diferenca seria pseudo-aleatoria")
print(f"{'='*70}")

diffs = []
seq_keys = sorted(k for k in SOLVED if k <= 70)

for i in range(len(seq_keys) - 1):
    n = seq_keys[i]
    m = seq_keys[i + 1]
    if m - n != 1:
        continue

    # bits que podemos comparar: min(n-1, m-1) = n-1
    shared_bits = n - 1
    if shared_bits <= 0:
        continue

    mod = 1 << shared_bits
    low_n = unmask(n, SOLVED[n])
    low_m = unmask(m, SOLVED[m])

    diff = (low_m - low_n) % mod
    diffs.append((n, m, shared_bits, diff, low_n, low_m))

print(f"\n  {'Pair':>8}  {'Shared bits':>11}  {'Diff mod 2^(n-1)':>20}  {'Diff (hex)':>20}")
print(f"  {'-'*8}  {'-'*11}  {'-'*20}  {'-'*20}")

for n, m, bits, diff, low_n, low_m in diffs:
    print(f"  {n:>2}->{m:<2}   {bits:>8}       {diff:>20d}  {format(diff, 'x'):>20}")

# Check if all diffs are the same (would indicate key_i = seed + i)
print(f"\n  Verificando se todas as diferencas sao iguais (key_i = seed + i):")
if len(set(d[3] for d in diffs[-20:])) == 1:
    print(f"  !!! TODAS IGUAIS = derivacao linear !!!")
else:
    print(f"  Diferencas variam. Nao e derivacao linear simples.")

# Check if diffs are constant for the LAST entries (larger bit counts)
print(f"\n  Ultimas 10 diferencas (mais bits disponiveis, mais confiavel):")
for n, m, bits, diff, low_n, low_m in diffs[-10:]:
    print(f"    #{n}->{m}: diff = {diff}  (0x{format(diff, 'x')})")

# =====================================================================
# TESTE 2: Bits baixos compartilhados entre puzzle_n e puzzle_{n+k}
# =====================================================================
print(f"\n{'='*70}")
print("TESTE 2: Consistencia de bits baixos entre pares nao-consecutivos")
print("Se as chaves vem da mesma wallet, os bits baixos devem ser")
print("consistentes com a mesma funcao de derivacao")
print(f"{'='*70}")

# For puzzles n and m (m > n), we can compare the lower (n-1) bits
# of both wallet keys
print(f"\n  Comparando bits baixos do puzzle n com os MESMOS bits do puzzle m:")
print(f"  (Se key_i = seed + i, entao low_bits(key_m) - low_bits(key_n) = m-n)")
print()

test_pairs = [(60, 65), (60, 70), (65, 70), (50, 60), (50, 70), (40, 50), (30, 40)]
for n, m in test_pairs:
    if n not in SOLVED or m not in SOLVED:
        continue
    shared_bits = n - 1
    mod = 1 << shared_bits
    low_n = unmask(n, SOLVED[n]) % mod
    low_m = unmask(m, SOLVED[m]) % mod
    diff = (low_m - low_n) % mod
    expected_linear = (m - n) % mod

    is_linear = (diff == expected_linear)
    print(f"  #{n} vs #{m} ({shared_bits} bits): diff={diff}  "
          f"linear_expected={expected_linear}  "
          f"{'MATCH!' if is_linear else 'no match'}")

# =====================================================================
# TESTE 3: Hipotese key_i = hash(seed || i) - bits baixos aleatorios?
# =====================================================================
print(f"\n{'='*70}")
print("TESTE 3: Os bits baixos compartilhados sao aleatorios?")
print("(Monte Carlo: se key_i = hash(seed||i), os bits devem ser uniformes)")
print(f"{'='*70}")

# Test: are the low bits of consecutive puzzle keys independent?
# Use the shared bits between puzzle_n and puzzle_{n+1}: (n-1) bits
# Extract just the LSBs for a simple test
lsb_pairs = []
for i in range(len(seq_keys) - 1):
    n = seq_keys[i]
    m = seq_keys[i + 1]
    if m - n != 1 or n < 8:
        continue
    low_n = SOLVED[n] & 0xFF  # last byte
    low_m = SOLVED[m] & 0xFF  # last byte
    lsb_pairs.append((low_n, low_m))

if lsb_pairs:
    # Correlation between last bytes of consecutive puzzles
    x_vals = [p[0] for p in lsb_pairs]
    y_vals = [p[1] for p in lsb_pairs]
    x_mean = sum(x_vals) / len(x_vals)
    y_mean = sum(y_vals) / len(y_vals)

    cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    var_x = sum((x - x_mean)**2 for x in x_vals)
    var_y = sum((y - y_mean)**2 for y in y_vals)

    if var_x > 0 and var_y > 0:
        correlation = cov / math.sqrt(var_x * var_y)
    else:
        correlation = 0

    print(f"  Correlacao entre ultimo byte de puzzle_n e puzzle_{{n+1}}: {correlation:+.4f}")
    print(f"  (esperado ~0 para hash-based, alto para linear)")

    # Monte Carlo significance
    random.seed(42)
    N_SIM = 500_000
    count_exceed = 0
    for _ in range(N_SIM):
        shuffled = y_vals[:]
        random.shuffle(shuffled)
        cov_s = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, shuffled))
        if var_x > 0 and var_y > 0:
            corr_s = cov_s / math.sqrt(var_x * var_y)
        else:
            corr_s = 0
        if abs(corr_s) >= abs(correlation):
            count_exceed += 1

    p_val = count_exceed / N_SIM
    print(f"  P-value (permutacao, 500K): {p_val:.6f}")
    print(f"  {'SIGNIFICATIVO' if p_val < 0.05 else 'NAO SIGNIFICATIVO'}")

# =====================================================================
# TESTE 4: XOR pattern - bits que se mantem entre puzzles adjacentes
# =====================================================================
print(f"\n{'='*70}")
print("TESTE 4: Bits que se MANTEM entre puzzles adjacentes")
print("(XOR dos bits compartilhados = 0 onde sao iguais)")
print(f"{'='*70}")

xor_hamming = []
for i in range(len(seq_keys) - 1):
    n = seq_keys[i]
    m = seq_keys[i + 1]
    if m - n != 1 or n < 4:
        continue
    shared_bits = n - 1
    mask = (1 << shared_bits) - 1
    low_n = SOLVED[n] & mask
    low_m = SOLVED[m] & mask
    xor = low_n ^ low_m
    hw = bin(xor).count('1')
    ratio = hw / shared_bits if shared_bits > 0 else 0
    xor_hamming.append((n, shared_bits, hw, ratio))

print(f"\n  {'Pair':>8}  {'Shared':>6}  {'XOR HW':>7}  {'Ratio':>7}  {'Status'}")
print(f"  {'-'*8}  {'-'*6}  {'-'*7}  {'-'*7}  {'-'*20}")

for n, bits, hw, ratio in xor_hamming[-20:]:
    status = "ANOMALO" if ratio < 0.3 or ratio > 0.7 else ""
    print(f"  {n:>2}->{n+1:<2}  {bits:>6}  {hw:>7}  {ratio:>6.1%}  {status}")

avg_ratio = sum(r for _, _, _, r in xor_hamming) / len(xor_hamming)
print(f"\n  Ratio medio de bits diferentes: {avg_ratio:.1%} (esperado ~50% para independentes)")

# Monte Carlo for XOR ratio
random.seed(123)
N_SIM = 200_000
sim_avgs = []
for _ in range(N_SIM):
    sim_ratios = []
    for n, bits, _, _ in xor_hamming:
        a = random.getrandbits(bits)
        b = random.getrandbits(bits)
        hw = bin(a ^ b).count('1')
        sim_ratios.append(hw / bits)
    sim_avgs.append(sum(sim_ratios) / len(sim_ratios))

sim_avgs.sort()
p_xor = sum(1 for s in sim_avgs if abs(s - 0.5) >= abs(avg_ratio - 0.5)) / N_SIM
print(f"  P-value (desvio de 50%): {p_xor:.6f}")
print(f"  {'SIGNIFICATIVO - bits compartilhados!' if p_xor < 0.05 else 'NAO SIGNIFICATIVO - independentes'}")

# =====================================================================
# TESTE 5: Projecao - se a derivacao fosse linear, qual seria o puzzle 71?
# =====================================================================
print(f"\n{'='*70}")
print("TESTE 5: Predicao sob hipotese linear")
print(f"{'='*70}")

# Under key_i = seed + i:
# From puzzle 70: seed mod 2^69 = puzzle_70 - 2^69 - 70  (? need to check)
# Actually: puzzle_70 = (seed + 70) mod 2^70, with bit 69 set
# So: (seed + 70) mod 2^69 = puzzle_70 mod 2^69 = puzzle_70 - 2^69

low_70 = SOLVED[70] - (1 << 69)  # lower 69 bits of (seed + 70)
low_69 = SOLVED[69] - (1 << 68)  # lower 68 bits of (seed + 69)

# If linear: (seed + 70) mod 2^68 should equal (seed + 69 + 1) mod 2^68
# i.e., low_70 mod 2^68 should equal (low_69 + 1) mod 2^68
mod_68 = 1 << 68
check = (low_70 % mod_68) == ((low_69 + 1) % mod_68)
print(f"\n  Hipotese: key_i = seed + i")
print(f"    puzzle_70 lower 69 bits: {hex(low_70)}")
print(f"    puzzle_69 lower 68 bits: {hex(low_69)}")
print(f"    (seed+70) mod 2^68 = {hex(low_70 % mod_68)}")
print(f"    (seed+69+1) mod 2^68 = {hex((low_69 + 1) % mod_68)}")
print(f"    Match: {'SIM !!!' if check else 'NAO'}")

if not check:
    # Test key_i = seed * (i+1) or key_i = seed XOR i
    diff_70_69 = (low_70 - low_69) % mod_68
    print(f"\n    Diferenca (mod 2^68): {diff_70_69} = 0x{format(diff_70_69, 'x')}")
    print(f"    Se fosse key_i = seed + i, diferenca seria 1")
    print(f"    Diferenca real: {diff_70_69}")

# Test with more pairs
print(f"\n  Teste sistematico da hipotese linear (key_i = seed + i):")
linear_matches = 0
total_tests = 0
for i in range(len(seq_keys) - 1):
    n = seq_keys[i]
    m = seq_keys[i + 1]
    if m - n != 1 or n < 4:
        continue

    total_tests += 1
    shared = n - 1
    mod = 1 << (shared - 1) if shared > 1 else 1

    low_n = (SOLVED[n] - (1 << (n-1))) % mod
    low_m = (SOLVED[m] - (1 << (m-1))) % mod

    if (low_m - low_n) % mod == 1:
        linear_matches += 1

print(f"    Pares onde diff = 1: {linear_matches}/{total_tests}")
print(f"    {'DERIVACAO LINEAR CONFIRMADA!' if linear_matches == total_tests else 'Derivacao NAO e linear simples'}")

# =====================================================================
# TESTE 6: Entropia condicional
# =====================================================================
print(f"\n{'='*70}")
print("TESTE 6: Entropia condicional dos bits baixos")
print("Se conhecer os bits de puzzle_n reduz a incerteza de puzzle_{n+1},")
print("entao a derivacao tem estrutura exploravel.")
print(f"{'='*70}")

# Compare last 8 bits of consecutive puzzles
last_8_pairs = []
for i in range(len(seq_keys) - 1):
    n = seq_keys[i]
    m = seq_keys[i + 1]
    if m - n != 1 or n < 10:
        continue
    last_8_pairs.append((SOLVED[n] & 0xFF, SOLVED[m] & 0xFF))

# Mutual information estimation
joint_counts = Counter(last_8_pairs)
x_counts = Counter(p[0] for p in last_8_pairs)
y_counts = Counter(p[1] for p in last_8_pairs)
N_total = len(last_8_pairs)

mi = 0
for (x, y), count_xy in joint_counts.items():
    p_xy = count_xy / N_total
    p_x = x_counts[x] / N_total
    p_y = y_counts[y] / N_total
    if p_xy > 0 and p_x > 0 and p_y > 0:
        mi += p_xy * math.log2(p_xy / (p_x * p_y))

print(f"  Informacao mutua (ultimos 8 bits): {mi:.6f} bits")
print(f"  (esperado ~0 para independentes, >0 para dependentes)")

# Monte Carlo for MI
random.seed(456)
N_SIM = 100_000
count_mi = 0
for _ in range(N_SIM):
    perm_y = [p[1] for p in last_8_pairs]
    random.shuffle(perm_y)
    perm_pairs = list(zip([p[0] for p in last_8_pairs], perm_y))

    joint_p = Counter(perm_pairs)
    mi_p = 0
    for (x, y), c in joint_p.items():
        pxy = c / N_total
        px = x_counts[x] / N_total
        py_p = sum(1 for pp in perm_pairs if pp[1] == y) / N_total
        if pxy > 0 and px > 0 and py_p > 0:
            mi_p += pxy * math.log2(pxy / (px * py_p))
    if mi_p >= mi:
        count_mi += 1

p_mi = count_mi / N_SIM
print(f"  P-value MI: {p_mi:.6f}")
print(f"  {'DEPENDENCIA DETECTADA!' if p_mi < 0.05 else 'Independentes (sem dependencia)'}")

# =====================================================================
# RESUMO
# =====================================================================
print(f"\n{'='*70}")
print("RESUMO DOS TESTES DE DERIVACAO")
print(f"{'='*70}")

print(f"""
  Hipotese testada                    Resultado
  ---------------------------------   --------
  key_i = seed + i (linear)           {'Confirmada' if linear_matches == total_tests else 'Rejeitada'}
  Bits baixos correlacionados         {'Sim (p<0.05)' if p_val < 0.05 else 'Nao'}
  XOR ratio anomalo                   {'Sim (p<0.05)' if p_xor < 0.05 else 'Nao'}
  Informacao mutua nos LSBs           {'Sim (p<0.05)' if p_mi < 0.05 else 'Nao'}
""")

if p_val < 0.05 or p_xor < 0.05 or p_mi < 0.05 or linear_matches == total_tests:
    print("  >>> ESTRUTURA DETECTADA NA DERIVACAO! <<<")
    print("  Os bits baixos das chaves NAO sao independentes.")
    print("  Isso pode ser explorado para reduzir o espaco de busca.")
else:
    print("  >>> NENHUMA ESTRUTURA DETECTADA <<<")
    print("  A derivacao parece ser hash-based (BIP32 ou similar).")
    print("  Cada chave e efetivamente independente das demais.")
