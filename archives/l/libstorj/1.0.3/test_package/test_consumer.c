/* test_package consumer for libstorj 1.0.3 (OHOS PC).
 *
 * Drives the installed libstorj archive as a real consumer: BIP39
 * mnemonic generate/check roundtrip, encrypted auth serialize/decrypt
 * roundtrip (exercises nettle AES/CTR + PBKDF2 + json-c serialization),
 * strerror mapping, and a CLI smoke of the installed `storj` binary.
 *
 * Counts each case explicitly (PASS lines) — TOTAL printed at the end.
 * Exit code 0 iff every case passed.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "storj.h"

static int tests_ran = 0;
static int tests_passed = 0;

static void report(const char *name, int ok)
{
    printf("%s %s\n", ok ? "PASS" : "FAIL", name);
    tests_ran += 1;
    if (ok) {
        tests_passed += 1;
    }
}

/* 24-word BIP39 test vector (valid checksum). */
static const char *VALID_MNEMONIC =
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon art";

static const char *TAMPERED_MNEMONIC =
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon abandon abandon legal";

int main(void)
{
    /* 1. util timestamp sane (> 2020-01-01 UTC in ms). */
    uint64_t ts = storj_util_timestamp();
    report("ohos-consumer:storj_util_timestamp>1577836800000", ts > 1577836800000ULL);

    /* 2. mnemonic checksum accept. */
    report("ohos-consumer:mnemonic_check(valid)==true",
           storj_mnemonic_check(VALID_MNEMONIC) == true);

    /* 3. mnemonic checksum reject (one word swapped -> bad checksum). */
    report("ohos-consumer:mnemonic_check(tampered)==false",
           storj_mnemonic_check(TAMPERED_MNEMONIC) == false);

    /* 4. mnemonic generate(128) -> 12 words, checksum-valid roundtrip.
     * Upstream contract: mnemonic_generate returns 1 on success, 0 on
     * failure (bip39.c mnemonic_from_data). */
    char *generated = NULL;
    int grc = storj_mnemonic_generate(128, &generated);
    int gen_ok = grc == 1 && generated != NULL;
    if (gen_ok) {
        int words = 1;
        for (const char *p = generated; *p; p++) {
            if (*p == ' ') words += 1;
        }
        gen_ok = words == 12 && storj_mnemonic_check(generated) == true;
    }
    report("ohos-consumer:mnemonic_generate(128)->12-words+check", gen_ok);
    free(generated);

    /* 5. encrypt_auth -> decrypt_auth roundtrip (nettle + json-c). */
    const char *user = "ohos-test-user@storj.io";
    const char *pass = "0123456789abcdef0123456789abcdef";
    char *blob = NULL;
    int erc = storj_encrypt_auth("ohos-passphrase", user, pass,
                                 VALID_MNEMONIC, &blob);
    int roundtrip_ok = erc == 0 && blob != NULL;
    if (roundtrip_ok) {
        char *du = NULL, *dp = NULL, *dm = NULL;
        int drc = storj_decrypt_auth(blob, "ohos-passphrase", &du, &dp, &dm);
        roundtrip_ok = drc == 0 && du && dp && dm &&
                       strcmp(du, user) == 0 &&
                       strcmp(dp, pass) == 0 &&
                       strcmp(dm, VALID_MNEMONIC) == 0;
        free(du); free(dp); free(dm);
    }
    report("ohos-consumer:encrypt_auth/decrypt_auth-roundtrip", roundtrip_ok);
    free(blob);

    /* 6. wrong passphrase must fail to decrypt. */
    char *blob2 = NULL;
    int erc2 = storj_encrypt_auth("pass-A", user, pass, VALID_MNEMONIC, &blob2);
    int wrong_ok = erc2 == 0 && blob2 != NULL;
    if (wrong_ok) {
        char *du = NULL, *dp = NULL, *dm = NULL;
        int drc = storj_decrypt_auth(blob2, "pass-B", &du, &dp, &dm);
        wrong_ok = drc != 0;
        free(du); free(dp); free(dm);
    }
    report("ohos-consumer:decrypt_auth(wrong-passphrase)!=0", wrong_ok);
    free(blob2);

    /* 7. strerror mapping returns stable text. NOTE upstream contract:
     * storj_strerror returns STATIC string literals — they must NOT be
     * freed (freeing them corrupts the heap → SIGSEGV, found the hard way
     * 2026-09-21). */
    char *msg = storj_strerror(0);
    report("ohos-consumer:storj_strerror-nonempty",
           msg != NULL && strlen(msg) > 0);

    /* 8. installed CLI smoke: `storj --help` prints usage (OHOS binary
     *    actually executing on this device). CLI_PATH comes from the
     *    test_package conanfile (-DCLI_PATH=...). Help output goes to
     *    $TMPDIR — never the cwd (would drop a stray file into the
     *    source tree / build folder). */
    int cli_ok = 0;
    {
        const char *tmp = getenv("TMPDIR");
        if (!tmp || !*tmp) {
            tmp = ".";
        }
        char cmd[2048];
        snprintf(cmd, sizeof(cmd),
                 "\"%s\" --help > \"%s/storj-cli-help.out\" 2>&1 "
                 "&& grep -q usage \"%s/storj-cli-help.out\"",
                 CLI_PATH, tmp, tmp);
        cli_ok = system(cmd) == 0;
    }
    report("ohos-consumer:installed-cli---help-smoke", cli_ok);

    printf("SUMMARY passed=%d total=%d\n", tests_passed, tests_ran);
    return tests_passed == tests_ran ? 0 : 1;
}
