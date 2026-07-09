"""
Extensão GPU da varredura de incompressibilidade da órbita.

Mesma ciência do scale_sweep.py, mas com a BATERIA DE DETECTORES vetorizada para
rodar em GPU via CuPy (cai para NumPy/CPU automaticamente se CuPy não estiver presente).

Arquitetura:
  - construção da órbita kG  -> CPU (sequencial, reaproveita rotinas já validadas)
  - bateria de detectores    -> GPU/array (gargalo O(N*M), embaraçosamente paralelo)

AUTOVALIDAÇÃO: em bits=16 deve reproduzir a linha do scale_sweep.py (fase~9.6, MI~1e-4,
|Δ-1| pequeno). Se reproduzir, o caminho GPU está correto — a placa só muda a velocidade.

ATENÇÃO (honestidade): NÃO testei o caminho CuPy (não tenho GPU aqui). O caminho NumPy eu
posso raciocinar como correto; o código CuPy é idêntico (mesmas chamadas de array). A
autovalidação em bits=16 é justamente para você confirmar a correção na sua máquina.

Dependência: CuPy compatível com seu CUDA, p.ex.:
    pip install cupy-cuda12x      (CUDA 12.x)
    pip install cupy-cuda11x      (CUDA 11.x)
Sem CuPy, roda em CPU (NumPy) e ainda funciona — só mais lento.

Rodar:
    python analysis/gpu_orbit_sweep.py
    python analysis/gpu_orbit_sweep.py 16 18 20 22   (escolher as escalas em bits)

Campo pequeno (p < 2^31) -> aritmética cabe em int64; produtos cabem em float64 exato p/ os
detectores. Isto é ciência em curva-brinquedo; nada aqui ataca secp256k1.
"""
import sys, math
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---- backend de array: GPU (CuPy) com fallback CPU (NumPy) ----
BACKEND = "?"
try:
    import cupy as xp          # type: ignore
    try:
        _ = xp.zeros(1) + 1     # força init do device; falha se sem GPU utilizável
        BACKEND = "CuPy/GPU"
    except Exception:
        import numpy as xp      # type: ignore
        BACKEND = "NumPy/CPU (CuPy presente mas GPU indisponível)"
except Exception:
    import numpy as xp          # type: ignore
    BACKEND = "NumPy/CPU"

from orbit_compressibility import find_prime_curve, find_generator, padd, legendre

# ---------------- construção da órbita (CPU, validada) ----------------
def build_orbit(p, N, G):
    X = [0]*N; Y = [0]*N
    P = None
    for k in range(1, N):
        P = padd(P, G, p) if P is not None else G
        X[k], Y[k] = P
    return X[1:], Y[1:]   # descarta k=0 (infinito)

# ---------------- detectores vetorizados (GPU/CPU) ----------------
def to_rows(funcs):
    """funcs: dict nome->lista int (comprimento Na). Retorna (nomes, matriz F x Na float64)."""
    names = list(funcs.keys())
    M = xp.array([funcs[n] for n in names], dtype=xp.float64)
    return names, M

def phase_max(A, N, M):
    """Para cada linha (funcional), máx sobre harmônicos m=1..M de z=2(c^2+s^2)/||a||^2.
    a = linha centrada. Vetorizado: loop em m (baixa memória O(F*N))."""
    a = A - A.mean(axis=1, keepdims=True)
    na2 = (a * a).sum(axis=1)                      # ||a||^2 por funcional
    na2 = xp.where(na2 == 0, 1.0, na2)
    k = xp.arange(N - 1, dtype=xp.float64)         # k = 0..Na-1
    best = xp.zeros(a.shape[0], dtype=xp.float64)
    for m in range(1, M + 1):
        w = 2.0 * math.pi * m / N
        cosk = xp.cos(w * k); sink = xp.sin(w * k)
        c = (a * cosk).sum(axis=1)                  # F-vetor (sem cuBLAS)
        s = (a * sink).sum(axis=1)
        z = 2.0 * (c * c + s * s) / na2
        best = xp.maximum(best, z)
    return best                                    # F-vetor

def mutual_info(A, bit, nbins=8):
    """I(bin(g); bit) por funcional. bit: array {0,1} comprimento Na."""
    Na = A.shape[1]
    bit = xp.asarray(bit, dtype=xp.int64)
    n1 = int(bit.sum()); n0 = Na - n1
    py1 = n1 / Na; py0 = n0 / Na
    out = xp.zeros(A.shape[0], dtype=xp.float64)
    for i in range(A.shape[0]):
        row = A[i]
        lo = row.min(); hi = row.max()
        if hi == lo:
            continue
        b = ((row - lo) / (hi - lo) * nbins).astype(xp.int64)
        b = xp.clip(b, 0, nbins - 1)
        idx = b * 2 + bit
        joint = xp.bincount(idx, minlength=nbins * 2).astype(xp.float64)
        cg = joint.reshape(nbins, 2).sum(axis=1)   # contagem por bin de g
        I = 0.0
        jj = joint.reshape(nbins, 2)
        for gi in range(nbins):
            tot = float(cg[gi])
            if tot == 0: continue
            for bj, pyj in ((0, py0), (1, py1)):
                c = float(jj[gi, bj])
                if c > 0 and pyj > 0:
                    pxy = c / Na; px = tot / Na
                    I += pxy * math.log2(pxy / (px * pyj))
        out[i] = I
    return out

def separation(A, bit):
    """|média(g|bit=1) - média(g|bit=0)| / std(g) por funcional (point-biserial)."""
    bitf = xp.asarray(bit, dtype=xp.float64)
    n1 = float(bitf.sum()); n0 = A.shape[1] - n1
    rowsum = A.sum(axis=1)
    s1 = (A * bitf).sum(axis=1)                     # sem cuBLAS
    mean1 = s1 / max(n1, 1.0)
    mean0 = (rowsum - s1) / max(n0, 1.0)
    sd = A.std(axis=1)
    sd = xp.where(sd == 0, 1.0, sd)
    return xp.abs(mean1 - mean0) / sd

def delta_dev(A):
    """|1 - var(g[k+1]-g[k]) / (2 var(g))| por funcional."""
    d = xp.roll(A, -1, axis=1) - A
    vard = (d * d).mean(axis=1)
    var = A.var(axis=1)
    var = xp.where(var == 0, 1.0, var)
    return xp.abs(1.0 - vard / (2.0 * var))

# ---------------- funcionais da curva ----------------
def curve_functionals(X, Y, p, Na):
    N = Na + 1
    F = {}
    F["x"]       = X
    F["x*y"]     = [(X[i]*Y[i]) % p for i in range(Na)]
    F["x^2+y^2"] = [(X[i]*X[i] + Y[i]*Y[i]) % p for i in range(Na)]
    F["leg(x)"]  = [legendre(X[i], p) for i in range(Na)]
    F["lsb(y)"]  = [Y[i] & 1 for i in range(Na)]
    F["x(3P)"]   = [X[(3*(i+1)) % N - 1] for i in range(Na)]  # x(3P_k), k=i+1
    return F

def maxstats(funcs, N, M, lsb_k, msb_k):
    names, A = to_rows(funcs)
    ph = phase_max(A, N, M)
    mi = xp.maximum(mutual_info(A, lsb_k), mutual_info(A, msb_k))
    sp = separation(A, lsb_k)
    dl = delta_dev(A)
    f = lambda v: float(v.max())
    return f(ph), f(mi), f(sp), f(dl)

def main(bits_list):
    print("=" * 92)
    print(f"VARREDURA GPU — incompressibilidade da órbita | backend: {BACKEND}")
    print("=" * 92)
    print(f"\n  {'bits':>4} {'N':>9} | {'CURVA: máx detectores':^36} | {'CONTROLES':^18}")
    print(f"  {'':>4} {'':>9} | {'fase':>9} {'MI':>9} {'sep':>7} {'|Δ-1|':>7} | {'fase':>9} {'MI':>7}")
    print(f"  {'-'*4} {'-'*9} | {'-'*9} {'-'*9} {'-'*7} {'-'*7} | {'-'*9} {'-'*7}")

    M = 16
    rows = []
    for bits in bits_list:
        lo = 1 << bits
        hi = int(lo * 1.05) + 400
        p, N = find_prime_curve(lo, hi)
        if p >= (1 << 31):
            print(f"  {bits:>4} {N:>9} | pulado: p>=2^31 (overflow int64 nos detectores)")
            continue
        G = find_generator(p)
        X, Y = build_orbit(p, N, G)
        Na = N - 1
        lsb_k = [(i + 1) & 1 for i in range(Na)]
        msb_k = [1 if (i + 1) >= N // 2 else 0 for i in range(Na)]

        cph, cmi, csp, cdl = maxstats(curve_functionals(X, Y, p, Na), N, M, lsb_k, msb_k)

        # controles positivos
        ramp = {"ramp": [i + 1 for i in range(Na)]}
        lk   = {"lsbk": [(i + 1) & 1 for i in range(Na)]}
        rph, _, _, _ = maxstats(ramp, N, M, lsb_k, msb_k)
        _, lmi, _, _ = maxstats(lk, N, M, lsb_k, msb_k)

        rows.append((bits, N, cph, cmi, csp, cdl, rph, lmi))
        print(f"  {bits:>4} {N:>9} | {cph:>9.1f} {cmi:>9.4f} {csp:>7.4f} {cdl:>7.4f} "
              f"| {rph:>9.0f} {lmi:>7.4f}")

    if len(rows) >= 2:
        print(f"\n{'='*92}\nTENDÊNCIA\n{'='*92}")
        def trend(vals):
            a, b = vals[0], vals[-1]
            if a == 0: return "—"
            r = b / a
            return "CRESCE" if r > 1.5 else ("decresce" if r < 0.67 else "estável")
        ph = [r[2] for r in rows]; mi = [r[3] for r in rows]
        sp = [r[4] for r in rows]; dl = [r[5] for r in rows]
        print(f"  fase (curva):  {trend(ph)}   (A2 prevê: estável ~ruído)")
        print(f"  MI (curva):    {trend(mi)}   (A2 prevê: decresce)")
        print(f"  sep (curva):   {trend(sp)}   (A2 prevê: decresce ~1/sqrt(N))")
        print(f"  |Δ-1| (curva): {trend(dl)}   (A2 prevê: decresce)")
        cresce = any(trend(v) == "CRESCE" for v in (ph, mi, sp, dl))
        ctrl_ok = rows[-1][6] > 1000 and rows[-1][7] > 0.5
        print(f"\n  Controles saturados na maior escala: {'sim' if ctrl_ok else 'NÃO'}")
        print("  >>> " + ("ALGUM detector da curva CRESCE — LEAD REAL." if cresce
                          else "Curva achata, controles saturam. A2 corroborada nesta varredura."))

    print(f"\n  [validação] em bits=16 compare 'fase' (~9.6) e |Δ-1| com scale_sweep.py (CPU).")

if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]] or [16, 18, 20]
    main(args)
