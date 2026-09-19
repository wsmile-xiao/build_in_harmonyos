/*
 * libopencsd test_package L1 consumer test.
 *
 * Links against the packaged libopencsd (C API) and verifies:
 *  1. ocsd_get_version_str() == "1.5.5";
 *  2. ocsd_get_version() == OCSD_VER_NUM (0x010505);
 *  3. a CoreSight decoder tree handle can be created and destroyed
 *     (exercises real library initialisation paths).
 */
#include <opencsd/c_api/opencsd_c_api.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fail(const char *what)
{
    fprintf(stderr, "FAIL: %s\n", what);
    return 1;
}

int main(void)
{
    const char *vstr = ocsd_get_version_str();
    if (!vstr || strcmp(vstr, "1.5.5") != 0) {
        fprintf(stderr, "FAIL: version string got '%s', want '1.5.5'\n",
                vstr ? vstr : "(null)");
        return 1;
    }

    uint32_t vnum = ocsd_get_version();
    if (vnum != OCSD_VER_NUM) {
        fprintf(stderr, "FAIL: version num got 0x%06x, want 0x%06x\n",
                vnum, (unsigned)OCSD_VER_NUM);
        return 1;
    }

    dcd_tree_handle_t tree =
        ocsd_create_dcd_tree(OCSD_TRC_SRC_FRAME_FORMATTED,
                             OCSD_DFRMTR_FRAME_MEM_ALIGN);
    if (tree == 0) {
        return fail("ocsd_create_dcd_tree returned NULL");
    }
    ocsd_destroy_dcd_tree(tree);

    printf("PASS: consumer OK (version=%s, num=0x%06x, dcd_tree create/destroy)\n",
           vstr, vnum);
    return 0;
}
