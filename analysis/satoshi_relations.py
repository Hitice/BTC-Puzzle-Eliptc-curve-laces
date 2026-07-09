"""Vínculo de geração entre os 50 primeiros pubkeys do Satoshi: relações EC simples."""
import json, os
P=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
Gx=0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy=0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G=(Gx,Gy)
def inv(a):return pow(a,P-2,P)
def add(A,B):
 if A is None:return B
 if B is None:return A
 x1,y1=A;x2,y2=B
 if x1==x2 and (y1+y2)%P==0:return None
 s=(3*x1*x1)*inv(2*y1)%P if A==B else (y2-y1)*inv((x2-x1)%P)%P
 x3=(s*s-x1-x2)%P;return(x3,(s*(x1-x3)-y1)%P)
def neg(A):return None if A is None else (A[0],(-A[1])%P)
def parse(pk):
 b=bytes.fromhex(pk);return(int.from_bytes(b[1:33],'big'),int.from_bytes(b[33:65],'big'))

HERE=os.path.dirname(os.path.abspath(__file__))
D=json.load(open(os.path.join(HERE,"..","data","satoshi_early_pubkeys.json")))
pts={r['height']:parse(r['pubkey']) for r in D if r.get('pubkey')}
hs=sorted(pts)
print(f"n={len(pts)} pubkeys (blocos 1-50)\n")

# tabela t*G para t<2^20
M=1<<20; tab={}; R=None
for t in range(1,M):
 R=add(R,G); tab[R[0]]=t

# [A] cada Q = t*G pequeno?
hitsC=[(h,tab[pts[h][0]]) for h in hs if pts[h][0] in tab and add(None,None)==None and __import__('builtins')]
hitsC=[]
for h in hs:
 if pts[h][0] in tab:
  hitsC.append((h,tab[pts[h][0]]))
print(f"[A] Q=t*G (t<2^20): {hitsC if hitsC else 'nenhum'}")

# [B] diferenca pequena Q_j - Q_i = t*G?
hitsB=[]
for i in hs:
 for j in hs:
  if i>=j:continue
  Dp=add(pts[j],neg(pts[i]))
  if Dp and Dp[0] in tab:
   hitsB.append((i,j,tab[Dp[0]]))
print(f"[B] Q_j-Q_i=t*G pequeno: {hitsB if hitsB else 'nenhuma'}")

# [C] razao pequena Q_j = m*Q_i?  (m<2^14)
hitsA=[]
for i in hs:
 target={pts[j]:j for j in hs if j!=i}
 Rr=pts[i]
 for m in range(2,1<<14):
  Rr=add(Rr,pts[i])
  if Rr in target: hitsA.append((i,target[Rr],m))
print(f"[C] Q_j=m*Q_i (m<2^14): {hitsA if hitsA else 'nenhuma'}")

print("\nVeredito:",("VINCULO ENCONTRADO!" if (hitsA or hitsB or hitsC) else
 "nenhuma relacao EC simples -> chaves independentes (keypool aleatorio), como esperado."))
