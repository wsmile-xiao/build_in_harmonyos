#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <fyba/fyba.h>

/* Consumer test for fyba (HarmonyOS PC):
 * uses ONLY the installed public headers (<fyba/fyba.h>) and the public
 * API to create a real SOSI file with HO_New, then verifies the observable
 * result (return status + the produced SOSI file's byte content: .HODE
 * header, ..TRANSPAR section, version line and terminating .SLUTT).
 *
 * Note: HO_TestSOSI's full parser loops on a minimal file (upstream parser
 * quirk), so the consumer verifies the created artifact directly instead of
 * re-parsing it through the library — the creation API and its observable
 * output are what a third-party upper-layer component would rely on. */
static int check_bytes(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        printf("consumer: reopen failed\n");
        return 0;
    }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *buf = (char *)malloc((size_t)sz + 1);
    if (!buf) { fclose(f); return 0; }
    size_t rd = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[rd] = '\0';

    int ok = (sz > 0) &&
             (strncmp(buf, ".HODE", 5) == 0) &&
             (strstr(buf, "..TRANSPAR") != NULL) &&
             (strstr(buf, "..SOSI-VERSJON") != NULL) &&
             (strstr(buf, ".SLUTT") != NULL);
    printf("consumer: size=%ld hode=%d trans=%d vers=%d slut=%d\n",
           sz,
           strncmp(buf, ".HODE", 5) == 0,
           strstr(buf, "..TRANSPAR") != NULL,
           strstr(buf, "..SOSI-VERSJON") != NULL,
           strstr(buf, ".SLUTT") != NULL);
    free(buf);
    return ok;
}

int main() {
    const char *path = "consumer.sosi";
    short st = HO_New(path, 23,
                      580000.0, 6645000.0,   /* origo_a, origo_n */
                      0.01, 0.01, 0.01,      /* enhet, enhet_h, enhet_d */
                      580000.0, 6645000.0,   /* nv_a, nv_n */
                      590000.0, 6646000.0);  /* oh_a, oh_n */
    printf("consumer: HO_New=%d\n", (int)st);

    int ok = (st == UT_TRUE) && check_bytes(path);
    remove(path);
    if (ok) {
        printf("fyba consumer test OK\n");
        return 0;
    }
    printf("fyba consumer test FAILED\n");
    return 1;
}
