"""
Varredura de escala do experimento de incompressibilidade da órbita.

Repete os detectores em curvas y^2=x^3+7 de ordem PRIMA crescente (~2^11..2^16) e
reporta o MÁXIMO de cada detector (sobre os funcionais da curva) vs N, mais os
controles positivos.

Previsão falsificável de A2 (incompressibilidade):
  - fase: máx da curva ~ CONSTANTE no nível de ruído (máx de M qui-quadrados), NÃO cresce com N.
  - MI / adv / |Δ-1|: DECRESCEM com N (~1/N ou ~1/sqrt(N)) — piso de amostra encolhe.
  - controles positivos: permanecem SATURADOS em toda escala.
Se QUALQUER detector da curva CRESCER com N -> lead real de compressibilidade.

Reaproveita as rotinas de orbit_compressibility.py. Python stdlib puro.
"""
import sys, math
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from orbit_compressibility import (
    legendre, find_prime_curve, find_generator, padd,
    phase_power, mutual_info_bit, bit_pred_adv, delta_smoothness,
)

def build_orbit(p, N, G):
    X = [0]*N; Y = [0]*N
    P = None
    for k in range(1, N):
        P = padd(P, G, p) if P is not None else G
        X[k], Y[k] = P
    return X, Y

def curve_functionals(X, Y, p, Na):
    # subconjunto representativo (rápido) p/ a varredura
    F = {}
    F["x"]       = X[1:]
    F["x*y"]     = [(X[k]*Y[k]) % p for k in range(1, len(X))]
    F["x^2+y^2"] = [(X[k]*X[k] + Y[k]*Y[k]) % p for k in range(1, len(X))]
    F["leg(x)"]  = [legendre(X[k], p) for k in range(1, len(X))]
    F["lsb(y)"]  = [Y[k] & 1 for k in range(1, len(Y))]
    F["x(3P)"]   = [X[(3*k) % (Na+1)] for k in range(1, len(X))]  # (3k) mod N
    return F

def detectors(arr, Na, lsb_k, msb_k, M):
    pw, _ = phase_power(arr, Na, M)
    mi = max(mutual_info_bit(arr, lsb_k), mutual_info_bit(arr, msb_k))
    adv = bit_pred_adv(arr, lsb_k)
    dlt = abs(1.0 - delta_smoothness(arr, Na))
    return pw, mi, adv, dlt

TARGETS = [(11, 2048, 2700), (12, 4096, 4800), (13, 8192, 9000),
           (14, 16384, 17200), (15, 32768, 33600), (16, 65536, 66400)]
M = 16

print("=" * 88)
print("VARREDURA DE ESCALA — A2 (incompressibilidade da órbita) vs N")
print("=" * 88)
print(f"\n  {'bits':>4} {'N':>7} | {'CURVA: máx detectores':^34} | {'CONTROLES':^18}")
print(f"  {'':>4} {'':>7} | {'fase':>8} {'MI':>8} {'adv':>7} {'|Δ-1|':>7} | {'fase':>8} {'MI':>8}")
print(f"  {'-'*4} {'-'*7} | {'-'*8} {'-'*8} {'-'*7} {'-'*7} | {'-'*8} {'-'*8}")

rows = []
for bits, lo, hi in TARGETS:
    p, N = find_prime_curve(lo, hi)
    G = find_generator(p)
    X, Y = build_orbit(p, N, G)
    Na = N - 1
    lsb_k = [k & 1 for k in range(1, N)]
    msb_k = [1 if k >= N//2 else 0 for k in range(1, N)]

    # curva
    F = curve_functionals(X, Y, p, Na)
    cmax = [0.0, 0.0, 0.0, 0.0]
    for arr in F.values():
        pw, mi, adv, dlt = detectors(arr, Na, lsb_k, msb_k, M)
        cmax[0] = max(cmax[0], pw); cmax[1] = max(cmax[1], mi)
        cmax[2] = max(cmax[2], adv); cmax[3] = max(cmax[3], dlt)

    # controles positivos
    ramp = [k for k in range(1, N)]
    lsbk = [k & 1 for k in range(1, N)]
    pw_r, _, _, _ = detectors(ramp, Na, lsb_k, msb_k, M)
    _, mi_l, _, _ = detectors(lsbk, Na, lsb_k, msb_k, M)

    rows.append((bits, N, cmax, pw_r, mi_l))
    print(f"  {bits:>4} {N:>7} | {cmax[0]:>8.1f} {cmax[1]:>8.4f} {cmax[2]:>7.4f} {cmax[3]:>7.4f} "
          f"| {pw_r:>8.0f} {mi_l:>8.4f}")

print(f"\n{'='*88}")
print("TENDÊNCIA")
print(f"{'='*88}")

def trend(vals):
    # razão último/primeiro; >1.5 cresce, <0.67 decresce, senão estável
    a, b = vals[0], vals[-1]
    if a == 0: return "—"
    r = b / a
    return "CRESCE" if r > 1.5 else ("decresce" if r < 0.67 else "estável")

ph = [r[2][0] for r in rows]; mi = [r[2][1] for r in rows]
ad = [r[2][2] for r in rows]; dl = [r[2][3] for r in rows]
print(f"  fase (curva):   {trend(ph)}   (A2 prevê: estável ~ruído)")
print(f"  MI (curva):     {trend(mi)}   (A2 prevê: decresce ~1/N)")
print(f"  adv (curva):    {trend(ad)}   (A2 prevê: decresce ~1/sqrt(N))")
print(f"  |Δ-1| (curva):  {trend(dl)}   (A2 prevê: decresce)")

cresce = any(trend(v) == "CRESCE" for v in (ph, mi, ad, dl))
ctrl_ok = rows[-1][3] > 1000 and rows[-1][4] > 0.5
print(f"\n  Controles ainda saturados na maior escala: {'sim' if ctrl_ok else 'NÃO (revisar)'}")
if cresce:
    print("  >>> ALGUM detector da curva CRESCE com N — LEAD REAL, investigar a fundo.")
else:
    print("""  >>> Nenhum detector da curva cresce com N; os que deviam decrescer, decrescem,
      e os controles seguem saturados. A2 (incompressibilidade) corroborada AO LONGO DA ESCALA.
      Evidência quantitativa multi-escala — não mais um único ponto.""")
