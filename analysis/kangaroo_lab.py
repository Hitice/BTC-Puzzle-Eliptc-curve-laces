"""
Laboratorio de Kangaroo - bancada para testar se ALGUEM (IA inclusa) consegue
algo melhor que kangaroo. Resolve interval-DLP em instancias PEQUENAS (rapidas),
mede o K empirico = (operacoes de grupo) / sqrt(W).

Filosofia: qualquer "mercurio novo" tem que BATER o K medido aqui, em instancias
que conseguimos verificar. Sem isso, e so conversa. Energia ~zero (bits pequenos).

Implementa o kangaroo classico de Pollard (lambda) para [0, W) em secp256k1 puro.
"""
import os, random, math

P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)

def inv(x): return pow(x, P - 2, P)

def padd(A, B):
    if A is None: return B
    if B is None: return A
    x1, y1 = A; x2, y2 = B
    if x1 == x2 and (y1 + y2) % P == 0: return None
    if A == B:
        s = (3 * x1 * x1) * inv(2 * y1) % P
    else:
        s = (y2 - y1) * inv((x2 - x1) % P) % P
    x3 = (s * s - x1 - x2) % P
    return (x3, (s * (x1 - x3) - y1) % P)

def pmul(k, Pt):
    R = None
    while k > 0:
        if k & 1: R = padd(R, Pt)
        Pt = padd(Pt, Pt); k >>= 1
    return R

OPCOUNT = 0
def padd_counted(A, B):
    global OPCOUNT
    OPCOUNT += 1
    return padd(A, B)

def kangaroo(Q, W, jump_bits=None, dp_bits=None, max_factor=60, seed=None):
    """Resolve Q = k*G com k em [0, W). Retorna (k, ops) ou (None, ops)."""
    global OPCOUNT
    rng = random.Random(seed)
    sqrtW = int(math.isqrt(W))
    t = jump_bits if jump_bits else max(2, W.bit_length() // 2)
    jumps = [1 << i for i in range(t)]
    jpts = [pmul(j, G) for j in jumps]          # pre-computa saltos (custo unico)
    d = dp_bits if dp_bits else max(1, (W.bit_length() // 2) - 2)
    dp_mask = (1 << d) - 1

    def is_dp(pt): return pt is not None and (pt[0] & dp_mask) == 0
    def jump_idx(pt): return pt[0] % t

    OPCOUNT = 0
    max_ops = max_factor * sqrtW

    # Tame: comeca no meio do intervalo, distancia conhecida
    tame = {}
    Pt = pmul(W // 2, G); dt = W // 2
    Pw = Q; dw = 0
    wild_offset = 0

    while OPCOUNT < max_ops:
        # passo tame
        if is_dp(Pt):
            tame[Pt] = dt
        i = jump_idx(Pt)
        Pt = padd_counted(Pt, jpts[i]); dt += jumps[i]

        # passo wild
        if is_dp(Pw):
            if Pw in tame:
                k = (tame[Pw] - dw) % P
                if 0 <= k < W and pmul(k, G) == Q:
                    return k, OPCOUNT
            # se wild anda demais sem colidir, reinicia com offset pequeno
        i = jump_idx(Pw)
        Pw = padd_counted(Pw, jpts[i]); dw += jumps[i]

        # reinicio do wild se a distancia ultrapassar muito (evita escapar do alcance)
        if dw > 8 * sqrtW:
            wild_offset = rng.randrange(0, sqrtW)
            Pw = padd(Q, pmul(wild_offset, G)); dw = wild_offset

    return None, OPCOUNT

def bench(bits, trials=15, seed0=1):
    W = 1 << bits
    sqrtW = math.isqrt(W)
    ks_found = 0
    Ks = []
    rng = random.Random(seed0)
    for tr in range(trials):
        k_true = rng.randrange(0, W)
        Q = pmul(k_true, G)
        k, ops = kangaroo(Q, W, seed=seed0 + tr)
        if k == k_true:
            ks_found += 1
            Ks.append(ops / sqrtW)
    avg_K = sum(Ks) / len(Ks) if Ks else float('nan')
    return ks_found, trials, avg_K, sqrtW

if __name__ == "__main__":
    print("=" * 64)
    print("KANGAROO LAB - bancada de medicao de K")
    print("=" * 64)
    print("\n  K = operacoes_de_grupo / sqrt(W).  Menor K = melhor 'mercurio'.")
    print("  Limite teorico generico: K nao pode -> 0 (parede de Shoup).")
    print("  Classico ~2.0 | RCKangaroo (SOTA) ~1.15\n")
    print(f"  {'bits':>5}  {'sqrt(W)':>10}  {'resolvidos':>11}  {'K medio':>8}")
    print(f"  {'-'*5}  {'-'*10}  {'-'*11}  {'-'*8}")
    for bits in [24, 28, 32]:
        found, total, avgK, sW = bench(bits, trials=12)
        print(f"  {bits:>5}  {sW:>10}  {found:>4}/{total:<6}  {avgK:>8.3f}")

    print(f"""
  Como usar esta bancada para "criar algo melhor":
    1. Troque jump_idx / jumps por uma nova heuristica (ex: funcao de salto
       aprendida, ou distribuicao otimizada por busca/IA).
    2. Rode bench() e compare o K medio com o baseline acima.
    3. Se o novo K for consistentemente menor (mesmos bits, mesma verificacao),
       voce tem uma melhoria REAL de constante - publicavel.
    4. Se o K nao cair, a ideia nao vale - a bancada te diz na hora, barato.

  O que a bancada NAO pode mostrar: K -> 0 ou escala melhor que sqrt(W).
  Isso e proibido por teorema; nenhuma heuristica aqui muda o expoente.
""")
