"""
Kangaroo de Pollard CORRETO para interval-DLP em secp256k1.

Resolve k em [a, b] dado Q = k*G (pubkey conhecida). Só funciona se k ESTIVER em [a,b].

Uso:
  Auto-teste (planta chave aleatória num intervalo de 2^BITS e resolve):
      python kangaroo_solve.py --selftest 40
  Alvo definido por você (pubkey comprimida 02/03... ou 04..., e o range em hex):
      python kangaroo_solve.py <pubkey_hex> <start_hex> <end_hex>

Observações honestas:
  - Custo ~ sqrt(b-a) passos. 2^40 -> ~2^20 passos -> segundos/min em CPU.
  - Se a chave NÃO estiver no intervalo, roda e não acha nada (esperado).
  - Range cheio (2^256, ex.: chave Satoshi) é inviável: ~2^128. Não tente.

Python stdlib puro.
"""
import sys, random, math, time

P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)

def inv(a): return pow(a, P - 2, P)
def add(A, B):
    if A is None: return B
    if B is None: return A
    x1, y1 = A; x2, y2 = B
    if x1 == x2 and (y1 + y2) % P == 0: return None
    s = (3*x1*x1) * inv(2*y1) % P if A == B else (y2 - y1) * inv((x2 - x1) % P) % P
    x3 = (s*s - x1 - x2) % P
    return (x3, (s*(x1 - x3) - y1) % P)
def neg(A): return None if A is None else (A[0], (-A[1]) % P)
def mul(k, Q=G):
    R = None; k %= N
    while k > 0:
        if k & 1: R = add(R, Q)
        Q = add(Q, Q); k >>= 1
    return R

def sqrt_mod(a):
    a %= P
    if a == 0: return 0
    if pow(a, (P-1)//2, P) != 1: return None
    return pow(a, (P+1)//4, P)   # P % 4 == 3

def decompress(hexstr):
    hexstr = "".join(c for c in hexstr if c in "0123456789abcdefABCDEF")
    b = bytes.fromhex(hexstr)
    if b[0] == 0x04:
        return (int.from_bytes(b[1:33], "big"), int.from_bytes(b[33:65], "big"))
    x = int.from_bytes(b[1:], "big")
    y = sqrt_mod((pow(x, 3, P) + 7) % P)
    if y is None: raise ValueError("ponto invalido")
    if (y & 1) != (b[0] & 1): y = (P - y) % P
    return (x, y)

def kangaroo(Q, a, b, verbose=True):
    W = b - a
    if W <= 0: raise ValueError("intervalo invalido")
    Qp = add(Q, neg(mul(a)))          # Q' = Q - a*G ; resolve d em [0, W]
    bits = W.bit_length()
    t = max(8, bits // 2 + 4)         # nº de saltos
    jumps = [1 << i for i in range(t)]
    jpts = [mul(s) for s in jumps]
    mean = sum(jumps) / t
    dp_bits = max(1, bits // 2 - 6)
    dp_mask = (1 << dp_bits) - 1

    tame = {}; wild = {}
    # tame parte do meio do intervalo; wild parte do alvo
    Tp = mul(W // 2); tval = W // 2
    Wp = Qp;          wbase = 0; wval = 0
    steps = 0
    max_steps = int(16 * math.isqrt(W)) + 1000
    expected = int(1.6 * math.isqrt(W))    # passos típicos até resolver
    t0 = time.time(); last = t0

    def fmt_eta(sec):
        if sec < 0: return "?"
        for u, s in (("anos",3.15e7),("dias",86400),("h",3600),("min",60)):
            if sec >= s: return f"{sec/s:.1f} {u}"
        return f"{sec:.0f}s"

    while True:
        steps += 1
        # --- tame ---
        if Tp is not None and (Tp[0] & dp_mask) == 0:
            if Tp[0] in wild:
                d = (tval - wild[Tp[0]]) % N
                if 0 <= d <= W and mul(a + d) == Q:
                    if verbose: sys.stdout.write("\n")
                    return a + d, steps, time.time()-t0
            tame[Tp[0]] = tval
        i = Tp[0] % t if Tp else 0
        Tp = add(Tp, jpts[i]); tval += jumps[i]
        # --- wild ---
        if Wp is not None and (Wp[0] & dp_mask) == 0:
            tot = wbase + wval
            if Wp[0] in tame:
                d = (tame[Wp[0]] - tot) % N
                if 0 <= d <= W and mul(a + d) == Q:
                    if verbose: sys.stdout.write("\n")
                    return a + d, steps, time.time()-t0
            wild[Wp[0]] = tot
        i = Wp[0] % t if Wp else 0
        Wp = add(Wp, jpts[i]); wval += jumps[i]

        if steps > max_steps:
            # reinicia wild com offset pequeno aleatório (preserva relação via wbase)
            wbase = random.randrange(0, max(1, math.isqrt(W)))
            Wp = add(Qp, mul(wbase)); wval = 0
            max_steps += int(8 * math.isqrt(W))
        if verbose and steps % 20000 == 0:
            now = time.time(); el = now - t0
            rate = steps / el if el else 0
            dps = len(tame) + len(wild)
            prog = 100.0 * steps / expected if expected else 0
            eta = (expected - steps) / rate if rate else -1
            sys.stdout.write(
                f"\r  {steps:>12,} passos | {rate:>8,.0f}/s | {el:>6.0f}s | "
                f"DPs {dps:>6,} | {prog:6.3f}% do esperado | ETA {fmt_eta(eta):>10}   ")
            sys.stdout.flush()

def selftest(bits):
    a = 1 << bits
    b = (1 << (bits + 1)) - 1
    k = random.randrange(a, b + 1)
    Q = mul(k)
    print(f"[auto-teste] intervalo 2^{bits}..2^{bits+1}, chave plantada k={hex(k)}")
    print(f"  pubkey alvo: {('02' if Q[1]%2==0 else '03') + format(Q[0],'064x')}")
    res = kangaroo(Q, a, b)
    if res:
        found, steps, dt = res
        K = steps / math.isqrt(b - a)
        ok = (found == k)
        print(f"  RESOLVIDO: k={hex(found)}  correto={ok}")
        print(f"  passos={steps}  tempo={dt:.1f}s  K={K:.2f} (sqrt-ops; ~1.5-2.5 esperado)")
    else:
        print("  nao resolveu (nao deveria acontecer)")

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        selftest(int(sys.argv[2]))
    elif len(sys.argv) == 4:
        pub, sa, sb = sys.argv[1], sys.argv[2], sys.argv[3]
        Q = decompress(pub)
        a = int(sa, 16); b = int(sb, 16)
        print(f"[alvo] pubkey={pub[:20]}...  range=[{sa}, {sb}]  largura~2^{(b-a).bit_length()}")
        if (b - a).bit_length() > 50:
            print("  AVISO: intervalo > 2^50 — pode levar muito tempo em CPU.")
        res = kangaroo(Q, a, b)
        if res:
            found, steps, dt = res
            print(f"  RESOLVIDO: k = {hex(found)}  (passos={steps}, {dt:.1f}s)")
            print(f"  decimal: {found}")
        else:
            print("  nao encontrado (chave provavelmente fora do intervalo).")
    else:
        print("=== Kangaroo interativo ===")
        pub = input("Chave pública (hex 02/03/04...): ").strip().lstrip("﻿").strip()
        nraw = input("Bits do range (ex: 30 -> 2^29..2^30 ; 135 -> 2^134..2^135): ")
        n = int("".join(c for c in nraw if c.isdigit()))
        a = 1 << (n - 1); b = (1 << n) - 1
        Q = decompress(pub)
        print(f"\nAlvo no range 2^{n-1}..2^{n}  (largura ~2^{(b-a).bit_length()})")
        if (b - a).bit_length() > 50:
            print("AVISO: > 2^50 — pode levar tempo enorme em CPU. Ctrl+C para parar.\n")
        res = kangaroo(Q, a, b)
        if res:
            found, steps, dt = res
            print(f"\n  RESOLVIDO: k = {hex(found)}")
            print(f"  decimal:   {found}")
            print(f"  passos={steps:,}  tempo={dt:.1f}s")
        else:
            print("\n  nao encontrado (chave fora do intervalo).")
