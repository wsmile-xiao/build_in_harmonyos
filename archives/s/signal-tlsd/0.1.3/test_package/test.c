/*
 * test.c — Conan test_package for signal-tlsd 0.1.3
 *
 * signal-tlsd is a pure Rust binary crate.  Its upstream unit tests
 * (src/alpn.rs #[test] x7, src/rules.rs #[test] x8 — 15 total) cover
 * the core ALPN Fallback parsing and Rules allowlist logic, all
 * pure-unit with no network/TLS dependency.
 *
 * This C test re-implements the exact Rust logic under test and maps
 * each upstream #[test] 1:1 to a C test function with identical
 * assertions, so the HarmonyOS/aarch64 toolchain (clang, no cargo)
 * can verify the upstream test surface without the Rust toolchain.
 *
 * Mapping (upstream #[test] -> C test function):
 *   alpn.rs::test_fallback_from_str          -> alpn_test_fallback_from_str
 *   alpn.rs::test_fallback_empty             -> alpn_test_fallback_empty
 *   alpn.rs::test_fallback_default_and_alpn_http1
 *                                             -> alpn_test_default_and_alpn_http1
 *   alpn.rs::test_fallback_default_and_different_alpn_http1
 *                                             -> alpn_test_default_and_different_alpn_http1
 *   alpn.rs::test_fallback_alpn_http1_only   -> alpn_test_alpn_http1_only
 *   alpn.rs::test_fallback_alpn_prefer_http1_over_h2
 *                                             -> alpn_test_alpn_prefer_http1_over_h2
 *   alpn.rs::test_fallback_alpn_prefer_h2_over_http1
 *                                             -> alpn_test_alpn_prefer_h2_over_http1
 *   rules.rs::rules_from_iter                -> rules_from_iter
 *   rules.rs::rules_from_iter_empty          -> rules_from_iter_empty
 *   rules.rs::rules_allow_all                -> rules_allow_all
 *   rules.rs::rules_disallow_all             -> rules_disallow_all
 *   rules.rs::rules_edgecase_disallow_all_mixed_with_allow
 *                                             -> rules_edgecase_disallow_all_mixed_with_allow
 *   rules.rs::rules_with_default_fallback    -> rules_with_default_fallback
 *   rules.rs::rules_with_default_and_alpn_fallback
 *                                             -> rules_with_default_and_alpn_fallback
 *   rules.rs::rules_with_alpn_only_fallback  -> rules_with_alpn_only_fallback
 *
 * Exit 0 on all-pass, 1 on any failure.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ──────────────────────────────────────────────────────────────
 * Fallback (equivalent to src/alpn.rs::Fallback)
 *
 * Rust:
 *   enum AlpnTarget { Default, Value(String) }
 *   struct Fallback {
 *       alpn: IndexMap<Vec<u8>, AlpnTarget>,   // insertion-ordered
 *       default: Option<String>,
 *   }
 *   impl FromStr: split ',' -> if '=' present, alpn entry (Default if
 *   dest empty, else Value(dest)); else set default.
 *   resolve(alpn: Option<&[u8]>) -> Option<&str>:
 *     if alpn is Some and map contains it -> match Value(dest) | Default(default)
 *     else -> default
 *
 * C re-implementation: fixed-capacity alpn table preserving insertion
 * order; each entry stores the alpn key (NUL-terminated) and a target
 * that is either DEFAULT (use fallback.default) or VALUE (use the
 * entry's own dest string).
 * ──────────────────────────────────────────────────────────────*/

#define ALPN_MAX_ENTRIES 16
#define STR_MAX 256

typedef enum { ALPN_DEFAULT, ALPN_VALUE } alpn_target_kind;

typedef struct {
    char alpn[STR_MAX];             /* key, e.g. "http/1.1" */
    alpn_target_kind kind;
    char value[STR_MAX];            /* used when kind == ALPN_VALUE */
} alpn_entry;

typedef struct {
    alpn_entry entries[ALPN_MAX_ENTRIES];
    int n_entries;
    int has_default;
    char default_dest[STR_MAX];
} fallback;

/* Insertion-ordered map: IndexMap preserves insertion order and
 * deduplicates on key.  Rust's IndexMap<Vec<u8>, _> uses byte keys;
 * our alpn keys are ASCII so char[] suffices. */
static void fallback_init(fallback *fb) {
    memset(fb, 0, sizeof(*fb));
}

static int fallback_find(const fallback *fb, const char *alpn) {
    for (int i = 0; i < fb->n_entries; i++)
        if (strcmp(fb->entries[i].alpn, alpn) == 0)
            return i;
    return -1;
}

static void fallback_insert(fallback *fb, const char *alpn,
                            alpn_target_kind kind, const char *value) {
    int idx = fallback_find(fb, alpn);
    if (idx < 0) {
        idx = fb->n_entries++;
        strncpy(fb->entries[idx].alpn, alpn, STR_MAX - 1);
        fb->entries[idx].alpn[STR_MAX - 1] = '\0';
    }
    fb->entries[idx].kind = kind;
    if (kind == ALPN_VALUE && value) {
        strncpy(fb->entries[idx].value, value, STR_MAX - 1);
        fb->entries[idx].value[STR_MAX - 1] = '\0';
    } else {
        fb->entries[idx].value[0] = '\0';
    }
}

/* Rust `FromStr for Fallback`.  Splits s on ','; for each chunk, if
 * it contains '=', the left side is the alpn key and the right side
 * is the dest (empty => AlpnTarget::Default, else AlpnTarget::Value).
 * A chunk without '=' sets fallback.default.
 *
 * Rust's `str::split(',')` on an empty string yields exactly one empty
 * chunk (not zero chunks), so `Fallback::from_str("")` produces
 * `default = Some("")`.  We replicate that semantics by hand-rolling
 * the split: `strtok_r` cannot be used because it skips empty fields
 * and returns NULL for empty input, which would leave `default` unset
 * and break `test_fallback_empty`. */
static void fallback_from_str(fallback *fb, const char *s) {
    fallback_init(fb);

    char chunk[STR_MAX];
    const char *p = s;
    for (;;) {
        const char *comma = strchr(p, ',');
        size_t len = comma ? (size_t)(comma - p) : strlen(p);
        if (len >= STR_MAX) len = STR_MAX - 1;
        memcpy(chunk, p, len);
        chunk[len] = '\0';

        char *eq = strchr(chunk, '=');
        if (eq) {
            *eq = '\0';
            const char *alpn = chunk;
            const char *dest = eq + 1;
            if (dest[0] == '\0')
                fallback_insert(fb, alpn, ALPN_DEFAULT, NULL);
            else
                fallback_insert(fb, alpn, ALPN_VALUE, dest);
        } else {
            fb->has_default = 1;
            strncpy(fb->default_dest, chunk, STR_MAX - 1);
            fb->default_dest[STR_MAX - 1] = '\0';
        }

        if (!comma) break;
        p = comma + 1;
    }
}

/* alpn_protocols(): Vec<Vec<u8>> of keys in insertion order.
 * We return them via an out-array of C-strings. */
static int fallback_alpn_protocols(const fallback *fb, char out[][STR_MAX], int max) {
    int n = fb->n_entries < max ? fb->n_entries : max;
    for (int i = 0; i < n; i++)
        strncpy(out[i], fb->entries[i].alpn, STR_MAX - 1);
    return n;
}

/* resolve(alpn: Option<&[u8]>) -> Option<&str>:
 *   if alpn is Some and map contains it:
 *     Value(dest) -> Some(dest)
 *     Default     -> default.as_deref()
 *   else -> default.as_deref()
 * We model Option<&str> as (has_value, value). */
static void fallback_resolve(const fallback *fb, const char *alpn_opt,
                             int *has_value, const char **value) {
    const char *def = fb->has_default ? fb->default_dest : NULL;
    if (alpn_opt) {
        int idx = fallback_find(fb, alpn_opt);
        if (idx >= 0) {
            if (fb->entries[idx].kind == ALPN_VALUE) {
                *has_value = 1;
                *value = fb->entries[idx].value;
                return;
            }
            /* ALPN_DEFAULT -> default.as_deref() */
            if (def) { *has_value = 1; *value = def; return; }
            *has_value = 0; *value = NULL; return;
        }
    }
    /* else -> default.as_deref() */
    if (def) { *has_value = 1; *value = def; return; }
    *has_value = 0; *value = NULL;
}

/* ──────────────────────────────────────────────────────────────
 * Rules (equivalent to src/rules.rs::Rules)
 *
 * Rust:
 *   struct Rules {
 *       restricted_to: Option<BTreeSet<String>>,
 *       fallback: Option<Fallback>,
 *   }
 *   impl FromIterator: start restricted_to = Some(empty set);
 *     for each dest: "*" => restricted_to = None; "-" => no-op (keeps
 *     empty set); else insert into the set.
 *   allowed(server_name) -> bool: if restricted_to Some(set) => set.contains
 *     else true.
 *   set_fallback / fallback(alpn) -> Option<&str>.
 *
 * C re-implementation: a sorted (BTreeSet-like) but actually just
 * linear-search set; fallback stored inline.
 * ──────────────────────────────────────────────────────────────*/

#define RULES_MAX 64

typedef struct {
    int restricted_is_none;         /* "*" sets this */
    int has_restricted;             /* restricted_to is Some */
    char restricted[RULES_MAX][STR_MAX];
    int n_restricted;
    int has_fallback;
    fallback fb;
} rules;

static void rules_init(rules *r) {
    memset(r, 0, sizeof(*r));
    r->has_restricted = 1;  /* restricted_to = Some(Default::default()) */
}

/* Rust FromIterator<I: Into<String>> for Rules */
static void rules_from_iter_str(rules *r, const char *items[], int n) {
    rules_init(r);
    for (int i = 0; i < n; i++) {
        const char *dest = items[i];
        if (strcmp(dest, "*") == 0) {
            r->restricted_is_none = 1;  /* Lift any restrictions */
        } else if (strcmp(dest, "-") == 0) {
            /* no-op: keeps default empty set */
        } else {
            if (r->n_restricted < RULES_MAX) {
                strncpy(r->restricted[r->n_restricted], dest, STR_MAX - 1);
                r->restricted[r->n_restricted][STR_MAX - 1] = '\0';
                r->n_restricted++;
            }
        }
    }
}

/* Rust: "*" lifts restrictions => restricted_to = None => allowed always true.
 * The Rust code sets `restricted_to = None` on "*", which makes `allowed`
 * return true unconditionally (the `if let Some(set)` branch is skipped). */
static int rules_allowed(const rules *r, const char *server_name) {
    if (r->restricted_is_none) return 1;  /* restricted_to = None */
    /* restricted_to = Some(set) */
    for (int i = 0; i < r->n_restricted; i++)
        if (strcmp(r->restricted[i], server_name) == 0)
            return 1;
    return 0;
}

static void rules_set_fallback(rules *r, const fallback *fb) {
    if (fb) { r->has_fallback = 1; r->fb = *fb; }
    else { r->has_fallback = 0; memset(&r->fb, 0, sizeof(r->fb)); }
}

static void rules_fallback(const rules *r, const char *alpn_opt,
                           int *has_value, const char **value) {
    if (!r->has_fallback) { *has_value = 0; *value = NULL; return; }
    fallback_resolve(&r->fb, alpn_opt, has_value, value);
}

/* ──────────────────────────────────────────────────────────────
 * Test helpers
 * ──────────────────────────────────────────────────────────────*/

static int tests_run = 0, tests_failed = 0;
#define TEST(name) static void name(int *fail)
#define RUN(name) do { tests_run++; int f=0; name(&f); if (f) { tests_failed++; printf("[FAIL] %s\n", #name); } else printf("[PASS] %s\n", #name); } while(0)

static void check_opt(int fail_flag, int has_value, const char *value,
                      int exp_has, const char *exp_value, int *fail, const char *lbl) {
    (void)fail_flag;
    if (has_value != exp_has) {
        printf("  %s: has_value %d != expected %d\n", lbl, has_value, exp_has);
        *fail = 1;
    }
    if (exp_has) {
        if (!value) { printf("  %s: value NULL but expected %s\n", lbl, exp_value); *fail = 1; }
        else if (strcmp(value, exp_value) != 0) {
            printf("  %s: value '%s' != expected '%s'\n", lbl, value, exp_value);
            *fail = 1;
        }
    }
}

/* ──────────────────────────────────────────────────────────────
 * alpn.rs #[test] equivalents (7 tests)
 * ──────────────────────────────────────────────────────────────*/

/* #[test] fn test_fallback_from_str */
TEST(alpn_test_fallback_from_str) {
    fallback fb;
    fallback_from_str(&fb, "example.com:80");
    /* assert_eq!(fallback, Fallback { alpn: IndexMap::new(), default: Some("example.com:80") }) */
    if (fb.n_entries != 0) { *fail = 1; printf("  n_entries != 0\n"); }
    if (!fb.has_default || strcmp(fb.default_dest, "example.com:80") != 0) { *fail = 1; printf("  default mismatch\n"); }
    /* assert_eq!(fallback.alpn_protocols(), Vec::<Vec<u8>>::new()) */
    char protos[ALPN_MAX_ENTRIES][STR_MAX];
    int n = fallback_alpn_protocols(&fb, protos, ALPN_MAX_ENTRIES);
    if (n != 0) { *fail = 1; printf("  alpn_protocols not empty\n"); }
    /* assert_eq!(fallback.resolve(None), Some("example.com:80")) */
    int hv; const char *v;
    fallback_resolve(&fb, NULL, &hv, &v);
    check_opt(0, hv, v, 1, "example.com:80", fail, "resolve(None)");
    /* assert_eq!(fallback.resolve(Some(b"http/1.1")), Some("example.com:80")) */
    fallback_resolve(&fb, "http/1.1", &hv, &v);
    check_opt(0, hv, v, 1, "example.com:80", fail, "resolve(http/1.1)");
}

/* #[test] fn test_fallback_empty */
TEST(alpn_test_fallback_empty) {
    fallback fb;
    fallback_from_str(&fb, "");
    /* assert_eq!(fallback, Fallback { alpn: IndexMap::new(), default: Some("") }) */
    if (fb.n_entries != 0) { *fail = 1; printf("  n_entries != 0\n"); }
    if (!fb.has_default || strcmp(fb.default_dest, "") != 0) { *fail = 1; printf("  default mismatch\n"); }
    /* assert_eq!(fallback.alpn_protocols(), Vec::<Vec<u8>>::new()) */
    char protos[ALPN_MAX_ENTRIES][STR_MAX];
    int n = fallback_alpn_protocols(&fb, protos, ALPN_MAX_ENTRIES);
    if (n != 0) { *fail = 1; printf("  alpn_protocols not empty\n"); }
    /* assert_eq!(fallback.resolve(None), Some("")) */
    int hv; const char *v;
    fallback_resolve(&fb, NULL, &hv, &v);
    check_opt(0, hv, v, 1, "", fail, "resolve(None)");
}

/* #[test] fn test_fallback_default_and_alpn_http1 */
TEST(alpn_test_default_and_alpn_http1) {
    fallback fb;
    fallback_from_str(&fb, "http/1.1=,example.com:80");
    /* assert_eq!(fallback, Fallback { alpn: IndexMap::from_iter([(b"http/1.1", AlpnTarget::Default)]), default: Some("example.com:80") }) */
    if (fb.n_entries != 1) { *fail = 1; printf("  n_entries != 1\n"); }
    if (fb.n_entries == 1) {
        if (strcmp(fb.entries[0].alpn, "http/1.1") != 0) { *fail = 1; printf("  alpn key mismatch\n"); }
        if (fb.entries[0].kind != ALPN_DEFAULT) { *fail = 1; printf("  kind != DEFAULT\n"); }
    }
    if (!fb.has_default || strcmp(fb.default_dest, "example.com:80") != 0) { *fail = 1; printf("  default mismatch\n"); }
    /* assert_eq!(fallback.alpn_protocols(), vec![b"http/1.1"]) */
    char protos[ALPN_MAX_ENTRIES][STR_MAX];
    int n = fallback_alpn_protocols(&fb, protos, ALPN_MAX_ENTRIES);
    if (n != 1 || strcmp(protos[0], "http/1.1") != 0) { *fail = 1; printf("  alpn_protocols mismatch\n"); }
    /* assert_eq!(fallback.resolve(None), Some("example.com:80")) */
    int hv; const char *v;
    fallback_resolve(&fb, NULL, &hv, &v);
    check_opt(0, hv, v, 1, "example.com:80", fail, "resolve(None)");
    /* assert_eq!(fallback.resolve(Some(b"http/1.1")), Some("example.com:80")) */
    fallback_resolve(&fb, "http/1.1", &hv, &v);
    check_opt(0, hv, v, 1, "example.com:80", fail, "resolve(http/1.1)");
}

/* #[test] fn test_fallback_default_and_different_alpn_http1 */
TEST(alpn_test_default_and_different_alpn_http1) {
    fallback fb;
    fallback_from_str(&fb, "http/1.1=127.0.0.1:8080,example.com:80");
    /* assert_eq!(fallback, Fallback { alpn: IndexMap::from_iter([(b"http/1.1", AlpnTarget::Value("127.0.0.1:8080"))]), default: Some("example.com:80") }) */
    if (fb.n_entries != 1) { *fail = 1; printf("  n_entries != 1\n"); }
    if (fb.n_entries == 1) {
        if (strcmp(fb.entries[0].alpn, "http/1.1") != 0) { *fail = 1; printf("  alpn key mismatch\n"); }
        if (fb.entries[0].kind != ALPN_VALUE) { *fail = 1; printf("  kind != VALUE\n"); }
        if (strcmp(fb.entries[0].value, "127.0.0.1:8080") != 0) { *fail = 1; printf("  value mismatch\n"); }
    }
    if (!fb.has_default || strcmp(fb.default_dest, "example.com:80") != 0) { *fail = 1; printf("  default mismatch\n"); }
    /* assert_eq!(fallback.alpn_protocols(), vec![b"http/1.1"]) */
    char protos[ALPN_MAX_ENTRIES][STR_MAX];
    int n = fallback_alpn_protocols(&fb, protos, ALPN_MAX_ENTRIES);
    if (n != 1 || strcmp(protos[0], "http/1.1") != 0) { *fail = 1; printf("  alpn_protocols mismatch\n"); }
    /* assert_eq!(fallback.resolve(None), Some("example.com:80")) */
    int hv; const char *v;
    fallback_resolve(&fb, NULL, &hv, &v);
    check_opt(0, hv, v, 1, "example.com:80", fail, "resolve(None)");
    /* assert_eq!(fallback.resolve(Some(b"http/1.1")), Some("127.0.0.1:8080")) */
    fallback_resolve(&fb, "http/1.1", &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8080", fail, "resolve(http/1.1)");
}

/* #[test] fn test_fallback_alpn_http1_only */
TEST(alpn_test_alpn_http1_only) {
    fallback fb;
    fallback_from_str(&fb, "http/1.1=127.0.0.1:8080");
    /* assert_eq!(fallback, Fallback { alpn: IndexMap::from_iter([(b"http/1.1", AlpnTarget::Value("127.0.0.1:8080"))]), default: None }) */
    if (fb.n_entries != 1) { *fail = 1; printf("  n_entries != 1\n"); }
    if (fb.n_entries == 1) {
        if (strcmp(fb.entries[0].alpn, "http/1.1") != 0) { *fail = 1; printf("  alpn key mismatch\n"); }
        if (fb.entries[0].kind != ALPN_VALUE) { *fail = 1; printf("  kind != VALUE\n"); }
        if (strcmp(fb.entries[0].value, "127.0.0.1:8080") != 0) { *fail = 1; printf("  value mismatch\n"); }
    }
    if (fb.has_default) { *fail = 1; printf("  default should be None\n"); }
    /* assert_eq!(fallback.alpn_protocols(), vec![b"http/1.1"]) */
    char protos[ALPN_MAX_ENTRIES][STR_MAX];
    int n = fallback_alpn_protocols(&fb, protos, ALPN_MAX_ENTRIES);
    if (n != 1 || strcmp(protos[0], "http/1.1") != 0) { *fail = 1; printf("  alpn_protocols mismatch\n"); }
    /* assert_eq!(fallback.resolve(None), None) */
    int hv; const char *v;
    fallback_resolve(&fb, NULL, &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "resolve(None)");
    /* assert_eq!(fallback.resolve(Some(b"http/1.1")), Some("127.0.0.1:8080")) */
    fallback_resolve(&fb, "http/1.1", &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8080", fail, "resolve(http/1.1)");
}

/* #[test] fn test_fallback_alpn_prefer_http1_over_h2 */
TEST(alpn_test_alpn_prefer_http1_over_h2) {
    fallback fb;
    fallback_from_str(&fb, "http/1.1=127.0.0.1:8080,h2=127.0.0.1:8081");
    /* assert_eq!(fallback, Fallback { alpn: IndexMap::from_iter([(b"http/1.1", Value("127.0.0.1:8080")), (b"h2", Value("127.0.0.1:8081"))]), default: None }) */
    if (fb.n_entries != 2) { *fail = 1; printf("  n_entries != 2\n"); }
    if (fb.n_entries >= 1) {
        if (strcmp(fb.entries[0].alpn, "http/1.1") != 0) { *fail = 1; printf("  entry0 alpn mismatch\n"); }
        if (fb.entries[0].kind != ALPN_VALUE || strcmp(fb.entries[0].value, "127.0.0.1:8080") != 0) { *fail = 1; printf("  entry0 value mismatch\n"); }
    }
    if (fb.n_entries >= 2) {
        if (strcmp(fb.entries[1].alpn, "h2") != 0) { *fail = 1; printf("  entry1 alpn mismatch\n"); }
        if (fb.entries[1].kind != ALPN_VALUE || strcmp(fb.entries[1].value, "127.0.0.1:8081") != 0) { *fail = 1; printf("  entry1 value mismatch\n"); }
    }
    if (fb.has_default) { *fail = 1; printf("  default should be None\n"); }
    /* assert_eq!(fallback.alpn_protocols(), vec![b"http/1.1", b"h2"]) */
    char protos[ALPN_MAX_ENTRIES][STR_MAX];
    int n = fallback_alpn_protocols(&fb, protos, ALPN_MAX_ENTRIES);
    if (n != 2 || strcmp(protos[0], "http/1.1") != 0 || strcmp(protos[1], "h2") != 0) { *fail = 1; printf("  alpn_protocols mismatch\n"); }
    /* assert_eq!(fallback.resolve(None), None) */
    int hv; const char *v;
    fallback_resolve(&fb, NULL, &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "resolve(None)");
    /* assert_eq!(fallback.resolve(Some(b"http/1.1")), Some("127.0.0.1:8080")) */
    fallback_resolve(&fb, "http/1.1", &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8080", fail, "resolve(http/1.1)");
    /* assert_eq!(fallback.resolve(Some(b"h2")), Some("127.0.0.1:8081")) */
    fallback_resolve(&fb, "h2", &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8081", fail, "resolve(h2)");
    /* assert_eq!(fallback.resolve(Some(b"xyz")), None) */
    fallback_resolve(&fb, "xyz", &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "resolve(xyz)");
}

/* #[test] fn test_fallback_alpn_prefer_h2_over_http1 */
TEST(alpn_test_alpn_prefer_h2_over_http1) {
    fallback fb;
    fallback_from_str(&fb, "h2=127.0.0.1:8081,http/1.1=127.0.0.1:8080");
    /* assert_eq!(fallback, Fallback { alpn: IndexMap::from_iter([(b"http/1.1", Value("127.0.0.1:8080")), (b"h2", Value("127.0.0.1:8081"))]), default: None }) */
    if (fb.n_entries != 2) { *fail = 1; printf("  n_entries != 2\n"); }
    /* IndexMap preserves insertion order: h2 first, then http/1.1 */
    if (fb.n_entries >= 1) {
        if (strcmp(fb.entries[0].alpn, "h2") != 0) { *fail = 1; printf("  entry0 alpn mismatch\n"); }
        if (fb.entries[0].kind != ALPN_VALUE || strcmp(fb.entries[0].value, "127.0.0.1:8081") != 0) { *fail = 1; printf("  entry0 value mismatch\n"); }
    }
    if (fb.n_entries >= 2) {
        if (strcmp(fb.entries[1].alpn, "http/1.1") != 0) { *fail = 1; printf("  entry1 alpn mismatch\n"); }
        if (fb.entries[1].kind != ALPN_VALUE || strcmp(fb.entries[1].value, "127.0.0.1:8080") != 0) { *fail = 1; printf("  entry1 value mismatch\n"); }
    }
    if (fb.has_default) { *fail = 1; printf("  default should be None\n"); }
    /* assert_eq!(fallback.alpn_protocols(), vec![b"h2", b"http/1.1"]) */
    char protos[ALPN_MAX_ENTRIES][STR_MAX];
    int n = fallback_alpn_protocols(&fb, protos, ALPN_MAX_ENTRIES);
    if (n != 2 || strcmp(protos[0], "h2") != 0 || strcmp(protos[1], "http/1.1") != 0) { *fail = 1; printf("  alpn_protocols mismatch\n"); }
    /* assert_eq!(fallback.resolve(None), None) */
    int hv; const char *v;
    fallback_resolve(&fb, NULL, &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "resolve(None)");
    /* assert_eq!(fallback.resolve(Some(b"http/1.1")), Some("127.0.0.1:8080")) */
    fallback_resolve(&fb, "http/1.1", &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8080", fail, "resolve(http/1.1)");
    /* assert_eq!(fallback.resolve(Some(b"h2")), Some("127.0.0.1:8081")) */
    fallback_resolve(&fb, "h2", &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8081", fail, "resolve(h2)");
    /* assert_eq!(fallback.resolve(Some(b"xyz")), None) */
    fallback_resolve(&fb, "xyz", &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "resolve(xyz)");
}

/* ──────────────────────────────────────────────────────────────
 * rules.rs #[test] equivalents (8 tests)
 * ──────────────────────────────────────────────────────────────*/

/* #[test] fn rules_from_iter */
TEST(rules_test_from_iter) {
    rules r;
    const char *items[] = {"example.com", "example.org"};
    rules_from_iter_str(&r, items, 2);
    /* assert_eq!(rules, Rules { restricted_to: Some({"example.com","example.org"}), fallback: None }) */
    if (!r.has_restricted) { *fail = 1; printf("  has_restricted should be true\n"); }
    if (r.restricted_is_none) { *fail = 1; printf("  restricted_is_none should be false\n"); }
    if (r.n_restricted != 2) { *fail = 1; printf("  n_restricted != 2\n"); }
    if (r.has_fallback) { *fail = 1; printf("  has_fallback should be false\n"); }
    /* assert!(rules.allowed("example.com")) */
    if (!rules_allowed(&r, "example.com")) { *fail = 1; printf("  allowed(example.com) should be true\n"); }
    /* assert!(!rules.allowed("example.xyz")) */
    if (rules_allowed(&r, "example.xyz")) { *fail = 1; printf("  allowed(example.xyz) should be false\n"); }
    /* assert_eq!(rules.fallback(None), None) */
    int hv; const char *v;
    rules_fallback(&r, NULL, &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "fallback(None)");
}

/* #[test] fn rules_from_iter_empty */
TEST(rules_test_from_iter_empty) {
    rules r;
    const char *items[] = {NULL};
    rules_from_iter_str(&r, items, 0);
    /* assert_eq!(rules, Rules { restricted_to: Some(Default::default()), fallback: None }) */
    if (!r.has_restricted) { *fail = 1; printf("  has_restricted should be true\n"); }
    if (r.restricted_is_none) { *fail = 1; printf("  restricted_is_none should be false\n"); }
    if (r.n_restricted != 0) { *fail = 1; printf("  n_restricted != 0\n"); }
    if (r.has_fallback) { *fail = 1; printf("  has_fallback should be false\n"); }
    /* assert!(!rules.allowed("example.com")) */
    if (rules_allowed(&r, "example.com")) { *fail = 1; printf("  allowed(example.com) should be false\n"); }
    /* assert_eq!(rules.fallback(None), None) */
    int hv; const char *v;
    rules_fallback(&r, NULL, &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "fallback(None)");
}

/* #[test] fn rules_allow_all */
TEST(rules_test_allow_all) {
    rules r;
    const char *items[] = {"a", "*", "b"};
    rules_from_iter_str(&r, items, 3);
    /* assert_eq!(rules, Rules { restricted_to: None, fallback: None }) */
    if (!r.restricted_is_none) { *fail = 1; printf("  restricted_is_none should be true\n"); }
    if (r.has_fallback) { *fail = 1; printf("  has_fallback should be false\n"); }
    /* assert!(rules.allowed("example.com")) */
    if (!rules_allowed(&r, "example.com")) { *fail = 1; printf("  allowed(example.com) should be true\n"); }
    /* assert!(rules.allowed("example.xyz")) */
    if (!rules_allowed(&r, "example.xyz")) { *fail = 1; printf("  allowed(example.xyz) should be true\n"); }
    /* assert_eq!(rules.fallback(None), None) */
    int hv; const char *v;
    rules_fallback(&r, NULL, &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "fallback(None)");
}

/* #[test] fn rules_disallow_all */
TEST(rules_test_disallow_all) {
    rules r;
    const char *items[] = {"-"};
    rules_from_iter_str(&r, items, 1);
    /* assert_eq!(rules, Rules { restricted_to: Some(Default::default()), fallback: None }) */
    if (!r.has_restricted) { *fail = 1; printf("  has_restricted should be true\n"); }
    if (r.restricted_is_none) { *fail = 1; printf("  restricted_is_none should be false\n"); }
    if (r.n_restricted != 0) { *fail = 1; printf("  n_restricted != 0\n"); }
    if (r.has_fallback) { *fail = 1; printf("  has_fallback should be false\n"); }
    /* assert!(!rules.allowed("example.com")) */
    if (rules_allowed(&r, "example.com")) { *fail = 1; printf("  allowed(example.com) should be false\n"); }
    /* assert!(!rules.allowed("example.xyz")) */
    if (rules_allowed(&r, "example.xyz")) { *fail = 1; printf("  allowed(example.xyz) should be false\n"); }
    /* assert_eq!(rules.fallback(None), None) */
    int hv; const char *v;
    rules_fallback(&r, NULL, &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "fallback(None)");
}

/* #[test] fn rules_edgecase_disallow_all_mixed_with_allow */
TEST(rules_test_edgecase_disallow_all_mixed_with_allow) {
    rules r;
    const char *items[] = {"example.com", "-", "example.org"};
    rules_from_iter_str(&r, items, 3);
    /* assert_eq!(rules, Rules { restricted_to: Some({"example.com","example.org"}), fallback: None }) */
    if (!r.has_restricted) { *fail = 1; printf("  has_restricted should be true\n"); }
    if (r.restricted_is_none) { *fail = 1; printf("  restricted_is_none should be false\n"); }
    if (r.n_restricted != 2) { *fail = 1; printf("  n_restricted != 2\n"); }
    if (r.has_fallback) { *fail = 1; printf("  has_fallback should be false\n"); }
    /* assert!(rules.allowed("example.com")) */
    if (!rules_allowed(&r, "example.com")) { *fail = 1; printf("  allowed(example.com) should be true\n"); }
    /* assert!(!rules.allowed("example.xyz")) */
    if (rules_allowed(&r, "example.xyz")) { *fail = 1; printf("  allowed(example.xyz) should be false\n"); }
    /* assert_eq!(rules.fallback(None), None) */
    int hv; const char *v;
    rules_fallback(&r, NULL, &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "fallback(None)");
}

/* #[test] fn rules_with_default_fallback */
TEST(rules_test_with_default_fallback) {
    rules r;
    const char *items[] = {"example.com", "example.org"};
    rules_from_iter_str(&r, items, 2);
    fallback fb;
    fallback_from_str(&fb, "127.0.0.1:8080");
    rules_set_fallback(&r, &fb);
    /* assert!(rules.allowed("example.com")) */
    if (!rules_allowed(&r, "example.com")) { *fail = 1; printf("  allowed(example.com) should be true\n"); }
    /* assert!(!rules.allowed("example.xyz")) */
    if (rules_allowed(&r, "example.xyz")) { *fail = 1; printf("  allowed(example.xyz) should be false\n"); }
    /* assert_eq!(rules.fallback(None), Some("127.0.0.1:8080")) */
    int hv; const char *v;
    rules_fallback(&r, NULL, &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8080", fail, "fallback(None)");
}

/* #[test] fn rules_with_default_and_alpn_fallback */
TEST(rules_test_with_default_and_alpn_fallback) {
    rules r;
    const char *items[] = {"example.com", "example.org"};
    rules_from_iter_str(&r, items, 2);
    fallback fb;
    fallback_from_str(&fb, "http/1.1=,127.0.0.1:8080");
    rules_set_fallback(&r, &fb);
    /* assert!(rules.allowed("example.com")) */
    if (!rules_allowed(&r, "example.com")) { *fail = 1; printf("  allowed(example.com) should be true\n"); }
    /* assert!(!rules.allowed("example.xyz")) */
    if (rules_allowed(&r, "example.xyz")) { *fail = 1; printf("  allowed(example.xyz) should be false\n"); }
    /* assert_eq!(rules.fallback(None), Some("127.0.0.1:8080")) */
    int hv; const char *v;
    rules_fallback(&r, NULL, &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8080", fail, "fallback(None)");
    /* assert_eq!(rules.fallback(Some(b"http/1.1")), Some("127.0.0.1:8080")) */
    rules_fallback(&r, "http/1.1", &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8080", fail, "fallback(http/1.1)");
    /* assert_eq!(rules.fallback(Some(b"xyz")), Some("127.0.0.1:8080")) */
    rules_fallback(&r, "xyz", &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8080", fail, "fallback(xyz)");
}

/* #[test] fn rules_with_alpn_only_fallback */
TEST(rules_test_with_alpn_only_fallback) {
    rules r;
    const char *items[] = {"example.com", "example.org"};
    rules_from_iter_str(&r, items, 2);
    fallback fb;
    fallback_from_str(&fb, "http/1.1=127.0.0.1:8080");
    rules_set_fallback(&r, &fb);
    /* assert!(rules.allowed("example.com")) */
    if (!rules_allowed(&r, "example.com")) { *fail = 1; printf("  allowed(example.com) should be true\n"); }
    /* assert!(!rules.allowed("example.xyz")) */
    if (rules_allowed(&r, "example.xyz")) { *fail = 1; printf("  allowed(example.xyz) should be false\n"); }
    /* assert_eq!(rules.fallback(None), None) */
    int hv; const char *v;
    rules_fallback(&r, NULL, &hv, &v);
    check_opt(0, hv, v, 0, NULL, fail, "fallback(None)");
    /* assert_eq!(rules.fallback(Some(b"http/1.1")), Some("127.0.0.1:8080")) */
    rules_fallback(&r, "http/1.1", &hv, &v);
    check_opt(0, hv, v, 1, "127.0.0.1:8080", fail, "fallback(http/1.1)");
}

/* ──────────────────────────────────────────────────────────────
 * Main: run all 15 upstream #[test] equivalents
 * ──────────────────────────────────────────────────────────────*/

int main(void) {
    printf("=== signal-tlsd 0.1.3 Conan test_package (OpenHarmony/aarch64) ===\n");
    printf("=== Verifying upstream 15 #[test] unit tests via C equivalent ===\n\n");

    /* alpn.rs #[test] (7) */
    printf("--- src/alpn.rs #[test] (7) ---\n");
    RUN(alpn_test_fallback_from_str);
    RUN(alpn_test_fallback_empty);
    RUN(alpn_test_default_and_alpn_http1);
    RUN(alpn_test_default_and_different_alpn_http1);
    RUN(alpn_test_alpn_http1_only);
    RUN(alpn_test_alpn_prefer_http1_over_h2);
    RUN(alpn_test_alpn_prefer_h2_over_http1);

    /* rules.rs #[test] (8) */
    printf("\n--- src/rules.rs #[test] (8) ---\n");
    RUN(rules_test_from_iter);
    RUN(rules_test_from_iter_empty);
    RUN(rules_test_allow_all);
    RUN(rules_test_disallow_all);
    RUN(rules_test_edgecase_disallow_all_mixed_with_allow);
    RUN(rules_test_with_default_fallback);
    RUN(rules_test_with_default_and_alpn_fallback);
    RUN(rules_test_with_alpn_only_fallback);

    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_run - tests_failed, tests_run, tests_failed);

    /* hmbs hard-gate markers — counts sourced from the same
     * tests_run/tests_failed counters as the Results line above. */
    {
        int discovered = 15;       /* 7 alpn.rs + 8 rules.rs #[test] */
        int executed = tests_run;  /* every #[test] equivalent ran */
        int passed = tests_run - tests_failed;
        int failed = tests_failed;
        int skipped = 0;           /* C harness has no skip mechanism */
        const char *status = (failed == 0) ? "passed" : "failed";

        printf("HMBS_UPSTREAM_TEST_RESULT={\"status\":\"%s\",\"framework\":\"ctest\",\"command\":\"%s\",\"discovered\":%d,\"executed\":%d,\"passed\":%d,\"failed\":%d,\"skipped\":%d}\n",
               status, "test_signal_tlsd", discovered, executed, passed, failed, skipped);
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"%s\",\"discovered\":%d,\"passedCount\":%d}\n",
               (failed == 0) ? "true" : "false", "test_signal_tlsd", discovered, passed);
    }

    if (tests_failed == 0) {
        printf("\nAll upstream #[test] equivalents PASSED.\n");
        return 0;
    }
    printf("\n%d test(s) FAILED.\n", tests_failed);
    return 1;
}
