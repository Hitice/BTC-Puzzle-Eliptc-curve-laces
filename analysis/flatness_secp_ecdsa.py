"""
Terreno plano (sem gradiente) em:
  A) secp256k1 escala COMPLETA (k aleatório 256 bits): vizinho (k+d)G parece mais perto?
  B) ECDSA: r = x(nonce*G). nonce vizinho -> r vizinho? (proximidade vaza?)
Python stdlib puro.
"""
import random
P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G=(Gx,Gy)
def inv(a): return pow(a,P-2,P)
def add(A,B):
    if A is None: return B
    if B is None: return A
    x1,y1=A;x2,y2=B
    if x1==x2 and (y1+y2)%P==0: return None
    s=(3*x1*x1)*inv(2*y1)%P if A==B else (y2-y1)*inv((x2-x1)%P)%P
    x3=(s*s-x1-x2)%P
    return (x3,(s*(x1-x3)-y1)%P)
def mul(k,Q=G):
    R=None
    while k>0:
        if k&1:R=add(R,Q)
        Q=add(Q,Q);k>>=1
    return R
def bits(a,b): return bin(a^b).count("1")
rng=random.Random(7)

print("A) secp256k1 ESCALA COMPLETA — k aleatório 256 bits")
k=rng.randrange(1,N); xk=mul(k)[0]
print(f"   k~2^{k.bit_length()}  |  bits diferentes de x(kG):")
print(f"   {'dist |Δ|':>12} | {'bits dif (de 256)':>18}")
for d in [1,2,10,1000,10**6,10**12,2**40]:
    ds=[bits(mul((k+ (1 if rng.random()<.5 else -1)*d)%N)[0], xk) for _ in range(8)]
    print(f"   {d:>12} | {sum(ds)/len(ds):>18.1f}")

print("\nB) ECDSA — r = x(nonce*G). nonce vizinho -> r vizinho?")
nonce=rng.randrange(1,N); r0=mul(nonce)[0]
print(f"   {'dist nonce':>12} | {'bits dif de r':>14}")
for d in [1,2,10,1000,10**6,2**40]:
    ds=[bits(mul((nonce+(1 if rng.random()<.5 else -1)*d)%N)[0], r0) for _ in range(8)]
    print(f"   {d:>12} | {sum(ds)/len(ds):>14.1f}")

print("\n  Veredito: ~128 bits dif em TODAS as distâncias nos dois casos =")
print("  terreno plano total. Proximidade NÃO vaza — nem na curva, nem no r do ECDSA.")
print("  (por isso ataque de nonce exige reuso/viés EXATO, nunca 'nonce parecido'.)")
