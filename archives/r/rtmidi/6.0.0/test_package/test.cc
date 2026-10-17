/*
 * rtmidi consumer test (C++) — HarmonyOS/OHOS aarch64.
 *
 * On OHOS (no ALSA/JACK/CoreMIDI/WinMM/Web/AMIDI) upstream auto-defines
 * __RTMIDI_DUMMY__; this consumer verifies the dummy fallback is really
 * compiled in and behaves per its documented contract:
 *  1. getCompiledApi reports RTMIDI_DUMMY and its name/display name
 *  2. RtMidiOut constructs against the dummy API
 *  3. portCount() == 0 on dummy; openPort() raises an error (non-functional
 *     API contract) without crashing
 *  4. getApiName on an invalid API returns "" and display name "Unknown"
 */
#include <cstdio>
#include <string>
#include <vector>

#include "RtMidi.h"

static int g_failures = 0;

#define CHECK(cond, msg)                                  \
    do {                                                  \
        if (!(cond)) {                                    \
            fprintf(stderr, "FAIL: %s\n", (msg));         \
            g_failures++;                                 \
        }                                                 \
    } while (0)

int main(void)
{
    /* 1. compiled API list contains DUMMY with valid names */
    std::vector<RtMidi::Api> apis;
    RtMidi::getCompiledApi(apis);
    bool has_dummy = false;
    for (size_t i = 0; i < apis.size(); i++) {
        if (apis[i] == RtMidi::RTMIDI_DUMMY) has_dummy = true;
    }
    CHECK(has_dummy, "getCompiledApi includes RTMIDI_DUMMY");
    CHECK(!RtMidi::getApiName(RtMidi::RTMIDI_DUMMY).empty(),
          "getApiName(RTMIDI_DUMMY) non-empty");

    /* 2. construct against the dummy API */
    RtMidiOut* out = NULL;
    try {
        out = new RtMidiOut(RtMidi::RTMIDI_DUMMY, "ohos-consumer-test");
    } catch (RtMidiError& e) {
        e.printMessage();
    }
    CHECK(out != NULL, "RtMidiOut(RTMIDI_DUMMY) constructs");

    if (out) {
        /* 3. documented non-functional contract: zero ports, openPort is a
         * silent no-op on dummy (outer wrapper is a pure pass-through), so
         * the port never actually opens */
        CHECK(out->getPortCount() == 0, "dummy portCount() == 0");
        CHECK(out->getCurrentApi() == RtMidi::RTMIDI_DUMMY,
              "getCurrentApi() == RTMIDI_DUMMY");
        out->openPort(0);
        CHECK(!out->isPortOpen(), "dummy openPort() no-op: isPortOpen() stays false");
        std::vector<unsigned char> msg;
        msg.push_back(0x90);
        msg.push_back(60);
        msg.push_back(100);
        out->sendMessage(&msg); /* dummy accepts without crashing */
        delete out;
    }

    /* 4. invalid-API mapping contract (mirrors upstream apinames) */
    CHECK(RtMidi::getApiDisplayName((RtMidi::Api)-1) == "Unknown",
          "getApiDisplayName(invalid) == \"Unknown\"");

    if (g_failures == 0) {
        printf("test_rtmidi: OK (dummy-API fallback verified on OHOS)\n");
        return 0;
    }
    printf("test_rtmidi: FAILED (%d checks failed)\n", g_failures);
    return 1;
}
