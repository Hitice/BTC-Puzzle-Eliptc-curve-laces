#!/usr/bin/env python3
"""Extrai indicadores forenses das 5 transacoes do criador do puzzle.

Objetivo: reduzir o conjunto de softwares que poderiam ter montado e assinado
essas transacoes, para restringir a hipotese sobre o gerador de 2015.

Este script SO extrai fatos objetivos. A interpretacao (qual carteira) exige
pesquisa externa sobre o comportamento de cada software na epoca e nao e feita
aqui. Saida: data/creator_txs.json

Uso: python3 analysis/creator_tx_forensics.py [--offline]
"""
import argparse, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "creator_txs.json")
API = "https://mempool.space/api/tx/%s"

N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
HALF_N = N // 2

TXS = [
    ("2015-01-15 financiamento (1 entrada / 256 saidas)",
     "08389f34c98c606322740c0be6a7125d9860bb8d5cb182c02f98461e5fa6cd15"),
    ("2017-07-11 gasto dos #161-#256",
     "5d45587cfd1d5b0fb826805541da7d94c61fe432259e68ee26f4a04544384164"),
    ("2019-05-16 financiamento dos 1000 sat",
     "7c432398c7631600af01695c9767eff109cbfae4f7ecccaff388043a474d4f1e"),
    ("2019-05-31 gasto que expos as pubkeys #65..#160",
     "17e4e323cfbc68d7f0071cad09364e8193eedf8fefbcbd8a21b4b65717a4b3d3"),
    ("2023-04-16 reforco x10",
     "12f34b58b04dfb0233ce889f674781c0e0c7ba95482cca469125af41a78d13b3"),
]


def parse_der(sig_hex):
    """Devolve (r, s, sighash, strict_der, minimal_ints)."""
    b = bytes.fromhex(sig_hex)
    if not 9 <= len(b) <= 73:
        raise ValueError('Invalid DER signature length')
    sighash = b[-1]
    body = b[:-1]
    ok = body[0] == 0x30 and body[1] == len(body) - 2
    i = 2
    ints = []
    minimal = True
    for _ in range(2):
        if i + 2 > len(body) or body[i] != 0x02:
            raise ValueError('Missing DER integer')
        ln = body[i + 1]
        if ln == 0 or i + 2 + ln > len(body):
            raise ValueError('Truncated or empty DER integer')
        raw = body[i + 2:i + 2 + ln]
        if ln == 0 or (raw[0] & 0x80):
            minimal = False
        if ln > 1 and raw[0] == 0x00 and not (raw[1] & 0x80):
            minimal = False
        ints.append(int.from_bytes(raw, "big"))
        i += 2 + ln
    if i != len(body):
        ok = False
    r, s = ints
    return r, s, sighash, ok, minimal


def script_pushes(script_hex):
    """Read push-only script bytes; do not trust explorer ASM formatting."""
    raw, result, i = bytes.fromhex(script_hex), [], 0
    while i < len(raw):
        opcode = raw[i]
        i += 1
        if opcode <= 75:
            size = opcode
        elif opcode in (76, 77, 78):
            width = 1 << (opcode-76)
            if i+width > len(raw):
                raise ValueError('Truncated PUSHDATA length')
            size = int.from_bytes(raw[i:i+width], 'little')
            i += width
        else:
            raise ValueError('Non-push opcode')
        if i+size > len(raw):
            raise ValueError('Truncated script push')
        result.append(raw[i:i+size])
        i += size
    return result


def signature_payload(vin):
    kind = vin['prevout'].get('scriptpubkey_type')
    if kind == 'p2pkh':
        values = script_pushes(vin.get('scriptsig', ''))
        origin = 'scriptsig'
    elif kind == 'v0_p2wpkh':
        if vin.get('scriptsig'):
            raise ValueError('Native P2WPKH has nonempty scriptSig')
        values = [bytes.fromhex(v) for v in vin.get('witness', [])]
        origin = 'witness'
    else:
        raise ValueError(f'Unsupported input type: {kind}')
    if len(values) != 2:
        raise ValueError('Expected signature and public key')
    sig, public = values
    if not ((len(public) == 33 and public[0] in (2, 3)) or
            (len(public) == 65 and public[0] == 4)):
        raise ValueError('Invalid public key encoding')
    return sig, public, origin


def analyze(tx):
    vin, vout = tx["vin"], tx["vout"]
    sigs = []
    for k, v in enumerate(vin):
        rec = {"index": k, "sequence": v.get("sequence"),
               "prev_address": v["prevout"].get("scriptpubkey_address"),
               "prev_value": v["prevout"]["value"],
               "prev_type": v["prevout"].get("scriptpubkey_type"),
               "scriptsig_len": len(bytes.fromhex(v.get("scriptsig", "") or ""))}
        try:
            sig, public, origin = signature_payload(v)
            r, s, sh, strict, minimal = parse_der(sig.hex())
            rec.update({"r": "%064x" % r, "s": "%064x" % s, "sighash": sh,
                        "low_s": s <= HALF_N, "strict_der": strict,
                        "minimal_ints": minimal, "sig_len": len(sig),
                        "pubkey_len": len(public), 'signature_source': origin,
                        "pubkey_compressed": len(public) == 33})
        except ValueError as exc:
            rec['signature_parse_error'] = str(exc)
        sigs.append(rec)
    signed = [s for s in sigs if "low_s" in s]
    values = [o["value"] for o in vout]
    addrs = [o.get("scriptpubkey_address") for o in vout]
    return {
        "version": tx["version"], "locktime": tx["locktime"],
        "size": tx["size"], "weight": tx["weight"], "fee": tx["fee"],
        "block_height": tx["status"].get("block_height"),
        "block_time": tx["status"].get("block_time"),
        "n_in": len(vin), "n_out": len(vout),
        "fee_rate_sat_vb": round(tx["fee"] / (tx["weight"] / 4.0), 4),
        "inputs": sigs,
        "outputs": [{"index": i, "address": a, "value": v,
                     "type": o.get("scriptpubkey_type")}
                    for i, (a, v, o) in enumerate(zip(addrs, values, vout))],
        "indicators": {
            "all_sequences": sorted({s["sequence"] for s in sigs}),
            "signed_inputs": len(signed),
            'unparsed_inputs': len(sigs)-len(signed),
            'witness_signatures': sum(s.get('signature_source') == 'witness' for s in signed),
            "low_s_count": sum(1 for s in signed if s["low_s"]),
            "high_s_count": sum(1 for s in signed if not s["low_s"]),
            "strict_der_all": all(s["strict_der"] for s in signed) if signed else None,
            "minimal_ints_all": all(s["minimal_ints"] for s in signed) if signed else None,
            "sighash_values": sorted({s["sighash"] for s in signed}),
            "pubkeys_compressed": sorted({s["pubkey_compressed"] for s in signed}),
            "inputs_sorted_by_value_asc": values and all(
                a["prev_value"] <= b["prev_value"]
                for a, b in zip(sigs, sigs[1:])),
            "outputs_sorted_by_value_asc": all(a <= b for a, b in zip(values, values[1:])),
            "outputs_sorted_by_value_desc": all(a >= b for a, b in zip(values, values[1:])),
            "out_value_min": min(values), "out_value_max": max(values),
            "distinct_out_values": len(set(values)),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="nao busca na rede; apenas reprocessa data/creator_txs.json")
    a = ap.parse_args()
    if a.offline:
        with open(OUT) as f:
            doc = json.load(f)
        raw = {t["txid"]: t["_raw"] for t in doc["transactions"] if "_raw" in t}
    else:
        raw = {}
        for label, txid in TXS:
            sys.stderr.write("buscando %s ...\n" % txid[:16])
            with urllib.request.urlopen(API % txid, timeout=60) as r:
                raw[txid] = json.load(r)
    out = []
    for label, txid in TXS:
        t = raw[txid]
        rec = {"label": label, "txid": txid}
        rec.update(analyze(t))
        rec["_raw"] = t
        out.append(rec)
    doc = {
        "purpose": "Indicadores forenses das transacoes do criador. Fatos apenas; "
                   "a atribuicao de software exige pesquisa externa.",
        "source": "mempool.space REST API",
        "transactions": out,
    }
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1)
    for r in out:
        i = r["indicators"]
        print("\n== %s" % r["label"])
        print("   txid %s" % r["txid"])
        print("   version=%d locktime=%d  in=%d out=%d  fee=%d sat (%.2f sat/vB)"
              % (r["version"], r["locktime"], r["n_in"], r["n_out"], r["fee"],
                 r["fee_rate_sat_vb"]))
        print("   sequences=%s  sighash=%s" % (i["all_sequences"], i["sighash_values"]))
        print("   assinaturas=%d  low-S=%d  high-S=%d  DER estrito=%s  ints minimos=%s"
              % (i["signed_inputs"], i["low_s_count"], i["high_s_count"],
                 i["strict_der_all"], i["minimal_ints_all"]))
        print("   pubkeys comprimidas=%s" % i["pubkeys_compressed"])
        print("   saidas ordenadas por valor: asc=%s desc=%s  valores distintos=%d/%d"
              % (i["outputs_sorted_by_value_asc"], i["outputs_sorted_by_value_desc"],
                 i["distinct_out_values"], r["n_out"]))
    print("\ngravado %s" % os.path.normpath(OUT))


if __name__ == "__main__":
    main()
