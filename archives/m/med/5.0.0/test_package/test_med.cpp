/* End-to-end HarmonyOS consumer test for the MED C API (libmedC).
 *
 * Exercises the real packaged library through a full create -> write -> close ->
 * reopen(read-only) -> read-back -> verify cycle:
 *   1. create a MED file
 *   2. write a file comment
 *   3. create a 3D unstructured mesh "mesh0" and write 3 node coordinates
 *   4. close the file
 *   5. reopen it read-only, read the comment and the node coordinates back
 *   6. compare the read-back values against what was written
 *
 * A non-zero exit code means the round-trip failed (library/format/IO defect).
 *
 * On OHOS the binary is statically linked (libmedC.a + libhdf5.a + libaec.a +
 * libsz.a) so it runs natively: the non-HAP loader cannot dlopen user-path .so.
 */
#include <stdio.h>
#include <string.h>
#include <med.h>

#define CHK(expr, code)                                                   \
    do {                                                                  \
        if ((expr) < 0) {                                                 \
            fprintf(stderr, "FAIL: %s (line %d)\n", #expr, __LINE__);     \
            return (code);                                                \
        }                                                                 \
    } while (0)

static int nearly_equal(med_float a, med_float b)
{
    /* 0.0 and 1.0 are exactly representable; use a tiny epsilon for safety. */
    return (a > b ? a - b : b - a) < 1e-9;
}

int main(void)
{
    med_idt fid;
    med_int nnode = 3;
    med_int spacedim = 3, meshdim = 3;
    med_float coords[9] = {0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0};
    med_float rcoords[9];
    char des[256] = "openharmony med port end-to-end test";
    char rdes[256];
    const char *meshname = "mesh0";
    int i;

    /* 1-4: create + populate + close */
    fid = MEDfileOpen("test_med.med", MED_ACC_CREAT);
    CHK(fid, 1);
    CHK(MEDfileCommentWr(fid, des), 2);

    CHK(MEDmeshCr(fid, meshname, spacedim, meshdim, MED_UNSTRUCTURED_MESH,
                  "end-to-end mesh", "s", MED_SORT_DTIT, MED_CARTESIAN,
                  "x y z", "m m m"),
        3);
    CHK(MEDmeshNodeCoordinateWr(fid, meshname, MED_NO_DT, MED_NO_IT,
                                MED_UNDEF_DT, MED_FULL_INTERLACE, nnode,
                                coords),
        4);
    CHK(MEDfileClose(fid), 5);

    /* 5-6: reopen read-only and verify every written value */
    fid = MEDfileOpen("test_med.med", MED_ACC_RDONLY);
    CHK(fid, 6);
    CHK(MEDfileCommentRd(fid, rdes), 7);
    if (strcmp(des, rdes) != 0) {
        fprintf(stderr, "FAIL: comment mismatch ('%s' != '%s')\n", des, rdes);
        return 8;
    }
    CHK(MEDmeshNodeCoordinateRd(fid, meshname, MED_NO_DT, MED_NO_IT,
                                MED_FULL_INTERLACE, rcoords),
        9);
    for (i = 0; i < 9; i++) {
        if (!nearly_equal(coords[i], rcoords[i])) {
            fprintf(stderr, "FAIL: coord[%d] %g != %g\n", i, coords[i],
                    rcoords[i]);
            return 10;
        }
    }
    CHK(MEDfileClose(fid), 11);

    printf("OK: med end-to-end round-trip verified (comment + %d nodes)\n",
           (int)nnode);
    return 0;
}
