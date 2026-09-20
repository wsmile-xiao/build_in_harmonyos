/* Consumer regression test for polyseed 1.0.0 on OpenHarmony aarch64.
 *
 * Exercises the public API through the runtime dependency-injection
 * contract. The all-language round-trip section is the key regression
 * for the AArch64 unsigned-`char` platform issue adapted by this recipe.
 */
#ifdef NDEBUG
#undef NDEBUG
#endif

#include <polyseed.h>

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* --- injected dependencies (test-grade implementations) --- */

static unsigned long long g_rng_state = 0x0123456789abcdefULL;

static void my_randbytes(void* result, size_t n) {
    uint8_t* p = (uint8_t*)result;
    for (size_t i = 0; i < n; ++i) {
        g_rng_state = g_rng_state * 6364136223846793005ULL + 1442695040888963407ULL;
        p[i] = (uint8_t)(g_rng_state >> 33);
    }
}

static void my_pbkdf2(const uint8_t* pw, size_t pwlen, const uint8_t* salt,
    size_t saltlen, uint64_t iterations, uint8_t* key, size_t keylen) {
    (void)iterations;
    for (size_t i = 0; i < keylen; ++i) {
        unsigned v = (unsigned)(i * 31 + 7);
        size_t j;
        for (j = 0; j < pwlen; ++j) {
            v = v * 33u + pw[j];
        }
        for (j = 0; j < saltlen; ++j) {
            v = v * 31u + salt[j];
        }
        key[i] = (uint8_t)(v & 0xff);
    }
}

static void my_memzero(void* const ptr, const size_t len) {
    volatile uint8_t* p = (volatile uint8_t*)ptr;
    size_t i;
    for (i = 0; i < len; ++i) {
        p[i] = 0;
    }
}

static size_t my_identity(const char* str, polyseed_str norm) {
    size_t n = strlen(str);
    memcpy(norm, str, n + 1);
    return n;
}

/* NFKD stand-in for tests, same contract as upstream tests.c `u8_nfkd_spaces`:
   all whitespace (including the U+3000 ideographic space used to separate
   Japanese phrases) is normalized to a single ASCII space; other bytes are
   copied verbatim (wordlists are already stored in NFKD). */
static int is_space_byte(unsigned char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\v' || c == '\f';
}

static size_t my_nfkd_spaces(const char* str, polyseed_str norm) {
    size_t size = 0;
    const unsigned char* p = (const unsigned char*)str;
    while (*p != '\0' && size < POLYSEED_STR_SIZE - 1) {
        size_t adv = 1;
        int is_space = is_space_byte(*p);
        if (*p >= 0xC2 && *p <= 0xDF && (p[1] & 0xC0) == 0x80) adv = 2;
        else if (*p >= 0xE0 && *p <= 0xEF && (p[1] & 0xC0) == 0x80
                 && (p[2] & 0xC0) == 0x80) {
            /* U+0085, U+00A0, U+1680, U+2000-200A, U+2028, U+2029,
               U+202F, U+205F, U+3000 */
            adv = 3;
            is_space =
                (p[0] == 0xC2 && p[1] == 0x85) ||
                (p[0] == 0xC2 && p[1] == 0xA0) ||
                (p[0] == 0xE1 && p[1] == 0x9A && p[2] == 0x80) ||
                (p[0] == 0xE2 && p[1] == 0x80 && (p[2] >= 0x80 && p[2] <= 0x8A)) ||
                (p[0] == 0xE2 && p[1] == 0x80 && (p[2] == 0xA8 || p[2] == 0xA9)) ||
                (p[0] == 0xE2 && p[1] == 0x80 && p[2] == 0xAF) ||
                (p[0] == 0xE2 && p[1] == 0x81 && p[2] == 0x9F) ||
                (p[0] == 0xE3 && p[1] == 0x80 && p[2] == 0x80);
        }
        else if (*p >= 0xF0) adv = 4;
        if (is_space) {
            norm[size++] = ' ';
        } else {
            for (size_t k = 0; k < adv && size < POLYSEED_STR_SIZE - 1; ++k) {
                norm[size++] = (char)p[k];
            }
        }
        p += adv;
    }
    norm[size] = '\0';
    return size;
}

static const polyseed_lang* find_lang(const char* name_en) {
    int i;
    for (i = 0; i < polyseed_get_num_langs(); ++i) {
        const polyseed_lang* lang = polyseed_get_lang(i);
        if (0 == strcmp(polyseed_get_lang_name_en(lang), name_en)) {
            return lang;
        }
    }
    return NULL;
}

int main(void) {
    const polyseed_dependency deps = {
        .randbytes = &my_randbytes,
        .pbkdf2_sha256 = &my_pbkdf2,
        .memzero = &my_memzero,
        .u8_nfc = &my_identity,
        .u8_nfkd = &my_nfkd_spaces,
    };
    polyseed_inject(&deps);

    /* basic introspection */
    assert(polyseed_get_num_langs() == 10);
    const polyseed_lang* en = find_lang("English");
    const polyseed_lang* jp = find_lang("Japanese");
    assert(en != NULL);
    assert(jp != NULL);

    /* seed creation + birthday window */
    polyseed_data* seed = NULL;
    assert(polyseed_create(0, &seed) == POLYSEED_OK);
    assert(seed != NULL);
    uint64_t birthday = polyseed_get_birthday(seed);
    time_t now = time(NULL);
    assert(birthday <= (uint64_t)now);
    assert(birthday + 2630000 > (uint64_t)now);

    /* English encode/decode round-trip + key stability */
    polyseed_str phrase;
    size_t len = polyseed_encode(seed, en, POLYSEED_MONERO, phrase);
    assert(len > 0);
    assert(strlen(phrase) == len);
    const polyseed_lang* lang_out = NULL;
    polyseed_data* decoded = NULL;
    assert(polyseed_decode(phrase, POLYSEED_MONERO, &lang_out, &decoded) == POLYSEED_OK);
    assert(lang_out == en);
    uint8_t key1[32];
    uint8_t key2[32];
    polyseed_keygen(seed, POLYSEED_MONERO, sizeof key1, key1);
    polyseed_keygen(decoded, POLYSEED_MONERO, sizeof key2, key2);
    assert(0 == memcmp(key1, key2, sizeof key1));
    polyseed_free(decoded);

    /* coin domain separation */
    uint8_t key_aeon[32];
    polyseed_keygen(seed, POLYSEED_AEON, sizeof key_aeon, key_aeon);
    assert(0 != memcmp(key1, key_aeon, sizeof key1));
    polyseed_data* wrong_coin = NULL;
    assert(polyseed_decode(phrase, POLYSEED_AEON, NULL, &wrong_coin) == POLYSEED_ERR_CHECKSUM);

    /* wrong word count */
    polyseed_data* short_phrase = NULL;
    assert(polyseed_decode("raven tail", POLYSEED_MONERO, NULL, &short_phrase) == POLYSEED_ERR_NUM_WORDS);

    /* store/load serialization */
    polyseed_storage store;
    polyseed_store(seed, store);
    polyseed_data* loaded = NULL;
    assert(polyseed_load(store, &loaded) == POLYSEED_OK);
    uint8_t key3[32];
    polyseed_keygen(loaded, POLYSEED_MONERO, sizeof key3, key3);
    assert(0 == memcmp(key1, key3, sizeof key1));
    polyseed_free(loaded);

    /* encryption toggle */
    assert(polyseed_is_encrypted(seed) == 0);
    polyseed_crypt(seed, "test password");
    assert(polyseed_is_encrypted(seed) == 1);
    polyseed_crypt(seed, "test password");
    assert(polyseed_is_encrypted(seed) == 0);
    uint8_t key4[32];
    polyseed_keygen(seed, POLYSEED_MONERO, sizeof key4, key4);
    assert(0 == memcmp(key1, key4, sizeof key1));

    /* all-language round-trip: the AArch64 signed-char regression path */
    int num_langs = polyseed_get_num_langs();
    for (int i = 0; i < num_langs; ++i) {
        const polyseed_lang* lang = polyseed_get_lang(i);
        polyseed_str p;
        assert(polyseed_encode(seed, lang, POLYSEED_MONERO, p) > 0);
        const polyseed_lang* lo = NULL;
        polyseed_data* s = NULL;
        assert(polyseed_decode(p, POLYSEED_MONERO, &lo, &s) == POLYSEED_OK);
        assert(lo == lang);
        polyseed_free(s);
    }

    polyseed_free(seed);
    polyseed_free(NULL);

    printf("polyseed consumer test: all assertions passed\n");
    return 0;
}
