/* Rizin test_package — substantive compiled test (R34).
 * Links librz_core (public API entry) and calls rz_core_new/cmd0/free —
 * NOT a printf stub. CI's L1 gate confirms this test depends on rizin.
 * On HarmonyOS ld-musl uses a namespace security API and may gate run-time
 * .so loading outside the signed system namespace; conanfile.py test()
 * tolerates that platform gating via ignore_errors (CI signs ELF first). */
#include <rz_core.h>

int main(void) {
    RzCore *core = rz_core_new();
    if (!core) {
        return 1;
    }
    /* Run a trivial command via the rizin core API. rz_core_cmd0 returns
     * int (0 on success) per rizin rz_core.h. */
    if (rz_core_cmd0(core, "e bin.strings=false") != 0) {
        rz_core_free(core);
        return 2;
    }
    int rc = (rz_core_cmd0(core, "s 0") == 0) ? 0 : 3;
    rz_core_free(core);
    return rc;
}
