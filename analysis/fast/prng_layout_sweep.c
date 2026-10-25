/*
 * prng_layout_sweep: PRNGs nao criptograficos da epoca usados DIRETAMENTE como material
 * de chave (sem hash, sem HD), em todos os layouts simples, com rejeicao no primeiro
 * puzzle resolvido que nao bate (#2 da 1 bit, #3 da 2, ...). Reproduzir todos ate #130
 * e conclusivo.
 *
 * Geradores (seed de 32 bits, salvo indicacao):
 *   glibc     srand(s)/srandom(s) + rand()/random(): TYPE_3 (r[i]=r[i-3]+r[i-31], >>1), 31 bits.
 *             Identico ao random() do BSD/macOS. Semeadura Park-Miller + 310 descartes.
 *   msvc      srand(s) + rand(): LCG 214013/2531011, saida (s>>16)&0x7fff, 15 bits.
 *   pm        rand() do BSD/macOS (Park-Miller 16807 mod 2^31-1), 31 bits.
 *   v8        Math.random do V8 2013-dez/2015 (Chrome 28-48, Node 0.12): MWC 18030/36969,
 *             x = (r0<<16) + (r1&0xFFFF); random = x/2^32. floor(random*256) e floor(random*16)
 *             dependem SO do estado s0 (32 bits) -> enumeracao exata. floor(random*2^32)
 *             depende de s1 tambem: os 16 bits altos de cada palavra vem de s0; checamos so eles.
 *   mtnp      MT19937 com init_genrand(seed): numpy.random.seed, Ruby Random.new(seed<2^32), std::mt19937.
 *             Unidades: byte = palavra & 0xFF (randint(0,256)); byte4 = bytes(): 4 por palavra LE; word = 32 bits.
 *   mtphp     mt_srand/mt_rand do PHP 5.x-7.0: init_genrand + twist com bug (loBit(u)); saida >> 1 (31 bits);
 *             mt_rand(0,255) = n>>23; mt_rand(0,15) = n>>27.
 *   lcg48     LCG de 48 bits 0x5DEECE66D (Java, SpiderMonkey/Firefox <= 40). Math.random =
 *             (next(26)<<27 | next(27)) / 2^53. floor(random*256) = top 8 de next(26);
 *             floor(random*2^32) = next(26)<<6 | next(27)>>21. RECUPERACAO DE ESTADO: o
 *             primeiro byte do primeiro puzzle fixa 8 bits do estado; enumeramos os 40
 *             restantes (byte) ou 22 (word32).
 *
 * Unidades por gerador: byte = bits baixos (libc) / altos (v8, lcg48); nibble idem; word =
 * saida inteira (31/15/32 bits). Recortes: s256 (32 bytes ou ceil(256/w) palavras por chave)
 * e fit (so o necessario para n-1 bits). Montagem BE e LE. Mascaras low e high.
 *
 * Compilar: clang -O3 -o prng_layout_sweep prng_layout_sweep.c -lpthread
 * Controle positivo: --synth GEN SEED UNIT CHUNK ORDER MASK imprime as chaves ate #125 (n hex) que
 * esse candidato produziria; a varredura deve reencontra-lo e rejeitar um conjunto adulterado.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include <stdatomic.h>

#define MAXP 131
typedef unsigned __int128 u128;

/* ---------------- chaves conhecidas ---------------- */
static int g_have[MAXP];
static u128 g_key[MAXP];       /* so puzzles <= 130: cabem em 128 bits? #130 tem 130 bits -> guardamos key - 2^(n-1) (n-1 <= 129 bits) */
static u128 g_info[MAXP];      /* key_n - 2^(n-1) */
static int g_solved_list[MAXP]; static int g_nsolved;

static int hexval(char c) { return c >= '0' && c <= '9' ? c - '0' : (c | 32) - 'a' + 10; }
static void load_keys(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) { perror(path); exit(2); }
    char line[512]; memset(g_have, 0, sizeof g_have); g_nsolved = 0;
    while (fgets(line, sizeof line, f)) {
        int n; char hex[300];
        if (sscanf(line, "%d %299s", &n, hex) != 2) continue;
        if (n < 1 || n > 128) continue;  /* u128: #130 (129 bits de info) fica para a confirmacao em Python */
        u128 v = 0; for (char *p = hex; *p; p++) v = (v << 4) | (u128)hexval(*p);
        g_have[n] = 1; g_info[n] = v - ((u128)1 << (n - 1));
    }
    fclose(f);
    for (int n = 1; n <= 128; n++) if (g_have[n]) g_solved_list[g_nsolved++] = n;
}

/* ---------------- geradores: produzem um fluxo de unidades ---------------- */
typedef enum { G_GLIBC, G_MSVC, G_PM, G_V8, G_LCG48, G_MTNP, G_MTPHP } gen_t;
static gen_t g_gen;

typedef struct {
    gen_t gen;
    /* glibc TYPE_3 */
    int32_t r[34]; int f, b;
    /* msvc / pm / v8 / lcg48 */
    uint32_t s; uint32_t s0, s1; uint64_t st48;
    /* MT19937 */
    uint32_t mt[624]; int mti;
    /* cache de saidas brutas */
    uint32_t out[4800]; int nout;
} stream_t;

static void mt_init_genrand(stream_t *s, uint32_t seed) {
    s->mt[0] = seed;
    for (int i = 1; i < 624; i++) s->mt[i] = 1812433253u * (s->mt[i-1] ^ (s->mt[i-1] >> 30)) + (uint32_t)i;
    s->mti = 624;
}
static void mt_reload(stream_t *s, int phpbug) {
    uint32_t *m = s->mt;
    for (int i = 0; i < 624; i++) {
        uint32_t u = m[i], v = m[(i + 1) % 624];
        uint32_t y = (u & 0x80000000u) | (v & 0x7fffffffu);
        uint32_t lo = phpbug ? (u & 1u) : (v & 1u);          /* PHP 5.x-7.0: loBit(u) em vez de loBit(v) */
        m[i] = m[(i + 397) % 624] ^ (y >> 1) ^ (lo ? 0x9908b0dfu : 0u);
    }
    s->mti = 0;
}
static uint32_t mt_next(stream_t *s, int phpbug) {
    if (s->mti >= 624) mt_reload(s, phpbug);
    uint32_t y = s->mt[s->mti++];
    y ^= y >> 11; y ^= (y << 7) & 0x9d2c5680u; y ^= (y << 15) & 0xefc60000u; y ^= y >> 18;
    return y;
}

static inline int32_t pm_next(int32_t x) { /* Park-Miller via hi/lo (Schrage), igual glibc/BSD */
    int32_t hi = x / 127773, lo = x % 127773;
    int32_t w = 16807 * lo - 2836 * hi; if (w < 0) w += 2147483647; return w;
}
static uint32_t glibc_raw(stream_t *s) {
    /* fptr=&r[f], rptr=&r[b]; *f += *r; result = (*f >> 1) & 0x7fffffff */
    uint32_t v = (uint32_t)s->r[s->f] + (uint32_t)s->r[s->b]; s->r[s->f] = (int32_t)v;
    uint32_t res = (v >> 1) & 0x7fffffff;
    s->f++; s->b++; if (s->f >= 31) s->f = 0; if (s->b >= 31) s->b = 0;
    return res;
}
static void stream_init(stream_t *s, gen_t g, uint64_t seed) {
    s->gen = g; s->nout = 0;
    if (g == G_GLIBC) {
        uint32_t sd = (uint32_t)seed; if (sd == 0) sd = 1;
        s->r[0] = (int32_t)sd;
        for (int i = 1; i < 31; i++) s->r[i] = pm_next(s->r[i - 1]);
        s->f = 3; s->b = 0;
        for (int i = 0; i < 310; i++) glibc_raw(s);
    } else if (g == G_MSVC) { s->s = (uint32_t)seed; }
    else if (g == G_PM) { s->s = (uint32_t)seed; if (s->s == 0) s->s = 123459876; /* BSD: srand(0) -> trata como ?; mantemos simples */ }
    else if (g == G_V8) { s->s0 = (uint32_t)seed; s->s1 = (uint32_t)(seed >> 32); }
    else if (g == G_MTNP || g == G_MTPHP) { mt_init_genrand(s, (uint32_t)seed); }
    else { s->st48 = seed & 0xFFFFFFFFFFFFULL; }
}
static uint32_t raw_next(stream_t *s) {
    switch (s->gen) {
    case G_GLIBC: return glibc_raw(s);
    case G_MSVC:  s->s = s->s * 214013u + 2531011u; return (s->s >> 16) & 0x7fff;
    case G_PM:    s->s = (uint32_t)pm_next((int32_t)s->s); return s->s;
    case G_V8: {  /* devolve r0 (32 bits); o chamador extrai os bits que dependem so de s0 */
        uint32_t r0 = 18030u * (s->s0 & 0xFFFF) + (s->s0 >> 16); s->s0 = r0;
        uint32_t r1 = 36969u * (s->s1 & 0xFFFF) + (s->s1 >> 16); s->s1 = r1;
        return ((r0 << 16) + (r1 & 0xFFFF));  /* x completo; top16 = r0 low16 */
    }
    case G_MTNP:  return mt_next(s, 0);
    case G_MTPHP: return mt_next(s, 1) >> 1;   /* mt_rand() = tempered >> 1, 31 bits */
    default: {    /* lcg48: devolve next(32) (os 32 bits altos do estado novo) */
        s->st48 = (s->st48 * 0x5DEECE66DULL + 0xBULL) & 0xFFFFFFFFFFFFULL;
        return (uint32_t)(s->st48 >> 16);
    }
    }
}
static inline uint32_t raw_at(stream_t *s, int i) {
    while (s->nout <= i) { if (s->nout >= 4800) return 0; s->out[s->nout++] = raw_next(s); }
    return s->out[i];
}

/* unidade k do layout */
typedef enum { U_BYTE, U_NIBBLE, U_WORD, U_BYTE4 } unit_t;
static int unit_bits(gen_t g, unit_t u) {
    if (u == U_BYTE || u == U_BYTE4) return 8; if (u == U_NIBBLE) return 4;
    return g == G_GLIBC || g == G_PM || g == G_MTPHP ? 31 : (g == G_MSVC ? 15 : 32);
}
static inline uint32_t unit_at(stream_t *s, unit_t u, int k) {
    gen_t g = s->gen;
    if (g == G_LCG48) {
        /* Math.random() consome 2 passos: a = next(26) (passo 2k), b = next(27) (passo 2k+1) */
        uint32_t a = raw_at(s, 2 * k) >> 6;            /* next(26) */
        if (u == U_BYTE) return a >> 18;                 /* top 8 de 26 */
        if (u == U_NIBBLE) return a >> 22;
        uint32_t b = raw_at(s, 2 * k + 1) >> 5;         /* next(27) */
        return (a << 6) | (b >> 21);                     /* floor(random*2^32) */
    }
    if (u == U_BYTE4) return (raw_at(s, k / 4) >> (8 * (k % 4))) & 0xFF;   /* bytes(): 4 por palavra, LE */
    uint32_t x = raw_at(s, k);
    if (g == G_V8) {
        if (u == U_BYTE) return x >> 24; if (u == U_NIBBLE) return x >> 28; return x;
    }
    if (g == G_MTPHP) {   /* mt_rand(0,255) = n>>23 ; mt_rand(0,15) = n>>27 (RAND_RANGE em double, exato) */
        if (u == U_BYTE) return x >> 23; if (u == U_NIBBLE) return x >> 27; return x;
    }
    /* libc: bits baixos */
    if (u == U_BYTE) return x & 0xFF; if (u == U_NIBBLE) return x & 0xF; return x;
}

static uint64_t g_lo, g_hi; static int g_threads = 8;
static _Atomic uint64_t g_next, g_done; static _Atomic int g_hits;
static FILE *g_out; static pthread_mutex_t g_mu = PTHREAD_MUTEX_INITIALIZER;
static const uint64_t CHUNK = 1 << 16;

/* ---------------- montagem e checagem ---------------- */
typedef struct { unit_t u; int chunk; int le; int high; } combo_t;   /* chunk: 0=s256 1=fit */
static combo_t g_combos[64]; static int g_ncombo;

static int units_for(int n, int bits, int chunk) {
    if (chunk == 0) return (256 + bits - 1) / bits;
    int need = n - 1; if (need < 1) need = 1; return (need + bits - 1) / bits;
}
/* devolve 1 se o candidato reproduz todos os puzzles resolvidos (2..128); v8 word: compara so top16.
 * So monta as unidades que entram na comparacao: mascara low usa as 'need' unidades menos
 * significativas; high usa as primeiras unidades ate completar n bits. */
static int check_combo(stream_t *s, const combo_t *c, int v8word_top16) {
    int bits = unit_bits(s->gen, c->u);
    int k = 0;
    for (int n = 1; n <= 128; n++) {
        int cnt = units_for(n, bits, c->chunk);
        if (g_have[n] && n >= 2) {
            u128 v = 0, mm = 0;
            if (!c->high) {
                int need = (n - 1 + bits - 1) / bits; if (need > cnt) need = cnt;
                for (int t = cnt - need; t < cnt; t++) {
                    int idx = c->le ? (cnt - 1 - t) : t;
                    v = (v << bits) | unit_at(s, c->u, k + idx);
                    mm = (mm << bits) | (u128)(0xFFFF0000u >> (32 - bits));
                }
            } else {
                int got = 0;
                for (int t = 0; t < cnt && got < n; t++) {
                    int idx = c->le ? (cnt - 1 - t) : t;
                    uint32_t uv = unit_at(s, c->u, k + idx);
                    int take = bits; if (got + take > n) take = n - got;
                    v = (v << take) | (uv >> (bits - take));
                    mm = (mm << take) | (u128)(0xFFFF0000u >> (32 - take));
                    got += take;
                }
            }
            u128 m = ((u128)1 << (n - 1)) - 1;
            if (v8word_top16) { if (((v ^ g_info[n]) & m & mm) != 0) return 0; }
            else if ((v & m) != g_info[n]) return 0;
        }
        k += cnt;
    }
    return 1;
}

/* ---------------- lcg48: recuperacao de estado ---------------- */
#define M48 0xFFFFFFFFFFFFULL
static const uint64_t LA = 0x5DEECE66DULL, LC = 0xBULL;
typedef struct { uint64_t A, C; } aff_t;                 /* x -> (A x + C) mod 2^48 */
static aff_t aff_pow(int m) { aff_t r = {1, 0}; for (int i = 0; i < m; i++) { r.A = (LA * r.A) & M48; r.C = (LA * r.C + LC) & M48; } return r; }
static uint64_t inv48(uint64_t a) { uint64_t x = a; for (int i = 0; i < 7; i++) x = (x * (2 - a * x)) & M48; return x & M48; }
static aff_t aff_inv_pow(int m) { uint64_t ai = inv48(LA); aff_t st = {ai, ((M48 + 1 - LC) * ai) & M48}; aff_t r = {1, 0};
    for (int i = 0; i < m; i++) { r.A = (st.A * r.A) & M48; r.C = (st.A * r.C + st.C) & M48; } return r; }
static inline uint64_t aff_ap(aff_t f, uint64_t x) { return (f.A * x + f.C) & M48; }

typedef struct { int idx; uint32_t val; } known_t;
/* lista as primeiras K unidades totalmente conhecidas do layout (indice no fluxo de unidades, valor) */
static int known_units(const combo_t *c, known_t *out, int K) {
    int bits = unit_bits(G_LCG48, c->u), k = 0, cntk = 0;
    for (int n = 1; n <= 128 && cntk < K; n++) {
        int cnt = units_for(n, bits, c->chunk);
        if (g_have[n] && n >= 2) {
            if (!c->high) {
                int need = (n - 1 + bits - 1) / bits; if (need > cnt) need = cnt;
                for (int p = 0; p < need && cntk < K; p++) {            /* p = posicao a partir da menos significativa */
                    if ((p + 1) * bits > n - 1) break;
                    int t = cnt - 1 - p; int idx = c->le ? (cnt - 1 - t) : t;
                    out[cntk++] = (known_t){k + idx, (uint32_t)((g_info[n] >> (p * bits)) & (((u128)1 << bits) - 1))};
                }
            } else {
                int got = 0, total = cnt * bits, L = total < n ? total : n;  /* V tem min(n, total) bits */
                for (int t = 0; t < cnt && got < n && cntk < K; t++) {
                    int take = bits; if (got + take > n) take = n - got;
                    int top = L - got, bottom = L - got - take;         /* bits [bottom, top) de V */
                    got += take;
                    if (t == 0 || take != bits || top > n - 1) continue;
                    int idx = c->le ? (cnt - 1 - t) : t;
                    out[cntk++] = (known_t){k + idx, (uint32_t)((g_info[n] >> bottom) & (((u128)1 << bits) - 1))};
                }
            }
        }
        k += cnt;
    }
    return cntk;
}

static known_t g_kn[8]; static int g_nkn; static aff_t g_aff[8]; static aff_t g_back; static combo_t g_rc; static int g_rbits;
static _Atomic uint64_t g_rnext, g_rdone;
static void *rworker(void *arg) {
    (void)arg; stream_t s;
    uint64_t lim = g_rc.u == U_BYTE ? ((uint64_t)1 << 40) : ((uint64_t)1 << 22);
    int S1 = 2 * g_kn[0].idx + 1;
    uint64_t top = g_rc.u == U_BYTE ? ((uint64_t)g_kn[0].val << 40) : ((uint64_t)(g_kn[0].val >> 6) << 22);
    for (;;) {
        uint64_t start = atomic_fetch_add(&g_rnext, CHUNK); if (start >= lim) break;
        uint64_t end = start + CHUNK; if (end > lim) end = lim;
        for (uint64_t low = start; low < end; low++) {
            uint64_t st = top | low; int ok = 1;
            if (g_rc.u == U_WORD) { uint64_t nx = (LA * st + LC) & M48; if ((nx >> 42) != (g_kn[0].val & 63)) continue; }
            for (int j = 1; j < g_nkn && ok; j++) {
                uint64_t sj = aff_ap(g_aff[j], st);
                if (g_rc.u == U_BYTE) ok = (sj >> 40) == g_kn[j].val;
                else { ok = (sj >> 22) == (g_kn[j].val >> 6); if (ok) { uint64_t nx = (LA * sj + LC) & M48; ok = (nx >> 42) == (g_kn[j].val & 63); } }
            }
            if (!ok) continue;
            uint64_t s0 = aff_ap(g_back, st);
            stream_init(&s, G_LCG48, s0);
            if (check_combo(&s, &g_rc, 0)) {
                pthread_mutex_lock(&g_mu); atomic_fetch_add(&g_hits, 1);
                fprintf(g_out, "HIT gen=4 seed=%llu unit=%d chunk=%s order=%s mask=%s (estado inicial recuperado)\n", (unsigned long long)s0,
                        g_rc.u, g_rc.chunk ? "fit" : "s256", g_rc.le ? "le" : "be", g_rc.high ? "high" : "low");
                fflush(g_out); pthread_mutex_unlock(&g_mu);
            }
        }
        atomic_fetch_add(&g_rdone, end - start);
    }
    (void)S1; return NULL;
}

static void recover_all(void) {
    for (int ci = 0; ci < g_ncombo; ci++) {
        g_rc = g_combos[ci];
        if (g_rc.u == U_NIBBLE) { fprintf(stderr, "  combo %d: nibble (2^44) pulado\n", ci); continue; }
        g_nkn = known_units(&g_rc, g_kn, 6);
        if (g_nkn < 2) { fprintf(stderr, "  combo %d: unidades conhecidas insuficientes (%d)\n", ci, g_nkn); continue; }
        int S1 = 2 * g_kn[0].idx + 1;
        for (int j = 1; j < g_nkn; j++) g_aff[j] = aff_pow(2 * (g_kn[j].idx - g_kn[0].idx));
        g_back = aff_inv_pow(S1);
        /* sanidade: ida e volta */
        { aff_t f = aff_pow(S1); uint64_t x = 0x123456789ABCULL; if (aff_ap(g_back, aff_ap(f, x)) != x) { fprintf(stderr, "erro afim\n"); exit(3); } }
        atomic_store(&g_rnext, 0); atomic_store(&g_rdone, 0);
        uint64_t lim = g_rc.u == U_BYTE ? ((uint64_t)1 << 40) : ((uint64_t)1 << 22);
        fprintf(stderr, "lcg48 recover combo %d unit=%d chunk=%s order=%s mask=%s: %d unidades conhecidas (1a no indice %d, passo %d), espaco 2^%d\n",
                ci, g_rc.u, g_rc.chunk ? "fit" : "s256", g_rc.le ? "le" : "be", g_rc.high ? "high" : "low", g_nkn, g_kn[0].idx, S1, g_rc.u == U_BYTE ? 40 : 22);
        pthread_t th[64]; for (int i = 0; i < g_threads; i++) pthread_create(&th[i], NULL, rworker, NULL);
        time_t t0 = time(NULL); int tick = 0;
        for (;;) { struct timespec ts = {1, 0}; nanosleep(&ts, NULL); tick++; uint64_t d = atomic_load(&g_rdone); double el = difftime(time(NULL), t0);
            if (tick % 60 == 0 || d >= lim) fprintf(stderr, "    %5.1f%%  %.0f est/s  hits=%d  eta=%.0f min\n", 100.0 * d / lim, el > 0 ? d / el : 0.0, atomic_load(&g_hits), d > 0 ? (lim - d) * el / d / 60.0 : 0.0);
            if (d >= lim) break; }
        for (int i = 0; i < g_threads; i++) pthread_join(th[i], NULL);
        fprintf(g_out, "DONE gen=4 recover unit=%d chunk=%s order=%s mask=%s states=%llu hits=%d elapsed_s=%.0f\n", g_rc.u, g_rc.chunk ? "fit" : "s256",
                g_rc.le ? "le" : "be", g_rc.high ? "high" : "low", (unsigned long long)lim, atomic_load(&g_hits), difftime(time(NULL), t0));
        fflush(g_out);
    }
}

/* ---------------- varredura ---------------- */

static void *worker(void *arg) {
    (void)arg; stream_t s;
    for (;;) {
        uint64_t start = atomic_fetch_add(&g_next, CHUNK);
        if (start >= g_hi) break;
        uint64_t end = start + CHUNK; if (end > g_hi) end = g_hi;
        for (uint64_t t = start; t < end; t++) {
            stream_init(&s, g_gen, t);
            for (int ci = 0; ci < g_ncombo; ci++) {
                int v8w = (g_gen == G_V8 && g_combos[ci].u == U_WORD);
                if (check_combo(&s, &g_combos[ci], v8w)) {
                    pthread_mutex_lock(&g_mu); atomic_fetch_add(&g_hits, 1);
                    fprintf(g_out, "HIT gen=%d seed=%llu unit=%d chunk=%s order=%s mask=%s%s\n", g_gen, (unsigned long long)t,
                            g_combos[ci].u, g_combos[ci].chunk ? "fit" : "s256", g_combos[ci].le ? "le" : "be",
                            g_combos[ci].high ? "high" : "low", v8w ? " (so top16; confirmar s1)" : "");
                    fflush(g_out); pthread_mutex_unlock(&g_mu);
                }
            }
        }
        atomic_fetch_add(&g_done, end - start);
    }
    return NULL;
}

static const char *UN[] = {"byte", "nibble", "word", "byte4"};
static void add_combos(const char *units, const char *chunks, const char *orders, const char *masks) {
    g_ncombo = 0;
    for (int u = 0; u < 4; u++) if (strstr(units, UN[u]))
        for (int ch = 0; ch < 2; ch++) if (strstr(chunks, ch ? "fit" : "s256"))
            for (int le = 0; le < 2; le++) if (strstr(orders, le ? "le" : "be"))
                for (int hi = 0; hi < 2; hi++) if (strstr(masks, hi ? "high" : "low")) {
                    g_combos[g_ncombo++] = (combo_t){(unit_t)u, ch, le, hi};
                }
}

static void synth(gen_t g, uint64_t seed, unit_t u, int chunk, int le, int high) {
    stream_t s; stream_init(&s, g, seed);
    int bits = unit_bits(g, u); int k = 0;
    static const int puzzles[] = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,75,80,85,90,95,100,105,110,115,120,125,0};
    for (int n = 1; n <= 128; n++) {
        int cnt = units_for(n, bits, chunk);
        int want = 0; for (int i = 0; puzzles[i]; i++) if (puzzles[i] == n) want = 1;
        if (want) {
            u128 v = 0; int total = cnt * bits;
            if (high) {
                int got = 0;
                for (int t = 0; t < cnt && got < n; t++) { int idx = le ? (cnt - 1 - t) : t; uint32_t uv = unit_at(&s, u, k + idx);
                    int take = bits; if (got + take > n) take = n - got; v = (v << take) | (uv >> (bits - take)); got += take; }
            } else {
                for (int t = 0; t < cnt; t++) { int idx = le ? (cnt - 1 - t) : t; v = (v << bits) | unit_at(&s, u, k + idx); }
                (void)total;
            }
            u128 key = (v & (((u128)1 << (n - 1)) - 1)) | ((u128)1 << (n - 1));
            char hex[40]; int p = 39; hex[p] = 0; u128 x = key;
            do { hex[--p] = "0123456789abcdef"[x & 15]; x >>= 4; } while (x);
            printf("%d %s\n", n, hex + p);
        }
        k += cnt;
    }
}

int main(int argc, char **argv) {
    const char *keys = NULL, *out = NULL, *units = "byte,nibble,word,byte4", *chunks = "s256,fit", *orders = "be,le", *masks = "low,high";
    const char *synth_args[7] = {0}; int do_synth = 0; int do_vec = 0; int do_recover = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--gen")) { const char *g = argv[++i];
            g_gen = !strcmp(g, "glibc") ? G_GLIBC : !strcmp(g, "msvc") ? G_MSVC : !strcmp(g, "pm") ? G_PM : !strcmp(g, "v8") ? G_V8 : !strcmp(g, "mtnp") ? G_MTNP : !strcmp(g, "mtphp") ? G_MTPHP : G_LCG48; }
        else if (!strcmp(argv[i], "--range")) sscanf(argv[++i], "%llu-%llu", (unsigned long long *)&g_lo, (unsigned long long *)&g_hi);
        else if (!strcmp(argv[i], "--keys")) keys = argv[++i];
        else if (!strcmp(argv[i], "--out")) out = argv[++i];
        else if (!strcmp(argv[i], "--threads")) g_threads = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--units")) units = argv[++i];
        else if (!strcmp(argv[i], "--chunks")) chunks = argv[++i];
        else if (!strcmp(argv[i], "--orders")) orders = argv[++i];
        else if (!strcmp(argv[i], "--masks")) masks = argv[++i];
        else if (!strcmp(argv[i], "--synth")) { do_synth = 1; for (int j = 0; j < 6; j++) synth_args[j] = argv[++i]; }
        else if (!strcmp(argv[i], "--vectors")) do_vec = 1;
        else if (!strcmp(argv[i], "--recover")) do_recover = 1;
        else { fprintf(stderr, "arg desconhecido %s\n", argv[i]); return 2; }
    }
    if (do_vec) {  /* vetores classicos para conferir os geradores */
        stream_t s;
        stream_init(&s, G_GLIBC, 1); printf("glibc srand(1): "); for (int i = 0; i < 5; i++) printf("%u ", raw_next(&s)); printf("(esperado 1804289383 846930886 1681692777 1714636915 1957747793)\n");
        stream_init(&s, G_MSVC, 1); printf("msvc srand(1): "); for (int i = 0; i < 5; i++) printf("%u ", raw_next(&s)); printf("(esperado 41 18467 6334 26500 19169)\n");
        stream_init(&s, G_PM, 1); printf("pm srand(1): "); for (int i = 0; i < 3; i++) printf("%u ", raw_next(&s)); printf("(esperado 16807 282475249 1622650073)\n");
        stream_init(&s, G_LCG48, (0x5DEECE66DULL ^ 42) & 0xFFFFFFFFFFFFULL); /* java new Random(42) */
        uint32_t a = raw_at(&s, 0) >> 6, b = raw_at(&s, 1) >> 5; double d = ((double)(((uint64_t)a << 27) | b)) / 9007199254740992.0;
        printf("lcg48 java Random(42).nextDouble(): %.16f (esperado 0.7275636800328681)\n", d);
        stream_init(&s, G_MTNP, 5489); printf("mt19937 init_genrand(5489): %u (esperado 3499211612)\n", raw_next(&s));
        stream_init(&s, G_MTPHP, 1); printf("php5 mt_srand(1): %u (esperado 1244335972; PHP>=7.1 corrigido 895547922)\n", raw_next(&s));
        stream_init(&s, G_MTPHP, 7); printf("php5 mt_srand(7) 6 palavras: "); for (int i = 0; i < 6; i++) printf("%u ", raw_next(&s)); printf("\n");
        stream_init(&s, G_V8, 0x1234567800000001ULL); printf("v8 s0=1,s1=0x12345678: x0=%u\n", raw_next(&s));
        return 0;
    }
    if (do_synth) {
        gen_t g = !strcmp(synth_args[0], "glibc") ? G_GLIBC : !strcmp(synth_args[0], "msvc") ? G_MSVC : !strcmp(synth_args[0], "pm") ? G_PM : !strcmp(synth_args[0], "v8") ? G_V8 : !strcmp(synth_args[0], "mtnp") ? G_MTNP : !strcmp(synth_args[0], "mtphp") ? G_MTPHP : G_LCG48;
        unit_t u = !strcmp(synth_args[2], "byte") ? U_BYTE : !strcmp(synth_args[2], "nibble") ? U_NIBBLE : !strcmp(synth_args[2], "byte4") ? U_BYTE4 : U_WORD;
        synth(g, strtoull(synth_args[1], NULL, 0), u, !strcmp(synth_args[3], "fit"), !strcmp(synth_args[4], "le"), !strcmp(synth_args[5], "high"));
        return 0;
    }
    if (!keys) { fprintf(stderr, "--keys <arquivo n hex> obrigatorio\n"); return 2; }
    load_keys(keys);
    add_combos(units, chunks, orders, masks);
    g_out = out ? fopen(out, "a") : stdout;
    if (do_recover) { if (g_gen != G_LCG48) { fprintf(stderr, "--recover so para lcg48\n"); return 2; } recover_all(); return 0; }
    fprintf(stderr, "prng_layout_sweep gen=%d range=%llu-%llu combos=%d threads=%d solved<=130=%d\n", g_gen,
            (unsigned long long)g_lo, (unsigned long long)g_hi, g_ncombo, g_threads, g_nsolved);
    atomic_store(&g_next, g_lo); atomic_store(&g_done, 0);
    pthread_t th[64]; for (int i = 0; i < g_threads; i++) pthread_create(&th[i], NULL, worker, NULL);
    time_t t0 = time(NULL); uint64_t total = g_hi - g_lo; int tick = 0;
    for (;;) { struct timespec ts = {1, 0}; nanosleep(&ts, NULL); tick++;
        uint64_t d = atomic_load(&g_done); double el = difftime(time(NULL), t0);
        if (tick % 30 == 0 || d >= total) fprintf(stderr, "  %5.1f%%  %llu/%llu  %.0f cand/s  hits=%d  eta=%.0f min\n", 100.0 * d / total,
            (unsigned long long)d, (unsigned long long)total, el > 0 ? d / el : 0.0, atomic_load(&g_hits), d > 0 ? (total - d) * el / d / 60.0 : 0.0);
        if (d >= total) break; }
    for (int i = 0; i < g_threads; i++) pthread_join(th[i], NULL);
    fprintf(g_out, "DONE gen=%d range=%llu-%llu candidates=%llu combos=%d hits=%d elapsed_s=%.0f\n", g_gen, (unsigned long long)g_lo,
            (unsigned long long)g_hi, (unsigned long long)total, g_ncombo, atomic_load(&g_hits), difftime(time(NULL), t0));
    return 0;
}
