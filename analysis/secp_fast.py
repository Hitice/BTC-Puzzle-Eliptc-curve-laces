"""secp256k1 minimo com multiplicacao de base fixa (comb w=8).

Somente biblioteca padrao. Usado pelas varreduras de seed, onde o custo por
candidato e dominado por uma unica multiplicacao k*G.
"""

P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)


def inv(x, m=P):
    return pow(x, m - 2, m)


def add_affine(A, B):
    if A is None:
        return B
    if B is None:
        return A
    x1, y1 = A
    x2, y2 = B
    if x1 == x2:
        if (y1 + y2) % P == 0:
            return None
        s = (3 * x1 * x1) * inv(2 * y1) % P
    else:
        s = (y2 - y1) * inv((x2 - x1) % P) % P
    x3 = (s * s - x1 - x2) % P
    return (x3, (s * (x1 - x3) - y1) % P)


def mul_affine(k, Pt):
    """Multiplicacao generica (lenta). Usada apenas fora do laco quente."""
    R = None
    k %= N
    while k > 0:
        if k & 1:
            R = add_affine(R, Pt)
        Pt = add_affine(Pt, Pt)
        k >>= 1
    return R


_W = 8
_WINDOWS = (256 + _W - 1) // _W
_TABLE = None


def _build_table():
    """_TABLE[w][d] = d * 2^(8w) * G, para d em 1..255, em coordenadas afins."""
    global _TABLE
    tbl = []
    base = G
    for _ in range(_WINDOWS):
        row = [None] * 256
        acc = None
        for d in range(1, 256):
            acc = add_affine(acc, base)
            row[d] = acc
        tbl.append(row)
        # base <<= 8
        for _ in range(_W):
            base = add_affine(base, base)
    _TABLE = tbl
    return tbl


def mul_g(k):
    """k*G em coordenadas afins, via comb de base fixa (Jacobiano interno)."""
    k %= N
    if k == 0:
        return None
    tbl = _TABLE if _TABLE is not None else _build_table()
    X, Y, Z = 0, 0, 0  # ponto no infinito em Jacobiano (Z == 0)
    w = 0
    while k:
        d = k & 0xFF
        k >>= 8
        if d:
            ax, ay = tbl[w][d]
            if Z == 0:
                X, Y, Z = ax, ay, 1
            else:
                # adicao mista Jacobiano + afim
                z2 = Z * Z % P
                u2 = ax * z2 % P
                s2 = ay * z2 % P * Z % P
                h = (u2 - X) % P
                r = (s2 - Y) % P
                if h == 0:
                    if r == 0:
                        # duplicacao
                        yy = Y * Y % P
                        s = 4 * X * yy % P
                        m = 3 * X * X % P
                        X2 = (m * m - 2 * s) % P
                        Y2 = (m * (s - X2) - 8 * yy * yy) % P
                        Z2 = 2 * Y * Z % P
                        X, Y, Z = X2, Y2, Z2
                    else:
                        X, Y, Z = 0, 0, 0
                else:
                    h2 = h * h % P
                    h3 = h2 * h % P
                    v = X * h2 % P
                    X3 = (r * r - h3 - 2 * v) % P
                    Y3 = (r * (v - X3) - Y * h3) % P
                    Z3 = Z * h % P
                    X, Y, Z = X3, Y3, Z3
        w += 1
    if Z == 0:
        return None
    zi = inv(Z)
    zi2 = zi * zi % P
    return (X * zi2 % P, Y * zi2 % P * zi % P)


def ser_compressed(pt):
    x, y = pt
    return bytes([2 + (y & 1)]) + x.to_bytes(32, "big")


def ser_uncompressed(pt):
    x, y = pt
    return b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")


def ser_xy(pt):
    """64 bytes sem prefixo — formato da MPK do Electrum antigo."""
    x, y = pt
    return x.to_bytes(32, "big") + y.to_bytes(32, "big")
