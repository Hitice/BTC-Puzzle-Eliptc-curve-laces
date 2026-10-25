/*
 * bx2_mi_sweep: varredura rapida de seeds `bx seed` (libbitcoin-explorer 2.0.0)
 * para BIP32 com ultimo nivel NAO endurecido (ex.: m/i, caminho padrao de
 * `bx hd-private`). Testa so a ANCORA (#130, 129 bits): qualquer acerto e
 * conclusivo (falso positivo 2^-129) e e confirmado depois em Python.
 *
 * Por candidato t:
 *   seed  = encoder(t)                      (16 ou 32 bytes, byte = engine() % 255)
 *   I     = HMAC-SHA512("Bitcoin seed", seed);  k = I[0:32], cc = I[32:64]
 *   [niveis fixos do caminho, endurecidos ou nao]
 *   P     = k*G (comprimido)                 <- o custo dominante
 *   para cada offset o: child = k + HMAC-SHA512(cc, P || be32(129+o))[0:32] mod n
 *   compara child com a chave #130 nas mascaras low / high / low_le.
 *
 * Compilar (macOS, Homebrew):
 *   clang -O3 -o bx2_mi_sweep bx2_mi_sweep.c -I/opt/homebrew/include -L/opt/homebrew/lib -lsecp256k1 -lpthread
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include <stdatomic.h>
#include <CommonCrypto/CommonHMAC.h>
#include <secp256k1.h>

#define MINSTD_M 2147483647ULL

typedef struct { uint32_t mt[624]; int idx; } mt19937_t;
static void mt_init(mt19937_t *s, uint32_t seed) {
    s->mt[0] = seed;
    for (int i = 1; i < 624; i++)
        s->mt[i] = 1812433253U * (s->mt[i-1] ^ (s->mt[i-1] >> 30)) + (uint32_t)i;
    s->idx = 624;
}
static uint32_t mt_next(mt19937_t *s) {
    if (s->idx >= 624) {
        for (int i = 0; i < 624; i++) {
            uint32_t y = (s->mt[i] & 0x80000000U) | (s->mt[(i+1) % 624] & 0x7fffffffU);
            s->mt[i] = s->mt[(i+397) % 624] ^ (y >> 1) ^ ((y & 1) ? 0x9908b0dfU : 0);
        }
        s->idx = 0;
    }
    uint32_t y = s->mt[s->idx++];
    y ^= y >> 11; y ^= (y << 7) & 0x9d2c5680U; y ^= (y << 15) & 0xefc60000U; y ^= y >> 18;
    return y;
}

typedef enum { ENC_MINSTD0, ENC_MINSTD, ENC_MT19937 } enc_kind;
static enc_kind g_enc; static int g_nbytes = 16; static const char *g_encname = "bx2-minstd0";

static void encode_seed(uint64_t t, uint8_t *out) {
    if (g_enc == ENC_MT19937) {
        mt19937_t s; mt_init(&s, (uint32_t)t);
        for (int j = 0; j < g_nbytes; j++) out[j] = (uint8_t)(mt_next(&s) % 255);
        return;
    }
    uint64_t a = (g_enc == ENC_MINSTD0) ? 16807ULL : 48271ULL;
    uint64_t x = t % MINSTD_M; if (x == 0) x = 1;
    for (int j = 0; j < g_nbytes; j++) { x = x * a % MINSTD_M; out[j] = (uint8_t)(x % 255); }
}

static void hmac512(const uint8_t *key, size_t klen, const uint8_t *msg, size_t mlen, uint8_t out[64]) {
    CCHmac(kCCHmacAlgSHA512, key, klen, msg, mlen, out);
}

/* caminho: niveis fixos antes do indice variavel; leaf sempre nao endurecido */
static uint32_t g_fixed[8]; static int g_nfixed = 0; static int g_leaf_hard = 0;
static int g_offsets[32]; static int g_noff = 0;
static uint8_t g_target[32];   /* chave #130 (ou ancora) big-endian */
static int g_anchor_n = 130;
static uint64_t g_lo, g_hi; static int g_threads = 8;
static _Atomic uint64_t g_next; static _Atomic uint64_t g_done; static _Atomic int g_hits;
static const uint64_t CHUNK = 20000;
static FILE *g_out;
static pthread_mutex_t g_mu = PTHREAD_MUTEX_INITIALIZER;

static int match_mask(const uint8_t child[32], int mask) {
    /* devolve 1 se mask(n, child) == target. n = g_anchor_n. Trabalha em bits. */
    uint8_t v[32];
    if (mask == 0) memcpy(v, child, 32);
    else if (mask == 2) for (int i = 0; i < 32; i++) v[i] = child[31 - i];
    else { /* high: top n bits */
        int sh = 256 - g_anchor_n; /* desloca para a direita sh bits */
        int by = sh / 8, bi = sh % 8;
        memset(v, 0, 32);
        for (int i = 31; i >= 0; i--) {
            int src = i - by; if (src < 0) break;
            uint32_t w = child[src];
            if (src - 1 >= 0) w |= (uint32_t)child[src-1] << 8;
            v[i] = (uint8_t)(w >> bi);
        }
    }
    /* compara os n-1 bits baixos */
    int nb = g_anchor_n - 1; int full = nb / 8, rem = nb % 8;
    for (int i = 0; i < full; i++) if (v[31 - i] != g_target[31 - i]) return 0;
    if (rem) { uint8_t m = (uint8_t)((1u << rem) - 1); if ((v[31 - full] & m) != (g_target[31 - full] & m)) return 0; }
    return 1;
}

static void *worker(void *arg) {
    (void)arg;
    secp256k1_context *ctx = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
    uint8_t seed[32], I[64], k[32], cc[32], pub[33], data[37], I2[64], child[32];
    secp256k1_pubkey P; size_t plen;
    for (;;) {
        uint64_t start = atomic_fetch_add(&g_next, CHUNK);
        if (start >= g_hi) break;
        uint64_t end = start + CHUNK; if (end > g_hi) end = g_hi;
        for (uint64_t t = start; t < end; t++) {
            encode_seed(t, seed);
            hmac512((const uint8_t *)"Bitcoin seed", 12, seed, g_nbytes, I);
            memcpy(k, I, 32); memcpy(cc, I + 32, 32);
            if (!secp256k1_ec_seckey_verify(ctx, k)) continue;
            int ok = 1;
            for (int L = 0; L < g_nfixed && ok; L++) {
                uint32_t idx = g_fixed[L];
                if (idx & 0x80000000U) { data[0] = 0; memcpy(data + 1, k, 32); }
                else {
                    if (!secp256k1_ec_pubkey_create(ctx, &P, k)) { ok = 0; break; }
                    plen = 33; secp256k1_ec_pubkey_serialize(ctx, data, &plen, &P, SECP256K1_EC_COMPRESSED);
                }
                data[33] = idx >> 24; data[34] = idx >> 16; data[35] = idx >> 8; data[36] = idx;
                hmac512(cc, 32, data, 37, I2);
                if (!secp256k1_ec_seckey_tweak_add(ctx, k, I2)) { ok = 0; break; }
                memcpy(cc, I2 + 32, 32);
            }
            if (!ok) continue;
            if (g_leaf_hard) { data[0] = 0; memcpy(data + 1, k, 32); }
            else {
                if (!secp256k1_ec_pubkey_create(ctx, &P, k)) continue;
                plen = 33; secp256k1_ec_pubkey_serialize(ctx, pub, &plen, &P, SECP256K1_EC_COMPRESSED);
                memcpy(data, pub, 33);
            }
            for (int oi = 0; oi < g_noff; oi++) {
                int64_t idx64 = (int64_t)(g_anchor_n - 1) + g_offsets[oi];
                if (idx64 < 0 || idx64 >= 0x80000000LL) continue;
                uint32_t idx = (uint32_t)idx64 | (g_leaf_hard ? 0x80000000u : 0u);
                data[33] = idx >> 24; data[34] = idx >> 16; data[35] = idx >> 8; data[36] = idx;
                hmac512(cc, 32, data, 37, I2);
                memcpy(child, k, 32);
                if (!secp256k1_ec_seckey_tweak_add(ctx, child, I2)) continue;
                for (int m = 0; m < 3; m++) {
                    if (match_mask(child, m)) {
                        pthread_mutex_lock(&g_mu);
                        atomic_fetch_add(&g_hits, 1);
                        fprintf(g_out, "HIT t=%llu offset=%d mask=%s\n", (unsigned long long)t, g_offsets[oi],
                                m == 0 ? "low" : (m == 1 ? "high" : "low_le"));
                        fflush(g_out);
                        pthread_mutex_unlock(&g_mu);
                    }
                }
            }
        }
        atomic_fetch_add(&g_done, end - start);
    }
    secp256k1_context_destroy(ctx);
    return NULL;
}

static int hex2bin(const char *h, uint8_t *out, int n) {
    size_t L = strlen(h); if (L > (size_t)n * 2) return -1;
    memset(out, 0, n);
    /* alinha a direita */
    char buf[65]; memset(buf, '0', 64); buf[64] = 0; memcpy(buf + 64 - L, h, L);
    for (int i = 0; i < 32; i++) { unsigned v; if (sscanf(buf + 2*i, "%2x", &v) != 1) return -1; out[i] = (uint8_t)v; }
    return 0;
}

static void dump_one(uint64_t t) {
    /* modo de conferencia: imprime seed, k, cc e child(129) para m/i */
    uint8_t seed[32], I[64], k[32], cc[32], pub[33], data[37], I2[64], child[32];
    secp256k1_context *ctx = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
    encode_seed(t, seed);
    printf("t=%llu seed=", (unsigned long long)t); for (int i = 0; i < g_nbytes; i++) printf("%02x", seed[i]);
    hmac512((const uint8_t *)"Bitcoin seed", 12, seed, g_nbytes, I);
    memcpy(k, I, 32); memcpy(cc, I + 32, 32);
    for (int L = 0; L < g_nfixed; L++) {
        uint32_t idx = g_fixed[L]; secp256k1_pubkey P; size_t plen = 33;
        if (idx & 0x80000000U) { data[0] = 0; memcpy(data + 1, k, 32); }
        else { secp256k1_ec_pubkey_create(ctx, &P, k); secp256k1_ec_pubkey_serialize(ctx, data, &plen, &P, SECP256K1_EC_COMPRESSED); }
        data[33] = idx >> 24; data[34] = idx >> 16; data[35] = idx >> 8; data[36] = idx;
        hmac512(cc, 32, data, 37, I2); secp256k1_ec_seckey_tweak_add(ctx, k, I2); memcpy(cc, I2 + 32, 32);
    }
    secp256k1_pubkey P; size_t plen = 33;
    if (g_leaf_hard) { data[0] = 0; memcpy(data + 1, k, 32); }
    else { secp256k1_ec_pubkey_create(ctx, &P, k); secp256k1_ec_pubkey_serialize(ctx, pub, &plen, &P, SECP256K1_EC_COMPRESSED); memcpy(data, pub, 33); }
    uint32_t idx = (g_anchor_n - 1) | (g_leaf_hard ? 0x80000000u : 0u);
    data[33] = idx >> 24; data[34] = idx >> 16; data[35] = idx >> 8; data[36] = idx;
    hmac512(cc, 32, data, 37, I2); memcpy(child, k, 32); secp256k1_ec_seckey_tweak_add(ctx, child, I2);
    printf(" k="); for (int i = 0; i < 32; i++) printf("%02x", k[i]);
    printf(" child%u=", idx & 0x7fffffffu); for (int i = 0; i < 32; i++) printf("%02x", child[i]);
    printf("\n");
    secp256k1_context_destroy(ctx);
}

int main(int argc, char **argv) {
    const char *target_hex = NULL, *path = "m/i", *dump = NULL, *outpath = NULL;
    g_offsets[g_noff++] = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--encoder")) {
            const char *e = argv[++i]; g_encname = e;
            if (!strcmp(e, "bx2-minstd0")) { g_enc = ENC_MINSTD0; g_nbytes = 16; }
            else if (!strcmp(e, "bx2-minstd")) { g_enc = ENC_MINSTD; g_nbytes = 16; }
            else if (!strcmp(e, "bx2-mt19937")) { g_enc = ENC_MT19937; g_nbytes = 16; }
            else if (!strcmp(e, "bx2-minstd0-256")) { g_enc = ENC_MINSTD0; g_nbytes = 32; }
            else if (!strcmp(e, "bx2-minstd-256")) { g_enc = ENC_MINSTD; g_nbytes = 32; }
            else if (!strcmp(e, "bx2-mt19937-256")) { g_enc = ENC_MT19937; g_nbytes = 32; }
            else { fprintf(stderr, "encoder desconhecido %s\n", e); return 2; }
        } else if (!strcmp(argv[i], "--range")) { sscanf(argv[++i], "%llu-%llu", (unsigned long long *)&g_lo, (unsigned long long *)&g_hi); }
        else if (!strcmp(argv[i], "--threads")) g_threads = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--target")) target_hex = argv[++i];
        else if (!strcmp(argv[i], "--anchor-n")) g_anchor_n = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--path")) path = argv[++i];
        else if (!strcmp(argv[i], "--offsets")) { g_noff = 0; char *s = strdup(argv[++i]); for (char *p = strtok(s, ","); p; p = strtok(NULL, ",")) g_offsets[g_noff++] = atoi(p); }
        else if (!strcmp(argv[i], "--dump")) dump = argv[++i];
        else if (!strcmp(argv[i], "--out")) outpath = argv[++i];
        else { fprintf(stderr, "arg desconhecido %s\n", argv[i]); return 2; }
    }
    /* caminho: m/<fixed>/.../i ; so o leaf 'i' (nao endurecido) e aceito */
    {
        char *s = strdup(path); char *p = strtok(s, "/"); int first = 1; g_nfixed = 0;
        for (; p; p = strtok(NULL, "/")) {
            if (first) { first = 0; if (strcmp(p, "m")) { fprintf(stderr, "caminho deve comecar com m\n"); return 2; } continue; }
            if (!strcmp(p, "i")) { if (strtok(NULL, "/")) { fprintf(stderr, "i deve ser o ultimo nivel\n"); return 2; } break; }
            if (!strcmp(p, "ih")) { g_leaf_hard = 1; if (strtok(NULL, "/")) { fprintf(stderr, "ih deve ser o ultimo nivel\n"); return 2; } break; }
            size_t L = strlen(p); int hard = (p[L-1] == 'h' || p[L-1] == '\''); 
            g_fixed[g_nfixed++] = (uint32_t)atol(p) + (hard ? 0x80000000U : 0);
        }
    }
    if (dump) { for (char *p = strtok((char *)dump, ","); p; p = strtok(NULL, ",")) dump_one(strtoull(p, NULL, 10)); return 0; }
    if (!target_hex || hex2bin(target_hex, g_target, 32)) { fprintf(stderr, "--target <hex da chave ancora> obrigatorio\n"); return 2; }
    g_out = outpath ? fopen(outpath, "a") : stdout; if (!g_out) { perror("out"); return 2; }
    fprintf(stderr, "bx2_mi_sweep encoder=%d nbytes=%d path=%s anchor=#%d range=%llu-%llu threads=%d offsets=%d\n",
            g_enc, g_nbytes, path, g_anchor_n, (unsigned long long)g_lo, (unsigned long long)g_hi, g_threads, g_noff);
    atomic_store(&g_next, g_lo); atomic_store(&g_done, 0);
    pthread_t th[64]; for (int i = 0; i < g_threads; i++) pthread_create(&th[i], NULL, worker, NULL);
    time_t t0 = time(NULL); uint64_t total = g_hi - g_lo;
    int tick = 0;
    for (;;) {
        struct timespec ts = {1, 0}; nanosleep(&ts, NULL); tick++;
        uint64_t d = atomic_load(&g_done); double el = difftime(time(NULL), t0);
        if (tick % 30 == 0 || d >= total) fprintf(stderr, "  %5.1f%%  %llu/%llu  %.0f cand/s  hits=%d  eta=%.0f min\n", 100.0 * d / total,
                (unsigned long long)d, (unsigned long long)total, el > 0 ? d / el : 0.0, atomic_load(&g_hits),
                d > 0 ? (total - d) * el / d / 60.0 : 0.0);
        if (d >= total) break;
    }
    for (int i = 0; i < g_threads; i++) pthread_join(th[i], NULL);
    double el = difftime(time(NULL), t0);
    fprintf(g_out, "DONE encoder=%s nbytes=%d path=%s anchor=%d range=%llu-%llu candidates=%llu hits=%d elapsed_s=%.0f\n",
            g_encname, g_nbytes, path, g_anchor_n, (unsigned long long)g_lo, (unsigned long long)g_hi, (unsigned long long)total, atomic_load(&g_hits), el);
    return 0;
}
