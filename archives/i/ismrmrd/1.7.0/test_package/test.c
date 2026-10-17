/**
 * ismrmrd 1.7.0 consumer test (test_package).
 *
 * Simulates a downstream application using ONLY the public installed headers
 * and the linked library: builds an ISMRMRD acquisition, exercises the
 * public C API (flags, channel masks, allocation) and verifies observable
 * results. This is not part of the upstream test suite.
 */
#include <stdio.h>
#include <string.h>
#include "ismrmrd/ismrmrd.h"

int main(void) {
    int rc = 0;

    /* --- Exercise public C API: flags --- */
    uint64_t flags = 0;
    if (ismrmrd_set_flag(&flags, 1u) != 0) { fprintf(stderr, "set_flag failed\n"); return 1; }
    if (!ismrmrd_is_flag_set(flags, 1u))    { fprintf(stderr, "is_flag_set check 1 failed\n"); return 1; }
    if (ismrmrd_set_flags(&flags, 2u) != 0) { fprintf(stderr, "set_flags failed\n"); return 1; }
    if (!ismrmrd_is_flag_set(flags, 2u))    { fprintf(stderr, "is_flag_set check 2 failed\n"); return 1; }
    if (ismrmrd_clear_flag(&flags, 1u) != 0){ fprintf(stderr, "clear_flag failed\n"); return 1; }
    if (ismrmrd_is_flag_set(flags, 1u))     { fprintf(stderr, "clear_flag not honoured\n"); return 1; }

    /* --- Exercise public C API: channel masks --- */
    uint64_t mask[ISMRMRD_CHANNEL_MASKS];
    if (ismrmrd_set_all_channels_off(mask) != 0) { fprintf(stderr, "set_all_channels_off failed\n"); return 1; }
    if (ismrmrd_set_channel_on(mask, 3) != 0)    { fprintf(stderr, "set_channel_on failed\n"); return 1; }
    if (!ismrmrd_is_channel_on(mask, 3))         { fprintf(stderr, "is_channel_on(3) failed\n"); return 1; }
    if (ismrmrd_is_channel_on(mask, 4))          { fprintf(stderr, "is_channel_on(4) should be false\n"); return 1; }

    /* --- Exercise public C API: acquisition lifecycle --- */
    ISMRMRD_Acquisition *acq = ismrmrd_create_acquisition();
    if (!acq) { fprintf(stderr, "create_acquisition failed\n"); return 1; }
    if (ismrmrd_init_acquisition(acq) != 0) { fprintf(stderr, "init_acquisition failed\n"); return 1; }
    acq->head.number_of_samples = 128;
    acq->head.active_channels   = 4;
    acq->head.trajectory_dimensions = 3;
    acq->head.center_sample = 64;
    acq->head.measurement_uid = 42;

    /* round-trip the serialized acquisition header size */
    ISMRMRD_AcquisitionHeader copy;
    memcpy(&copy, &acq->head, sizeof(copy));
    if (copy.number_of_samples != 128 || copy.active_channels != 4) {
        fprintf(stderr, "acquisition header copy mismatch\n");
        rc = 1;
    }

    /* NDArray sanity via public init entry */
    ISMRMRD_NDArray *arr = ismrmrd_create_ndarray();
    if (!arr) { fprintf(stderr, "create_ndarray failed\n"); return 1; }
    arr->ndim = 2;
    arr->dims[0] = 8;
    arr->dims[1] = 16;
    arr->data_type = ISMRMRD_CXFLOAT;
    if (arr->ndim != 2 || arr->dims[1] != 16) {
        fprintf(stderr, "ndarray fields mismatch\n");
        rc = 1;
    }
    if (ismrmrd_free_ndarray(arr) != 0) { fprintf(stderr, "free_ndarray failed\n"); return 1; }
    if (ismrmrd_free_acquisition(acq) != 0) { fprintf(stderr, "free_acquisition failed\n"); return 1; }

    if (rc == 0) {
        printf("ismrmrd consumer test PASSED (flags/channels/acquisition/ndarray OK)\n");
    }
    return rc;
}