#include <stdio.h>
#include <unistd.h>

#include <hamlib/rig.h>
#include <hamlib/riglist.h>

int main(void)
{
    if (rig_load_all_backends() < 0) {
        fprintf(stderr, "rig_load_all_backends failed\n");
        return 1;
    }

    if (rig_get_caps(RIG_MODEL_DUMMY) == NULL) {
        fprintf(stderr, "dummy rig capabilities missing\n");
        return 2;
    }

    RIG *rig = rig_init(RIG_MODEL_DUMMY);
    if (rig == NULL) {
        fprintf(stderr, "rig_init(dummy) failed\n");
        return 3;
    }

    if (rig->caps->rig_model != RIG_MODEL_DUMMY) {
        fprintf(stderr, "unexpected rig model: %d\n", rig->caps->rig_model);
        rig_cleanup(rig);
        return 4;
    }

    if (rig_cleanup(rig) != RIG_OK) {
        fprintf(stderr, "rig_cleanup failed\n");
        return 5;
    }

    RIG *opened = rig_init(RIG_MODEL_DUMMY);
    if (opened == NULL || rig_open(opened) != RIG_OK) {
        fprintf(stderr, "rig_open(dummy) failed\n");
        if (opened != NULL) {
            rig_cleanup(opened);
        }
        return 6;
    }

    /* Allow the Morse worker to create its FIFO before exercising its queue. */
    usleep(100 * 1000);
    if (rig_set_mode(opened, RIG_VFO_CURR, RIG_MODE_CW, 0) != RIG_OK) {
        fprintf(stderr, "rig_set_mode(CW) failed\n");
        rig_close(opened);
        rig_cleanup(opened);
        return 7;
    }
    if (rig_send_morse(opened, RIG_VFO_CURR, "CQ") != RIG_OK) {
        fprintf(stderr, "rig_send_morse(dummy) failed\n");
        rig_close(opened);
        rig_cleanup(opened);
        return 8;
    }

    if (rig_close(opened) != RIG_OK) {
        fprintf(stderr, "rig_close(dummy) failed\n");
        rig_cleanup(opened);
        return 9;
    }

    if (rig_cleanup(opened) != RIG_OK) {
        fprintf(stderr, "rig_cleanup(opened dummy) failed\n");
        return 10;
    }

    puts("Hamlib API assertions: 10 passed");
    return 0;
}
