"""
Busca os coinbases dos blocos 1..50, extrai as pubkeys (P2PK) e salva.
Objetivo: analisar se há vínculo de geração entre as primeiras chaves do Satoshi.
Fonte: blockstream.info API (pública, sem chave). Python stdlib puro.
"""
import urllib.request, json, time, os

API = "https://blockstream.info/api"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "satoshi_early_pubkeys.json")

def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": "research"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = r.read().decode()
    return d if raw else json.loads(d)

def extract_pubkey(script_hex):
    # P2PK: 41 <65-byte pubkey> ac   (uncompressed)  ou  21 <33> ac (comprimida)
    s = script_hex.lower()
    if s.startswith("41") and s.endswith("ac") and len(s) == 2 + 130 + 2:
        return s[2:-2]
    if s.startswith("21") and s.endswith("ac") and len(s) == 2 + 66 + 2:
        return s[2:-2]
    return None

def main():
    results = []
    for h in range(1, 51):
        try:
            bh = get(f"{API}/block-height/{h}", raw=True).strip()
            txs = get(f"{API}/block/{bh}/txs/0")   # primeiros 25 txs; coinbase = [0]
            cb = txs[0]
            vout = cb["vout"][0]
            script = vout["scriptpubkey"]
            pub = extract_pubkey(script)
            addr = vout.get("scriptpubkey_address") or vout.get("scriptpubkey_type")
            results.append({"height": h, "txid": cb["txid"], "address": addr,
                            "pubkey": pub, "type": vout.get("scriptpubkey_type")})
            print(f"  bloco {h:>3}: {vout.get('scriptpubkey_type'):>6}  pub={'sim' if pub else 'NAO'}  {addr}")
        except Exception as e:
            print(f"  bloco {h:>3}: ERRO {e}")
            results.append({"height": h, "error": str(e)})
        time.sleep(0.25)

    with open(OUT, "w") as f:
        json.dump(results, f, indent=2)
    npub = sum(1 for r in results if r.get("pubkey"))
    print(f"\nSalvo em {OUT}")
    print(f"Pubkeys P2PK extraidas: {npub}/50")

if __name__ == "__main__":
    main()
