#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <fyba/fyba.h>

/* HarmonyOS-specific test for fyba:
 * - LC_Cancel(): public API; on the LINUX/OHOS build it deterministically
 *   returns UT_FALSE (no Esc-abort support) — observable result.
 * - HO_New(): creates a real SOSI file through the public API on the OHOS
 *   runtime; the produced artifact is verified byte-wise (ISO8859-10
 *   tegnsett declaration, KOORDSYS value, OMRADE section and .SLUTT).
 * - LC_StartMessage/LC_ShowMessage/LC_EndMessage are no-ops under LINUX;
 *   calling them exercises the API surface without side effects. */
int main() {
    /* 1) public cancel-check API: deterministic observable result */
    short cancel = LC_Cancel();
    printf("ohos: LC_Cancel=%d (expect %d=UT_FALSE)\n", (int)cancel, (int)UT_FALSE);

    /* 2) message API surface (no-op under LINUX, safe to call) */
    LC_StartMessage("ohos.sosi");
    LC_ShowMessage(50.0);
    LC_EndMessage();

    /* 3) create a real SOSI file via public API and verify the artifact */
    const char *path = "ohos.sosi";
    short st = HO_New(path, 23,
                      580000.0, 6645000.0,   /* origo_a, origo_n */
                      0.01, 0.01, 0.01,      /* enhet, enhet_h, enhet_d */
                      580000.0, 6645000.0,   /* nv_a, nv_n */
                      590000.0, 6646000.0);  /* oh_a, oh_n */
    printf("ohos: HO_New=%d (expect %d=UT_TRUE)\n", (int)st, (int)UT_TRUE);

    FILE *f = fopen(path, "rb");
    if (!f) { printf("ohos: reopen failed\n"); return 1; }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *buf = (char *)malloc((size_t)sz + 1);
    if (!buf) { fclose(f); return 1; }
    size_t rd = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[rd] = '\0';

    int hode = strncmp(buf, ".HODE", 5) == 0;
    int tegn = strstr(buf, "..TEGNSETT ISO8859-10") != NULL;
    int koor = strstr(buf, "...KOORDSYS  23") != NULL;
    int omr  = strstr(buf, "..OMR") != NULL;      /* ..OMRADE (Latin-1) */
    int minn = strstr(buf, "...MIN-N") != NULL;
    int maxn = strstr(buf, "...MAX-N") != NULL;
    int slut = strstr(buf, ".SLUTT") != NULL;
    printf("ohos: size=%ld hode=%d tegnsett=%d koordsys=%d omrade=%d min=%d max=%d slut=%d\n",
           sz, hode, tegn, koor, omr, minn, maxn, slut);

    free(buf);
    remove(path);

    int ok = (cancel == UT_FALSE) &&
             (st == UT_TRUE) && hode && tegn && koor && omr && minn && maxn && slut;
    if (ok) {
        printf("fyba HarmonyOS test OK\n");
        return 0;
    }
    printf("fyba HarmonyOS test FAILED\n");
    return 1;
}
