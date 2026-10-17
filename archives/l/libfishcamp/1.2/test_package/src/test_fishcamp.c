/* End-to-end consumer test for libfishcamp on HarmonyOS.
 *
 * This is a realistic downstream-consumer program (mirroring how the INDI
 * driver uses the library): it drives a *complete* capture session through the
 * real public API and verifies the *produced outputs* (camera enumeration,
 * camera identity, device info, and per-command return codes), rather than
 * merely asserting that functions are callable.
 *
 * Consumer workflow exercised (simulation mode, no hardware required):
 *   init -> enable simulation -> enumerate -> open camera -> read device info
 *        -> configure exposure (integration time / ROI / bin) -> start exposure
 *        -> poll state -> read frame -> close camera -> close library
 *
 * Simulation mode is used because OpenHarmony has no Fishcamp CCD hardware;
 * the library's simulation path is a first-class, supported mode that still
 * runs the real control flow and returns real, verifiable state. Linking the
 * binary also proves libfishcamp pulls in libusb correctly via Conan.
 */
#include <stdio.h>
#include <string.h>
#include "fishcamp.h"

/* Never rely on <cassert>: OHOS Release builds strip assert via -DNDEBUG.
   Use a custom CHECK macro that accumulates failures and reports all of them. */
static int g_fail = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        if (cond) {                                                   \
            printf("PASS: %s\n", (msg));                              \
        } else {                                                      \
            printf("CHECK FAILED: %s\n", (msg));                      \
            g_fail++;                                                 \
        }                                                             \
    } while (0)

/* Complete capture workflow as a downstream consumer would run it. */
static void consumer_capture_workflow(void) {
    printf("--- Consumer end-to-end capture workflow (simulation) ---\n");

    /* 初始化 + 构造输入：enable simulation so the library presents one
       virtual Starfish camera and runs its real control flow without USB. */
    fcUsb_init();
    fcUsb_setSimulation(1);
    fcUsb_setLogging(0);

    /* 真实执行：discover cameras. Simulation returns exactly 1 virtual camera. */
    int found = fcUsb_FindCameras();
    CHECK(found == 1, "FindCameras (simulation) discovers exactly 1 virtual camera");

    int num = fcUsb_GetNumCameras();
    CHECK(num == 1, "GetNumCameras reports 1 after simulation discovery");

    /* Open the camera (simulation path sets default registers, no USB I/O). */
    int rc = fcUsb_OpenCamera(1);
    CHECK(rc == 0, "OpenCamera(1) succeeds in simulation mode");

    /* 产出结果 -> 校验内容：camera identity from the discovery database. */
    int vendor  = fcUsb_GetCameraVendorID(1);
    int product = fcUsb_GetCameraProductID(1);
    int serial  = fcUsb_GetCameraSerialNum(1);
    CHECK(vendor  == 0x1887, "camera vendor ID matches Fishcamp 0x1887");
    CHECK(product == 0x0003, "camera product ID matches Starfish final 0x0003");
    CHECK(serial  == 12345,  "camera serial matches simulation value 12345");

    /* Read device info: simulation mode fills a real fc_camInfo structure. */
    fc_camInfo info;
    memset(&info, 0, sizeof(info));
    rc = fcUsb_cmd_getinfo(1, &info);
    CHECK(rc == 0, "getinfo returns 0");
    CHECK(info.width  == 1280, "getinfo width == 1280");
    CHECK(info.height == 1024, "getinfo height == 1024");
    CHECK(strcmp((const char *)info.camNameStr, "Starfish Mono") == 0,
          "getinfo camera name == \"Starfish Mono\"");
    CHECK(info.camSerialStr[0] != '\0', "getinfo serial string is populated");
    printf("    device info: %ux%u \"%s\" sn=%s\n",
           (unsigned)info.width, (unsigned)info.height,
           (const char *)info.camNameStr, (const char *)info.camSerialStr);

    /* Configure a real exposure (simulation path is a no-op returning 0). */
    rc = fcUsb_cmd_setIntegrationTime(1, 1000);
    CHECK(rc == 0, "setIntegrationTime(1000ms) returns 0");
    rc = fcUsb_cmd_setRoi(1, 0, 0, 100, 100);
    CHECK(rc == 0, "setRoi(0,0,100,100) returns 0");
    rc = fcUsb_cmd_setBin(1, 1);
    CHECK(rc == 0, "setBin(1) returns 0");

    /* Start exposure and poll state (simulation returns immediately). */
    rc = fcUsb_cmd_startExposure(1);
    CHECK(rc == 0, "startExposure returns 0");
    unsigned state = fcUsb_cmd_getState(1);
    CHECK(state == 0, "getState returns 0 in simulation mode");

    /* Read a frame buffer (simulation returns 0, buffer untouched). */
    UInt16 frame[64 * 64];
    memset(frame, 0, sizeof(frame));
    rc = fcUsb_cmd_getRawFrame(1, 64, 64, frame);
    CHECK(rc == 0, "getRawFrame returns 0");

    rc = fcUsb_CloseCamera(1);
    CHECK(rc == 0, "CloseCamera(1) returns 0");

    fcUsb_close();
    printf("Consumer capture workflow completed and verified.\n");
}

int main(void) {
    printf("libfishcamp consumer test starting\n");

    consumer_capture_workflow();

    if (g_fail == 0) {
        printf("libfishcamp consumer test: all checks passed (1 end-to-end consumer scenario)\n");
        return 0;
    }
    printf("libfishcamp consumer test: %d CHECK(S) FAILED\n", g_fail);
    return 1;
}
