"""
Força bruta de um range contra uma pubkey. Varre incrementalmente (P += G).
Uso:
  python brute_range.py            -> varre 2^29..2^30 contra a pubkey do gênese
  python brute_range.py 29 30      -> idem (bits inicio, fim)
  python brute_range.py 24 25      -> fatia pequena pra medir velocidade primeiro
  python brute_range.py 29 30 <pubkey_hex>  -> outra pubkey

Acha nada = a chave NÃO está no range (prova definitiva pra ranges pequenos).
"""
import sys, time

P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G  = (Gx, Gy)
GEN = "04678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5f"

def inv(a): return pow(a, P-2, P)
def add(A, B):
    if A is None: return B
    if B is None: return A
    x1,y1=A; x2,y2=B
    if x1==x2 and (y1+y2)%P==0: return None
    s=(3*x1*x1)*inv(2*y1)%P if A==B else (y2-y1)*inv((x2-x1)%P)%P
    x3=(s*s-x1-x2)%P
    return (x3,(s*(x1-x3)-y1)%P)
def mul(k,Q=G):
    R=None
    while k>0:
        if k&1: R=add(R,Q)
        Q=add(Q,Q); k>>=1
    return R

def target_x(pub):
    pub="".join(c for c in pub if c in "0123456789abcdefABCDEF")
    b=bytes.fromhex(pub)
    return int.from_bytes(b[1:33],"big")  # X (vale p/ 04... e 02/03...)

def main():
    sb = int(sys.argv[1]) if len(sys.argv)>1 else 29
    eb = int(sys.argv[2]) if len(sys.argv)>2 else 30
    pub = sys.argv[3] if len(sys.argv)>3 else GEN
    tx = target_x(pub)
    start = 1<<sb; end = 1<<eb
    total = end-start
    print(f"Varrendo k de 2^{sb} a 2^{eb}  ({total:,} chaves)")
    print(f"Alvo x = {hex(tx)[:22]}...\n")

    P0 = mul(start)        # ponto inicial
    cur = P0; k = start
    t0 = time.time(); rep = 1<<19
    while k < end:
        if cur is not None and cur[0] == tx:
            print(f"\n!!! ACHOU: k = {hex(k)}  ({k}) !!!")
            return
        cur = add(cur, G); k += 1
        if (k & (rep-1)) == 0:
            done = k-start; el = time.time()-t0
            rate = done/el if el else 0
            eta = (total-done)/rate if rate else 0
            sys.stdout.write(f"\r  {done:,}/{total:,} | {rate:,.0f}/s | {el:.0f}s | ETA {eta/60:.1f} min   ")
            sys.stdout.flush()
    print(f"\n\nVARREDURA COMPLETA. Nada encontrado.")
    print(f"=> a chave NÃO está em 2^{sb}..2^{eb}. Questão fechada (prova exaustiva).")

if __name__=="__main__":
    main()
