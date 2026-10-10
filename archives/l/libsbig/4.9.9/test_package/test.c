/* Consumer test for libsbig/4.9.9 on OHOS PC.
 *
 * The upstream libsbig ships as a prebuilt shared library blog plus the
 * sbigudrv.h API header (no C sources, no tests).  This test links against
 * the delivered libsbig and drives the *real* driver entry point
 * SBIGUnivDrvCommand() through three commands:
 *
 *   1. CC_OPEN_DRIVER       - initialise the driver (no params/results)
 *   2. CC_GET_DRIVER_INFO    - query driver identity (params + results structs)
 *   3. CC_CLOSE_DRIVER       - shut the driver down
 *
 * A SBIG camera is not required: on a hardware-less machine the driver simply
 * returns a PAR_ERROR code (e.g. CE_DRIVER_NOT_FOUND), which is recorded and
 * treated as a successful non-crash run.  The test fails only if the returned
 * code is not a recognised driver error, if a command is reported as unknown
 * (broken linkage/binding to the delivered library), or if a successful
 * GetDriverInfo does not actually fill its results struct (broken struct
 * params/results marshalling through the real ABI).
 */
#include <sbigudrv.h>

#include <stdio.h>
#include <string.h>

static int g_failures = 0;

static void check_ret(const char *what, short ret)
{
    if (ret == CE_UNKNOWN_COMMAND) {
        printf("FAIL: %s returned CE_UNKNOWN_COMMAND (wrong/broken library binding)\n",
               what);
        ++g_failures;
        return;
    }
    if (ret < CE_NO_ERROR || ret >= CE_NEXT_ERROR) {
        printf("FAIL: %s returned out-of-range code %hd\n", what, ret);
        ++g_failures;
        return;
    }
    printf("ok:   %s -> %hd\n", what, ret);
}

int main(void)
{
    short ret;

    /* 1. Open the driver.  No params/results are required for this command. */
    ret = SBIGUnivDrvCommand(CC_OPEN_DRIVER, NULL, NULL);
    printf("CC_OPEN_DRIVER returned %hd (no camera expected on this host)\n", ret);
    check_ret("CC_OPEN_DRIVER", ret);

    /* 2. Query driver info through params+results structs. */
    GetDriverInfoParams infoParams;
    GetDriverInfoResults0 infoResults;
    memset(&infoParams, 0, sizeof infoParams);
    memset(&infoResults, 0, sizeof infoResults);
    infoParams.request = DRIVER_STD;
    ret = SBIGUnivDrvCommand(CC_GET_DRIVER_INFO, &infoParams, &infoResults);
    printf("CC_GET_DRIVER_INFO returned %hd\n", ret);
    check_ret("CC_GET_DRIVER_INFO", ret);
    if (ret == CE_NO_ERROR) {
        /* CE_NO_ERROR means the driver is live and must have populated the
         * results struct - proves struct params/results marshalling works
         * through the real ABI. */
        if (infoResults.name[0] == '\0' || infoResults.version == 0) {
            printf("FAIL: GetDriverInfo returned CE_NO_ERROR but results not "
                   "filled (name='%s', version=0)\n", infoResults.name);
            ++g_failures;
        } else {
            printf("ok:   driver name='%s' version=0x%04x maxRequest=%u\n",
                   infoResults.name, (unsigned)infoResults.version,
                   (unsigned)infoResults.maxRequest);
        }
    } else {
        printf("note: no driver available on this host (ret=%hd) - "
               "GetDriverInfo results skipped\n", ret);
    }

    /* 3. Close the driver. */
    ret = SBIGUnivDrvCommand(CC_CLOSE_DRIVER, NULL, NULL);
    check_ret("CC_CLOSE_DRIVER", ret);

    if (g_failures == 0) {
        puts("libsbig consumer test: PASS");
        return 0;
    }
    printf("libsbig consumer test: FAIL (%d assertion(s))\n", g_failures);
    return 1;
}

