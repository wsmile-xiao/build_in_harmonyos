/* Consumer smoke test for lib60870 2.4.0 (HarmonyOS PC / aarch64).
 *
 * Exercises the packaged library through its public API, mirroring the
 * upstream unit-test usage patterns (tests/all_tests.c):
 *   1. library version info (must be exactly 2.4.0)
 *   2. CS101_ASDU population with SinglePointInformation + element query
 *   3. CP56Time2a timestamp creation from the HAL clock
 *   4. CS104 slave create/configure/destroy cycle
 *   5. StepPositionInformation get/set roundtrip
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "iec60870_common.h"
#include "cs101_information_objects.h"
#include "cs104_slave.h"
#include "hal_time.h"

int main(void)
{
    /* 1) library version must be exactly 2.4.0 */
    Lib60870VersionInfo version = Lib60870_getLibraryVersionInfo();
    if (version.major != 2 || version.minor != 4 || version.patch != 0) {
        fprintf(stderr, "unexpected lib60870 version: %d.%d.%d\n",
                version.major, version.minor, version.patch);
        return 1;
    }

    /* 2) CS101 ASDU population + element query (upstream usage pattern) */
    struct sCS101_AppLayerParameters alParamsInst = {
        .sizeOfTypeId = 1,
        .sizeOfVSQ = 1,
        .sizeOfCOT = 2,
        .originatorAddress = 0,
        .sizeOfCA = 2,
        .sizeOfIOA = 3,
        .maxSizeOfASDU = 249,
    };
    CS101_AppLayerParameters alParams = &alParamsInst;

    SinglePointInformation spi1 =
        SinglePointInformation_create(NULL, 101, true, IEC60870_QUALITY_INVALID);
    SinglePointInformation spi2 =
        SinglePointInformation_create(NULL, 102, false, IEC60870_QUALITY_BLOCKED);

    if (spi1 == NULL || spi2 == NULL) {
        fprintf(stderr, "SinglePointInformation_create failed\n");
        return 1;
    }

    CS101_ASDU asdu =
        CS101_ASDU_create(alParams, false, CS101_COT_PERIODIC, 0, 1, false, false);
    if (asdu == NULL) {
        fprintf(stderr, "CS101_ASDU_create failed\n");
        return 1;
    }

    if (!CS101_ASDU_addInformationObject(asdu, (InformationObject)spi1) ||
        !CS101_ASDU_addInformationObject(asdu, (InformationObject)spi2)) {
        fprintf(stderr, "CS101_ASDU_addInformationObject failed\n");
        return 1;
    }

    SinglePointInformation_destroy(spi1);
    SinglePointInformation_destroy(spi2);

    if (CS101_ASDU_getTypeID(asdu) != M_SP_NA_1) {
        fprintf(stderr, "unexpected ASDU type: %d\n", CS101_ASDU_getTypeID(asdu));
        return 1;
    }
    if (CS101_ASDU_getNumberOfElements(asdu) != 2) {
        fprintf(stderr, "unexpected element count: %d\n",
                CS101_ASDU_getNumberOfElements(asdu));
        return 1;
    }
    if (CS101_ASDU_getCOT(asdu) != CS101_COT_PERIODIC) {
        fprintf(stderr, "unexpected COT\n");
        return 1;
    }

    SinglePointInformation dec = (SinglePointInformation)CS101_ASDU_getElement(asdu, 1);
    if (dec == NULL) {
        fprintf(stderr, "CS101_ASDU_getElement failed\n");
        return 1;
    }
    if (InformationObject_getObjectAddress((InformationObject)dec) != 102 ||
        SinglePointInformation_getValue(dec) != false ||
        SinglePointInformation_getQuality(dec) != IEC60870_QUALITY_BLOCKED) {
        fprintf(stderr, "decoded single-point values mismatch\n");
        return 1;
    }
    SinglePointInformation_destroy(dec);
    CS101_ASDU_destroy(asdu);

    /* 3) CP56Time2a timestamp from the HAL clock (year is encoded as
     * year - 2000 per IEC 60870-5-7, so 26 == 2026) */
    struct sCP56Time2a ts;
    CP56Time2a_createFromMsTimestamp(&ts, Hal_getTimeInMs());
    if (CP56Time2a_getYear(&ts) < 20 || CP56Time2a_getYear(&ts) > 200) {
        fprintf(stderr, "unexpected CP56Time2a year: %d\n", CP56Time2a_getYear(&ts));
        return 1;
    }

    /* 4) CS104 slave create/configure/destroy cycle (no sockets involved) */
    CS104_Slave slave = CS104_Slave_create(100, 100);
    if (slave == NULL) {
        fprintf(stderr, "CS104_Slave_create failed\n");
        return 1;
    }
    CS104_Slave_setServerMode(slave, CS104_MODE_SINGLE_REDUNDANCY_GROUP);

    CS104_APCIParameters apciParams = CS104_Slave_getConnectionParameters(slave);
    if (apciParams == NULL || apciParams->k != 12 || apciParams->w != 8) {
        fprintf(stderr, "unexpected default APCI parameters\n");
        return 1;
    }
    CS104_Slave_destroy(slave);

    /* 5) StepPositionInformation get/set roundtrip */
    StepPositionInformation step =
        StepPositionInformation_create(NULL, 201, 42, false, IEC60870_QUALITY_GOOD);
    if (step == NULL || StepPositionInformation_getValue(step) != 42) {
        fprintf(stderr, "StepPositionInformation roundtrip failed\n");
        return 1;
    }
    if (InformationObject_getObjectAddress((InformationObject)step) != 201) {
        fprintf(stderr, "StepPositionInformation object address mismatch\n");
        return 1;
    }
    StepPositionInformation_destroy(step);

    printf("lib60870 consumer test: PASS "
           "(version %d.%d.%d, ASDU population, CP56Time2a, CS104 slave cycle, step position)\n",
           version.major, version.minor, version.patch);
    return 0;
}
