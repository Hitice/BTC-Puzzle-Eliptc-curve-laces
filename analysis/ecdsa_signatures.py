"""
Análise de Assinaturas ECDSA dos Bitcoin Puzzles
Extrai assinaturas (r, s) das transações de saída e analisa fraquezas no nonce.
"""
import urllib.request
import urllib.error
import json
import hashlib
import struct
import time
import math
import os
from collections import Counter

# secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

TARGETS = {
    135: {
        "address": "16RGFo6hjq9ym6Pj7N5H7L1NR1rVPJyw2v",
        "pubkey": "02145d2611c823a396ef6712ce0f712f09b9b4f3135e3e0aa3230fb9b6d08d1e16"
    },
    140: {
        "address": "1QKBaU6WAeycb3DbKbLBkX7vJiaS8r42Xo",
        "pubkey": "031f6a332d3c5c4f2de2378c012f429cd109ba07d69690c6c701b6bb87860d6640"
    },
    145: {
        "address": "19GpszRNUej5yYqxXoLnbZWKew3KdVLkXg",
        "pubkey": "03afdda497369e219a2c1c369954a930e4d3740968e5e4352475bcffce3140dae5"
    },
    150: {
        "address": "1MUJSJYtGPVGkBCTqGspnxyHahpt5Te8jy",
        "pubkey": "03137807790ea7dc6e97901c2bc87411f45ed74a5629315c4e4b03a0a102250c49"
    },
    155: {
        "address": "1AoeP37TmHdFh8uN72fu9AqgtLrUwcv2wJ",
        "pubkey": "035cd1854cae45391ca4ec428cc7e6c7d9984424b954209a8eea197b9e364c05f6"
    },
    160: {
        "address": "1NBC8uXJy1GiJ6drkiZa1WuKn51ps7EPTv",
        "pubkey": "02e0a8b039282faf6fe0fd769cfbc4b6b4cf8758ba68220eac420e32b91ddfa673"
    },
}

# Include solved puzzles that had outgoing tx (for cross-reference)
SOLVED_WITH_TX = {
    65: {
        "address": "18ZMbwUFLMHoZBbfpCjUJQTCMCbktshgpe",
        "pubkey": "0230210c23b1a047bc9bdbb13448e67deddc108946de6de639bcc75d47c0216b1b",
        "privkey": 0x1a838b13505b26867
    },
    70: {
        "address": "19YZECXj3SxEZMoUeJ1yiPsw8xANe7M7QR",
        "pubkey": "0290e6900a58d33393bc1097b5aed31f2e4e7cbd3e5466af958665bc0121248483",
        "privkey": 0x349b84b6431a6c4ef1
    },
    75: {
        "address": "1J36UjUByGroXcCvmj13U6uwaVv9caEeAt",
        "pubkey": "03726b574f193e374686d8e12bc6e4142adeb06770e0a2856f5e4ad89f66044755",
        "privkey": 0x4c5ce114686a1336e07
    },
    80: {
        "address": "1BCf6rHUW6m3iH2ptsvnjgLruAiPQQepLe",
        "pubkey": "037e1238f7b1ce757df94faa9a2eb261bf0aeb9f84dbf81212104e78931c2a19dc",
        "privkey": 0xea1a5c66dcc11b5ad180
    },
    85: {
        "address": "1Kh22PvXERd2xpTQk3ur6pPEqFeckCJfAr",
        "pubkey": "0329c4574a4fd8c810b7e42a4b398882b381bcd85e40c6883712912d167c83e73a",
        "privkey": 0x11720c4f018d51b8cebba8
    },
    90: {
        "address": "1L12FHH2FHjvTviyanuiFVfmzCy46RRATU",
        "pubkey": "035c38bd9ae4b10e8a250857006f3cfd98ab15a6196d9f4dfd25bc7ecc77d788d5",
        "privkey": 0x2ce00bb2136a445c71e85bf
    },
    95: {
        "address": "19eVSDuizydXxhohGh8Ki9WY9KsHdSwoQC",
        "pubkey": "02967a5905d6f3b420959a02789f96ab4c3223a2c4d2762f817b7895c5bc88a045",
        "privkey": 0x527a792b183c7f64a0e8b1f4
    },
    100: {
        "address": "1KCgMv8fo2TPBpddVi9jqmMmcne9uSNJ5F",
        "pubkey": "03d2063d40402f030d4cc71331468827aa41a8a09bd6fd801ba77fb64f8e67e617",
        "privkey": 0xaf55fc59c335c8ec67ed24826
    },
    130: {
        "address": "1Fo65aKq8s8iquMt6weF1rku1moWVEd5Ua",
        "pubkey": "03633cbe3ec02b9401c5effa144c5b4d22f87940259634858fc7e59b1c09937852",
        "privkey": 0x33e7665705359f04f28b88cf897c603c9
    },
}

def api_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    ERRO: {e}")
                return None

def api_get_raw(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    ERRO: {e}")
                return None

def decode_der_signature(der_hex):
    """Decode DER-encoded ECDSA signature to (r, s)."""
    data = bytes.fromhex(der_hex)
    if data[0] != 0x30:
        return None, None
    total_len = data[1]
    idx = 2

    if data[idx] != 0x02:
        return None, None
    r_len = data[idx + 1]
    idx += 2
    r = int.from_bytes(data[idx:idx + r_len], 'big')
    idx += r_len

    if data[idx] != 0x02:
        return None, None
    s_len = data[idx + 1]
    idx += 2
    s = int.from_bytes(data[idx:idx + s_len], 'big')

    return r, s

def parse_scriptsig(script_hex):
    """Extract signature and pubkey from P2PKH scriptSig."""
    data = bytes.fromhex(script_hex)
    if len(data) < 2:
        return None, None, None

    idx = 0
    sig_len = data[idx]
    idx += 1
    if idx + sig_len > len(data):
        return None, None, None

    sig_with_hashtype = data[idx:idx + sig_len]
    sighash_type = sig_with_hashtype[-1]
    sig_der = sig_with_hashtype[:-1].hex()
    idx += sig_len

    if idx >= len(data):
        return sig_der, sighash_type, None

    pk_len = data[idx]
    idx += 1
    pubkey = data[idx:idx + pk_len].hex()

    return sig_der, sighash_type, pubkey

def double_sha256(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def get_outgoing_txs(address, puzzle_num):
    """Get transactions where address is an input (outgoing)."""
    print(f"\n  Buscando transacoes de #{puzzle_num} ({address})...")

    url = f"https://blockstream.info/api/address/{address}/txs"
    txs = api_get(url)
    if not txs:
        url = f"https://mempool.space/api/address/{address}/txs"
        txs = api_get(url)
    if not txs:
        return []

    outgoing = []
    for tx in txs:
        for vin in tx.get("vin", []):
            prevout = vin.get("prevout", {})
            if prevout and prevout.get("scriptpubkey_address") == address:
                outgoing.append(tx)
                break

    print(f"    Total de transacoes: {len(txs)}")
    print(f"    Transacoes de saida: {len(outgoing)}")
    return outgoing

def extract_signatures(txs, target_address):
    """Extract all ECDSA signatures from outgoing transactions."""
    sigs = []

    for tx in txs:
        txid = tx.get("txid", "?")
        for i, vin in enumerate(tx.get("vin", [])):
            prevout = vin.get("prevout", {})
            if not prevout or prevout.get("scriptpubkey_address") != target_address:
                continue

            scriptsig = vin.get("scriptsig", "")
            witness = vin.get("witness", [])

            sig_der = None
            sighash_type = None
            pubkey = None

            if scriptsig:
                sig_der, sighash_type, pubkey = parse_scriptsig(scriptsig)
            elif witness and len(witness) >= 2:
                sig_with_ht = witness[0]
                sig_bytes = bytes.fromhex(sig_with_ht)
                sighash_type = sig_bytes[-1]
                sig_der = sig_bytes[:-1].hex()
                pubkey = witness[1]

            if sig_der:
                r, s = decode_der_signature(sig_der)
                if r and s:
                    sigs.append({
                        "txid": txid,
                        "input_idx": i,
                        "r": r,
                        "s": s,
                        "r_hex": format(r, '064x'),
                        "s_hex": format(s, '064x'),
                        "sighash_type": sighash_type,
                        "pubkey": pubkey,
                        "sig_der": sig_der,
                    })

    return sigs

def analyze_signatures(all_sigs, puzzle_label):
    """Analyze signatures for nonce weaknesses."""
    print(f"\n{'='*70}")
    print(f"  ANALISE: {puzzle_label}")
    print(f"  Total de assinaturas extraidas: {len(all_sigs)}")
    print(f"{'='*70}")

    if not all_sigs:
        print("  Nenhuma assinatura encontrada.")
        return {}

    results = {}

    # --- 1. Nonce Reuse Check ---
    print(f"\n  [1] VERIFICACAO DE REUTILIZACAO DE NONCE (r duplicado)")
    r_values = [sig["r"] for sig in all_sigs]
    r_counts = Counter(r_values)
    duplicates = {r: c for r, c in r_counts.items() if c > 1}

    if duplicates:
        print(f"  !!! NONCE REUTILIZADO ENCONTRADO !!!")
        for r_val, count in duplicates.items():
            print(f"      r = {format(r_val, '064x')}")
            print(f"      Aparece em {count} assinaturas")
            matching = [s for s in all_sigs if s["r"] == r_val]
            for m in matching:
                print(f"        txid: {m['txid'][:16]}... input {m['input_idx']}")
            print(f"      >>> CHAVE PRIVADA PODE SER RECUPERADA TRIVIALMENTE <<<")
        results["nonce_reuse"] = True
    else:
        print(f"  Todos os {len(r_values)} valores de r sao unicos. Sem reutilizacao.")
        results["nonce_reuse"] = False

    # --- 2. r-value Analysis ---
    print(f"\n  [2] ANALISE DOS VALORES DE r")

    for sig in all_sigs:
        r = sig["r"]
        r_bits = r.bit_length()
        r_hex = sig["r_hex"]

        # Check for small r (would indicate small k)
        if r_bits < 200:
            print(f"  !!! r PEQUENO DETECTADO: {r_bits} bits (txid: {sig['txid'][:16]}...)")
            print(f"      Pode indicar nonce k pequeno!")

        # Check leading zeros in r
        leading_zeros = len(r_hex) - len(r_hex.lstrip('0'))
        if leading_zeros > 4:
            print(f"  !!! r com {leading_zeros} zeros iniciais (txid: {sig['txid'][:16]}...)")

    # r statistics
    r_bitlengths = [sig["r"].bit_length() for sig in all_sigs]
    avg_rbits = sum(r_bitlengths) / len(r_bitlengths)
    print(f"\n  Comprimento medio de r: {avg_rbits:.1f} bits (esperado ~256)")
    print(f"  Min: {min(r_bitlengths)} bits, Max: {max(r_bitlengths)} bits")

    # --- 3. s-value Analysis ---
    print(f"\n  [3] ANALISE DOS VALORES DE s")

    s_values = [sig["s"] for sig in all_sigs]
    half_order = N_ORDER // 2

    low_s_count = sum(1 for s in s_values if s <= half_order)
    print(f"  s <= N/2 (low-s): {low_s_count}/{len(s_values)}")
    print(f"  (BIP-62 exige low-s; indica software moderno se todos low-s)")
    results["all_low_s"] = (low_s_count == len(s_values))

    s_bitlengths = [s.bit_length() for s in s_values]
    avg_sbits = sum(s_bitlengths) / len(s_bitlengths)
    print(f"  Comprimento medio de s: {avg_sbits:.1f} bits")

    # --- 4. Byte-level bias in r (nonce bias detection) ---
    print(f"\n  [4] DISTRIBUICAO DE BYTES DO NONCE (via r)")
    print(f"  (r = k*G mod p, onde k e o nonce)")

    all_r_bytes = []
    for sig in all_sigs:
        r_bytes = sig["r"].to_bytes(32, 'big')
        all_r_bytes.extend(r_bytes)

    if len(all_r_bytes) >= 32:
        byte_counts = Counter(all_r_bytes)
        expected = len(all_r_bytes) / 256

        chi2 = sum((byte_counts.get(i, 0) - expected)**2 / expected for i in range(256))
        df = 255
        # Approximate chi2 test
        z_chi2 = (chi2 - df) / math.sqrt(2 * df)
        print(f"  Total bytes analisados: {len(all_r_bytes)}")
        print(f"  Chi2 = {chi2:.2f} (df={df})")
        print(f"  Z-score = {z_chi2:.3f} ({'ANOMALO' if abs(z_chi2) > 3 else 'NORMAL'})")

        # Check MSB of r values (most significant byte)
        msb_values = [sig["r"].to_bytes(32, 'big')[0] for sig in all_sigs]
        print(f"\n  MSB dos valores de r:")
        msb_counts = Counter(msb_values)
        for byte_val, count in sorted(msb_counts.items()):
            print(f"    0x{byte_val:02x}: {count}x")

    # --- 5. Sighash type ---
    print(f"\n  [5] TIPO DE SIGHASH")
    ht_counts = Counter(sig["sighash_type"] for sig in all_sigs)
    for ht, count in ht_counts.items():
        ht_name = {1: "SIGHASH_ALL", 2: "SIGHASH_NONE", 3: "SIGHASH_SINGLE",
                   0x81: "SIGHASH_ALL|ANYONECANPAY"}.get(ht, f"UNKNOWN(0x{ht:02x})")
        print(f"  {ht_name}: {count}x")

    # --- 6. Public key consistency ---
    print(f"\n  [6] CONSISTENCIA DE CHAVE PUBLICA")
    pubkeys = set(sig["pubkey"] for sig in all_sigs if sig["pubkey"])
    print(f"  Chaves publicas distintas: {len(pubkeys)}")
    for pk in pubkeys:
        print(f"    {pk}")

    # --- 7. Signature size analysis (DER encoding) ---
    print(f"\n  [7] TAMANHO DAS ASSINATURAS DER")
    der_sizes = [len(sig["sig_der"]) // 2 for sig in all_sigs]
    size_counts = Counter(der_sizes)
    for size, count in sorted(size_counts.items()):
        print(f"    {size} bytes: {count}x")
    results["der_sizes"] = dict(size_counts)

    return results

def cross_puzzle_analysis(all_puzzle_sigs):
    """Cross-reference analysis across all puzzles."""
    print(f"\n\n{'='*70}")
    print("ANALISE CRUZADA ENTRE PUZZLES")
    print(f"{'='*70}")

    all_sigs = []
    for puzzle_num, sigs in all_puzzle_sigs.items():
        for sig in sigs:
            sig["puzzle"] = puzzle_num
            all_sigs.append(sig)

    if not all_sigs:
        print("  Nenhuma assinatura coletada.")
        return

    print(f"\n  Total de assinaturas coletadas: {len(all_sigs)}")

    # Cross-puzzle nonce reuse
    print(f"\n  [A] REUTILIZACAO DE NONCE ENTRE PUZZLES DIFERENTES")
    r_to_puzzles = {}
    for sig in all_sigs:
        r = sig["r"]
        if r not in r_to_puzzles:
            r_to_puzzles[r] = []
        r_to_puzzles[r].append(sig["puzzle"])

    cross_reuse = {r: puzzles for r, puzzles in r_to_puzzles.items()
                   if len(set(puzzles)) > 1}
    if cross_reuse:
        print(f"  !!! REUTILIZACAO CRUZADA ENCONTRADA !!!")
        for r_val, puzzles in cross_reuse.items():
            print(f"      r = {format(r_val, '064x')[:32]}...")
            print(f"      Puzzles: {sorted(set(puzzles))}")
            print(f"      >>> RELACAO ENTRE CHAVES PODE SER EXPLORADA <<<")
    else:
        print(f"  Nenhuma reutilizacao cruzada.")

    # Check if all r values are unique globally
    all_r = [sig["r"] for sig in all_sigs]
    unique_r = len(set(all_r))
    print(f"  r unicos: {unique_r}/{len(all_r)}")

    # R-value bit pattern comparison
    print(f"\n  [B] COMPARACAO DE PADROES DE r ENTRE PUZZLES")
    for puzzle_num in sorted(all_puzzle_sigs.keys()):
        sigs = all_puzzle_sigs[puzzle_num]
        if sigs:
            r_bits = [s["r"].bit_length() for s in sigs]
            s_bits = [s["s"].bit_length() for s in sigs]
            print(f"    #{puzzle_num:3d}: {len(sigs)} sigs, "
                  f"r_bits=[{min(r_bits)}-{max(r_bits)}], "
                  f"s_bits=[{min(s_bits)}-{max(s_bits)}]")

    # Nonce bias: MSB analysis across all
    print(f"\n  [C] MSB DO NONCE (primeiro byte de r) - GLOBAL")
    msb_all = [sig["r"].to_bytes(32, 'big')[0] for sig in all_sigs]
    high = sum(1 for b in msb_all if b >= 0x80)
    low = sum(1 for b in msb_all if b < 0x80)
    print(f"  MSB >= 0x80: {high} ({high/len(msb_all)*100:.1f}%)")
    print(f"  MSB <  0x80: {low} ({low/len(msb_all)*100:.1f}%)")
    print(f"  (esperado ~50/50 para nonces aleatorios)")

    # Top/bottom 4 bits of all r values
    print(f"\n  [D] TOP 4 BITS DE r (global)")
    top_nibs = [(sig["r"] >> 252) & 0xF for sig in all_sigs]
    nib_counts = Counter(top_nibs)
    for i in range(16):
        c = nib_counts.get(i, 0)
        pct = c / len(all_sigs) * 100
        print(f"    0x{i:X}: {c:2d} ({pct:5.1f}%)")

    # Wallet fingerprinting
    print(f"\n  [E] FINGERPRINT DO SOFTWARE")
    all_low_s = all(sig["s"] <= N_ORDER // 2 for sig in all_sigs)
    print(f"  Todas assinaturas low-s (BIP-62): {'Sim' if all_low_s else 'Nao'}")
    all_sighash = set(sig["sighash_type"] for sig in all_sigs)
    print(f"  Sighash types usados: {all_sighash}")

    der_sizes = Counter(len(sig["sig_der"]) // 2 for sig in all_sigs)
    print(f"  Tamanhos DER: {dict(der_sizes)}")

    if all_low_s:
        print(f"  -> Compativel com Bitcoin Core >= 0.9.0 ou software moderno")
    else:
        print(f"  -> Pode ser software antigo ou custom")


def main():
    print("=" * 70)
    print("ANALISE DE ASSINATURAS ECDSA - BITCOIN PUZZLES")
    print("Extraindo assinaturas das transacoes de saida")
    print("=" * 70)

    all_puzzle_sigs = {}

    # Process unsolved targets first
    print(f"\n{'='*70}")
    print("PUZZLES NAO RESOLVIDOS (alvos)")
    print(f"{'='*70}")

    for puzzle_num in sorted(TARGETS.keys()):
        info = TARGETS[puzzle_num]
        txs = get_outgoing_txs(info["address"], puzzle_num)
        time.sleep(1)

        sigs = extract_signatures(txs, info["address"])
        all_puzzle_sigs[puzzle_num] = sigs

        if sigs:
            results = analyze_signatures(sigs, f"Puzzle #{puzzle_num} (NAO RESOLVIDO)")
            for sig in sigs:
                print(f"\n    Assinatura #{sigs.index(sig)+1}:")
                print(f"      txid: {sig['txid']}")
                print(f"      r:    {sig['r_hex']}")
                print(f"      s:    {sig['s_hex']}")
        else:
            print(f"  Puzzle #{puzzle_num}: nenhuma assinatura encontrada")

    # Process some solved ones for comparison
    print(f"\n\n{'='*70}")
    print("PUZZLES RESOLVIDOS (referencia)")
    print(f"{'='*70}")

    solved_to_check = [65, 70, 75, 80, 130]
    for puzzle_num in solved_to_check:
        if puzzle_num not in SOLVED_WITH_TX:
            continue
        info = SOLVED_WITH_TX[puzzle_num]
        txs = get_outgoing_txs(info["address"], puzzle_num)
        time.sleep(1)

        sigs = extract_signatures(txs, info["address"])
        all_puzzle_sigs[puzzle_num] = sigs

        if sigs:
            analyze_signatures(sigs, f"Puzzle #{puzzle_num} (RESOLVIDO)")

    # Cross-puzzle analysis
    cross_puzzle_analysis(all_puzzle_sigs)

    # Save raw data
    output = {}
    for pnum, sigs in all_puzzle_sigs.items():
        output[str(pnum)] = [{
            "txid": s["txid"],
            "r": s["r_hex"],
            "s": s["s_hex"],
            "sighash": s["sighash_type"],
            "pubkey": s["pubkey"],
        } for s in sigs]

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signatures_raw.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n\nDados brutos salvos em: {out_path}")


if __name__ == "__main__":
    main()
