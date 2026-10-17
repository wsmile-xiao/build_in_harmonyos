///////////////////////////////////////////////////////////////////////////////////
// test_serialdv.cpp — consumer regression test for the serialdv Conan package.
//
// Upstream ships no automated test suite: the v1.1.5 tarball has no tests/
// directory and CMakeLists.txt registers no enable_testing()/add_test() target;
// the only test-like artifact is the dvtest utility, which needs an AMBE3000
// (DVSI ThumbDV) dongle or an AMBE-over-UDP server (hardware absent in CI).
//
// This test links against the packaged libserialdv.so and verifies the public
// contract that is exercisable without DV hardware:
//   * protocol constants and the full MBE frame-size/bits rate matrix;
//   * controller lifecycle contracts (a closed controller refuses encode/decode);
//   * input validation and error paths of the serial/UDP/dummy controllers.
//
// Every CHECK is a real assertion; the program exits non-zero on any failure.
///////////////////////////////////////////////////////////////////////////////////
#include <cstdio>

#include <serialdv/datacontroller.h>
#include <serialdv/dummydatacontroller.h>
#include <serialdv/dvcontroller.h>
#include <serialdv/udpdatacontroller.h>

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        ++g_checks;                                                          \
        if (!(cond)) {                                                       \
            ++g_failures;                                                    \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__,     \
                         #cond);                                             \
        }                                                                    \
    } while (0)

int main()
{
    using namespace SerialDV;

    // ---- protocol constants (dvcontroller.h) ----
    CHECK(MBE_AUDIO_BLOCK_SIZE == 160U);
    CHECK(MBE_AUDIO_BLOCK_BYTES == 320U);
    CHECK(MBE_FRAME_MAX_LENGTH_BYTES == 18U);
    CHECK(DV3000_START_BYTE == 0x61U);
    CHECK(DV3000_TYPE_CONTROL == 0x00U);
    CHECK(DV3000_TYPE_AMBE == 0x01U);
    CHECK(DV3000_TYPE_AUDIO == 0x02U);
    CHECK(DV3000_CONTROL_PRODID == 0x30U);
    CHECK(DV3000_CONTROL_RATEP == 0x0AU);
    CHECK(DV3000_CONTROL_GAIN == 0x4BU);
    CHECK(DV3000_HEADER_LEN == 4U);
    CHECK(DV3000_REQ_PRODID_LEN == 5U);
    CHECK(DV3000_REQ_RATEP_LEN == 17U);
    CHECK(DV3000_REQ_GAIN_LEN == 5U);
    CHECK(DV3000_AUDIO_HEADER_LEN == 6U);
    CHECK(DV3000_AMBE_HEADER_LEN == 6U);

    // ---- MBE frame size table (getNbMbeBytes) ----
    CHECK(DVController::getNbMbeBytes(DVRateNone) == 0);
    CHECK(DVController::getNbMbeBytes(DVRate3600x2400) == 9);
    CHECK(DVController::getNbMbeBytes(DVRate3600x2450) == 9);
    CHECK(DVController::getNbMbeBytes(DVRate7200x4400) == 18);
    CHECK(DVController::getNbMbeBytes(DVRate7100x4400) == 0); // not in upstream table
    CHECK(DVController::getNbMbeBytes(DVRate2400) == 0);      // not in upstream table
    CHECK(DVController::getNbMbeBytes(DVRate2450) == 7);
    CHECK(DVController::getNbMbeBytes(DVRate4400) == 11);
    CHECK(DVController::getNbMbeBytes(DVRate2200) == 6);
    CHECK(DVController::getNbMbeBytes(DVRate3000) == 8);
    CHECK(DVController::getNbMbeBytes(DVRate6400) == 16);
    CHECK(DVController::getNbMbeBytes(DVRate7200) == 18);
    CHECK(DVController::getNbMbeBytes(DVRate8000) == 20);
    CHECK(DVController::getNbMbeBytes(DVRate9600) == 24);

    // ---- MBE frame size table (getNbMbeBits) ----
    CHECK(DVController::getNbMbeBits(DVRateNone) == 0);
    CHECK(DVController::getNbMbeBits(DVRate3600x2400) == 72);
    CHECK(DVController::getNbMbeBits(DVRate3600x2450) == 72);
    CHECK(DVController::getNbMbeBits(DVRate7200x4400) == 144);
    CHECK(DVController::getNbMbeBits(DVRate7100x4400) == 0); // not in upstream table
    CHECK(DVController::getNbMbeBits(DVRate2400) == 0);      // not in upstream table
    CHECK(DVController::getNbMbeBits(DVRate2450) == 49);
    CHECK(DVController::getNbMbeBits(DVRate4400) == 88);
    CHECK(DVController::getNbMbeBits(DVRate2200) == 44);
    CHECK(DVController::getNbMbeBits(DVRate3000) == 60);
    CHECK(DVController::getNbMbeBits(DVRate6400) == 128);
    CHECK(DVController::getNbMbeBits(DVRate7200) == 144);
    CHECK(DVController::getNbMbeBits(DVRate8000) == 160);
    CHECK(DVController::getNbMbeBits(DVRate9600) == 192);

    // ---- controller lifecycle: closed controller refuses codec calls ----
    short audio[MBE_AUDIO_BLOCK_SIZE];
    unsigned char mbe[MBE_FRAME_MAX_LENGTH_BYTES];
    for (unsigned int i = 0; i < MBE_AUDIO_BLOCK_SIZE; ++i) {
        audio[i] = 0;
    }
    for (unsigned int i = 0; i < MBE_FRAME_MAX_LENGTH_BYTES; ++i) {
        mbe[i] = 0;
    }

    DVController dv;
    CHECK(dv.isOpen() == false);
    CHECK(dv.encode(audio, mbe, DVRate3600x2400) == false);
    CHECK(dv.decode(audio, mbe, DVRate3600x2400) == false);

    // ---- serial controller: a non-TTY path must be rejected, not crash ----
    CHECK(dv.open("/dev/null") == false);
    DVController dvNoDev;
    CHECK(dvNoDev.open("/nonexistent/serialdv/test-device") == false);
    CHECK(dvNoDev.isOpen() == false);

    // ---- UDP controller: non-local peer without server -> open fails ----
    DVController dvUdp;
    CHECK(dvUdp.open("203.0.113.1:45678") == false);
    CHECK(dvUdp.isOpen() == false);

    // ---- DummyDataController API contract ----
    DummyDataController dummy;
    CHECK(dummy.open("/dev/whatever", SERIAL_460800) == false);
    unsigned char buf[8] = {0};
    CHECK(dummy.read(buf, sizeof(buf)) == 0);
    CHECK(dummy.write(buf, sizeof(buf)) == 0);
    CHECK(dummy.initResponse() == true);
    dummy.closeIt();
    CHECK(dummy.read(buf, sizeof(buf)) == 0);

    // ---- UDPDataController input validation ----
    UDPDataController udp;
    CHECK(udp.open("not-an-ip-port", SERIAL_460800) == false);
    CHECK(udp.open("192.0.2.1:99", SERIAL_460800) == false); // 4-5 digit port required

    std::printf("test_serialdv: %d/%d assertions passed\n", g_checks - g_failures,
                g_checks);
    return (g_failures == 0) ? 0 : 1;
}
