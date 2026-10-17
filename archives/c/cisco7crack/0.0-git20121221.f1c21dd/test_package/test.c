/* test.c — test_package for cisco7crack 0.0-git20121221.f1c21dd (R34).
 *
 * cisco7crack is a CLI tool, so the test drives the installed binary and
 * asserts real behaviour:
 *   1. known-answer decrypt:  -d 104D000A0618  -> "cisco"
 *      (the very example quoted in the upstream source header)
 *   2. deterministic crypt:   -c#9 -q gHa5ecret1 -> 094B66084C0014000E1855
 *      (fixed xor offset 9 => stable known-answer, recorded on the target)
 *   3. round-trip decrypt of that ciphertext back to "gHa5ecret1"
 *   4. illegal input (odd hex digits) -> exit status 4 with a warning
 *
 * The binary path is passed as argv[1]; the test fails when the package
 * artifacts are removed (CI L1e destructive negative test).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *crack_bin = NULL;
static int failures = 0;

static void check(int ok, const char *what)
{
    if (ok) {
        printf("PASS: %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

/* Run the binary with args and capture stdout; returns exit status. */
static int run_capture(char *const argv[], char *out, size_t outsz)
{
    char cmd[2048];
    char joined[1024] = "";
    int i, rc;

    for (i = 0; argv[i] != NULL; i++) {
        if (i > 0)
            strncat(joined, " ", sizeof(joined) - strlen(joined) - 1);
        strncat(joined, argv[i], sizeof(joined) - strlen(joined) - 1);
    }
    snprintf(cmd, sizeof(cmd), "\"%s\" %s 2>&1", crack_bin, joined);

    FILE *fp = popen(cmd, "r");
    if (fp == NULL)
        return -1;
    size_t got = fread(out, 1, outsz - 1, fp);
    out[got] = '\0';
    rc = pclose(fp);
    if (rc == -1)
        return -1;
    return WEXITSTATUS(rc);
}

int main(int argc, char *argv[])
{
    char out[512];

    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-cisco7crack>\n", argv[0]);
        return 1;
    }
    crack_bin = argv[1];
    printf("Testing cisco7crack binary: %s\n", crack_bin);

    /* 1. known-answer decrypt (example from the upstream source header) */
    {
        char *argv2[] = { (char *)"-d", (char *)"104D000A0618", NULL };
        int rc = run_capture(argv2, out, sizeof(out));
        check(rc == 0 && strstr(out, "Plain string     : cisco") != NULL,
              "-d 104D000A0618 decrypts to \"cisco\"");
    }

    /* 2. deterministic crypt with fixed xor offset 9 */
    {
        char *argv2[] = { (char *)"-c#9", (char *)"-q", (char *)"gHa5ecret1", NULL };
        int rc = run_capture(argv2, out, sizeof(out));
        out[strcspn(out, "\r\n")] = '\0';
        check(rc == 0 && strcmp(out, "094B66084C0014000E1855") == 0,
              "-c#9 -q gHa5ecret1 yields 094B66084C0014000E1855");
    }

    /* 3. round-trip: decrypting that ciphertext restores the plaintext */
    {
        char *argv2[] = { (char *)"-d", (char *)"094B66084C0014000E1855", NULL };
        int rc = run_capture(argv2, out, sizeof(out));
        check(rc == 0 && strstr(out, "Plain string     : gHa5ecret1") != NULL,
              "-d 094B66084C0014000E1855 restores \"gHa5ecret1\"");
    }

    /* 4. illegal input: odd number of hex digits -> exit 4 */
    {
        char *argv2[] = { (char *)"-d", (char *)"104", NULL };
        int rc = run_capture(argv2, out, sizeof(out));
        check(rc == 4 && strstr(out, "odd number") != NULL,
              "-d 104 (odd digits) fails with exit 4 and a warning");
    }

    if (failures != 0) {
        printf("%d test(s) failed\n", failures);
        return 1;
    }
    printf("All tests passed\n");
    return 0;
}
