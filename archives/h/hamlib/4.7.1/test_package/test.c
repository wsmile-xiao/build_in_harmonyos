#include <stdio.h>
#include <string.h>

#include <hamlib/rig.h>

/*
 * hamlib 4.7.1 consumer test (R34): exercises the packaged library API.
 * 1. library version string matches 4.7.1
 * 2. rig_list_foreach enumerates the compiled-in backend rig models (>100)
 * 3. dummy rig init/open/close/cleanup round-trip succeeds
 * 4. mode/str helpers work (rig_parse_mode / rig_strrmode round-trip)
 */
/* enumerate rig models via public API */
static int count_cb(const rig_model_t model, rig_ptr_t arg)
{
    (void)model;
    (*(int *)arg)++;
    return 1; /* continue */
}

int main(void)
{
    int ret = 1;

    rig_set_debug(RIG_DEBUG_NONE);
    if (strstr(hamlib_version, "4.7.1") == NULL) {
        fprintf(stderr, "FAIL: unexpected hamlib version: %s\n",
                hamlib_version);
        return ret;
    }
    printf("PASS: hamlib version = %s\n", hamlib_version);

    rig_set_debug(RIG_DEBUG_NONE);

    /* enumerate rig models */
    int count = 0;
    rig_load_all_backends();
    rig_list_foreach_model(count_cb, &count);
    if (count < 100) {
        fprintf(stderr, "FAIL: only %d rig models enumerated\n", count);
        return ret;
    }
    printf("PASS: %d rig models enumerated\n", count);

    /* dummy rig round trip */
    RIG *rigd = rig_init(RIG_MODEL_DUMMY);
    if (rigd == NULL) {
        fprintf(stderr, "FAIL: rig_init(RIG_MODEL_DUMMY)\n");
        return ret;
    }
    if (rig_open(rigd) != RIG_OK) {
        fprintf(stderr, "FAIL: rig_open: %s\n", rigerror(rigd->caps->status));
        rig_cleanup(rigd);
        return ret;
    }
    freq_t freq = 14250000;
    if (rig_set_freq(rigd, RIG_VFO_CURR, freq) != RIG_OK ||
        rig_get_freq(rigd, RIG_VFO_CURR, &freq) != RIG_OK ||
        freq != 14250000) {
        fprintf(stderr, "FAIL: dummy rig set/get freq\n");
        rig_close(rigd);
        rig_cleanup(rigd);
        return ret;
    }
    printf("PASS: dummy rig freq round-trip = %.0f Hz\n", (double)freq);
    rig_close(rigd);
    rig_cleanup(rigd);

    /* mode helpers */
    rmode_t m = rig_parse_mode("USB");
    if (m == RIG_MODE_NONE || strcmp(rig_strrmode(m), "USB") != 0) {
        fprintf(stderr, "FAIL: rig_parse_mode/rig_strrmode USB\n");
        return ret;
    }
    printf("PASS: mode helper round-trip USB\n");

    printf("test hamlib 4.7.1: all checks OK\n");
    return 0;
}
