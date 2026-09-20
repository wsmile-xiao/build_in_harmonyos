/* Consumer test for the packaged libofa library.
 *
 * Links against the installed headers/library (find_package(libofa)) and
 * exercises the whole public C API from <ofa1/ofa.h>: ofa_get_version() and
 * end-to-end ofa_create_print() on synthetic PCM, checking output validity
 * and determinism. Each passing check prints one "CHECK-OK: <name>" line;
 * the driver script counts those lines for the HMBS evidence marker.
 */
#include <math.h>
#include <ofa1/ofa.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TONE_PI 3.14159265358979323846
#define SAMPLE_RATE 44100
#define TONE_SECONDS 15
#define TONE_FREQ 440.0
#define TONE_AMPLITUDE 15000.0

static int failures = 0;

static void report(const char *name, int ok)
{
    if (ok) {
        printf("CHECK-OK: %s\n", name);
    } else {
        printf("CHECK-FAIL: %s\n", name);
        failures++;
    }
    fflush(stdout);
}

static int is_base64_char(char c)
{
    return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
           (c >= '0' && c <= '9') || c == '+' || c == '/' || c == '=';
}

/* Build TONE_SECONDS of a 440 Hz sine wave, 16-bit mono samples. */
static short *make_tone(long *out_samples)
{
    long n = (long)SAMPLE_RATE * (long)TONE_SECONDS;
    short *buf = (short *)malloc((size_t)n * sizeof(short));
    long i;

    if (!buf) {
        return NULL;
    }
    for (i = 0; i < n; i++) {
        double t = (double)i / (double)SAMPLE_RATE;
        buf[i] = (short)(TONE_AMPLITUDE * sin(2.0 * TONE_PI * TONE_FREQ * t));
    }
    *out_samples = n;
    return buf;
}

int main(void)
{
    int major = -1, minor = -1, rev = -1;
    long n = 0;
    short *tone = NULL;
    const char *print1;
    const char *print2;
    char first[768];
    char second[768];
    size_t len, i;
    int valid;

    printf("PLAN 6\n");
    fflush(stdout);

    /* 1-3: the library reports its own build version 0.9.3. */
    ofa_get_version(&major, &minor, &rev);
    printf("libofa version: %d.%d.%d\n", major, minor, rev);
    report("version-major", major == 0);
    report("version-minor", minor == 9);
    report("version-rev", rev == 3);

    /* 4: a tonal excerpt yields a fingerprint (no network involved). */
    tone = make_tone(&n);
    if (!tone) {
        report("fingerprint-nonnull", 0);
        report("fingerprint-content", 0);
        report("fingerprint-deterministic", 0);
        return 1;
    }
    /* The call destroys the input buffer, so each call gets a fresh copy. */
    print1 = ofa_create_print((unsigned char *)tone, OFA_LITTLE_ENDIAN,
                              n, SAMPLE_RATE, 0);
    free(tone);
    tone = NULL;
    report("fingerprint-nonnull", print1 != NULL);
    if (!print1) {
        report("fingerprint-content", 0);
        report("fingerprint-deterministic", 0);
        return 1;
    }
    strncpy(first, print1, sizeof(first) - 1);
    first[sizeof(first) - 1] = '\0';

    /* 5: the fingerprint is a non-trivial base64 text. */
    len = strlen(first);
    printf("fingerprint length: %lu\n", (unsigned long)len);
    valid = (len > 100 && len < sizeof(first) - 1);
    for (i = 0; valid && i < len; i++) {
        if (!is_base64_char(first[i])) {
            valid = 0;
        }
    }
    report("fingerprint-content", valid);

    /* 6: the same audio always yields the same fingerprint. */
    tone = make_tone(&n);
    if (!tone) {
        report("fingerprint-deterministic", 0);
        return 1;
    }
    print2 = ofa_create_print((unsigned char *)tone, OFA_LITTLE_ENDIAN,
                              n, SAMPLE_RATE, 0);
    free(tone);
    tone = NULL;
    if (!print2) {
        report("fingerprint-deterministic", 0);
        return 1;
    }
    strncpy(second, print2, sizeof(second) - 1);
    second[sizeof(second) - 1] = '\0';
    report("fingerprint-deterministic", strcmp(first, second) == 0);

    return failures == 0 ? 0 : 1;
}
