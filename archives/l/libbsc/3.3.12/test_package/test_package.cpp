/* test_package for libbsc 3.3.12 on HarmonyOS PC (aarch64).
 *
 * Real round-trip verification: bsc_init -> bsc_compress -> bsc_decompress
 * -> memcmp on two corpora (synthetic pattern + real file data). Exits
 * non-zero on any mismatch. Prints version macros in effect.
 *
 * Multi-threading feature is explicitly NOT requested (features = FASTMODE
 * only): the OHOS build ships without libomp, so we exercise the
 * single-thread path that is actually delivered.
 */

/* upstream header uses size_t in prototypes without including <stddef.h>:
   include it BEFORE libbsc.h so the type is visible to its prototypes */
#include <stddef.h>

#include <libbsc/libbsc.h>
#include <libbsc/filters.h>

#include <cstdio>
#include <cstring>
#include <vector>

/* Corpus 1: highly-repetitive synthetic pattern (BWT-friendly). */
static const char *kSynthetic = "HARMONYOS_LIBBSC_ROUNDTRIP_1234567890_";

/* Corpus 2: real file contents (/etc/profile on the test host). */
static std::vector<unsigned char> load_real_file(const char *path) {
    std::vector<unsigned char> data;
    FILE *f = fopen(path, "rb");
    if (!f) return data;
    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0)
        data.insert(data.end(), buf, buf + n);
    fclose(f);
    return data;
}

static int roundtrip(const std::vector<unsigned char> &input, const char *label) {
    const int n = static_cast<int>(input.size());
    if (n == 0) {
        printf("[SKIP] %s: empty corpus\n", label);
        return 0;
    }

    /* FASTMODE only — single-threaded path (no libomp on OHOS). */
    const int features = LIBBSC_FEATURE_FASTMODE;

    std::vector<unsigned char> compressed(n + LIBBSC_HEADER_SIZE + 1024);
    std::vector<unsigned char> decompressed(n + 1024);

    printf("[%s] input %d bytes\n", label, n);

    const int r_compress = bsc_compress(
        input.data(), compressed.data(), n,
        LIBBSC_DEFAULT_LZPHASHSIZE, LIBBSC_DEFAULT_LZPMINLEN,
        LIBBSC_DEFAULT_BLOCKSORTER, LIBBSC_DEFAULT_CODER, features);
    if (r_compress < 0) {
        printf("FAIL: bsc_compress returned %d\n", r_compress);
        return 1;
    }
    printf("[%s] compressed %d -> %d bytes\n", label, n, r_compress);

    const int r_decompress = bsc_decompress(compressed.data(), r_compress,
                                            decompressed.data(), n, features);
    if (r_decompress != LIBBSC_NO_ERROR) {
        printf("FAIL: bsc_decompress returned %d\n", r_decompress);
        return 1;
    }

    if (memcmp(input.data(), decompressed.data(), n) != 0) {
        printf("FAIL: content mismatch after round-trip\n");
        return 1;
    }
    printf("[%s] round-trip OK: %d -> %d -> %d bytes (byte-identical)\n",
           label, n, r_compress, n);
    return 0;
}

int main() {
    printf("libbsc %d.%d.%d (LIBBSC_VERSION_STRING %s)\n",
           LIBBSC_VERSION_MAJOR, LIBBSC_VERSION_MINOR, LIBBSC_VERSION_PATCH,
           LIBBSC_VERSION_STRING);

    if (bsc_init(LIBBSC_FEATURE_FASTMODE) != LIBBSC_NO_ERROR) {
        printf("FAIL: bsc_init failed\n");
        return 1;
    }

    int failures = 0;

    /* Corpus 1: synthetic pattern repeated to ~64 KiB. */
    std::vector<unsigned char> synthetic;
    for (int i = 0; i < 64 * 1024 / (int)strlen(kSynthetic) + 1; ++i)
        synthetic.insert(synthetic.end(), kSynthetic, kSynthetic + strlen(kSynthetic));
    failures += roundtrip(synthetic, "synthetic");

    /* Corpus 2: real file (/etc/profile, ~1 KiB of shell config). */
    const auto real = load_real_file("/etc/profile");
    if (!real.empty()) {
        failures += roundtrip(real, "/etc/profile");
    } else {
        printf("[SKIP] /etc/profile unreadable; synthetic corpus only\n");
    }

    if (failures) {
        printf("RESULT: FAIL (%d corpus(es) failed)\n", failures);
        return 1;
    }
    printf("RESULT: PASS\n");
    return 0;
}
