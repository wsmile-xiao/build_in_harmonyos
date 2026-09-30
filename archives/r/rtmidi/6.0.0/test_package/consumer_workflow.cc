/*
 * End-to-end rtmidi consumer workflow for HarmonyOS/OHOS.
 *
 * OHOS exposes no native MIDI backend, so this application deliberately
 * selects the upstream dummy fallback. It still runs the lifecycle that a
 * MIDI producer/monitor consumer uses: discover an API, create input and
 * output sessions, configure virtual ports, submit a NoteOn/NoteOff pair,
 * and release both sessions. The dummy backend intentionally performs no
 * hardware I/O; a successful run proves the fallback remains linkable and
 * usable as a complete no-hardware application flow.
 */
#include <cstdio>
#include <vector>

#include "RtMidi.h"

int main()
{
    try {
        std::vector<RtMidi::Api> apis;
        RtMidi::getCompiledApi(apis);

        bool dummy_available = false;
        for (size_t i = 0; i < apis.size(); ++i) {
            if (apis[i] == RtMidi::RTMIDI_DUMMY) {
                dummy_available = true;
                break;
            }
        }
        if (!dummy_available) {
            std::fprintf(stderr, "workflow: RTMIDI_DUMMY is not compiled\n");
            return 1;
        }

        std::printf("workflow: discovered %s API\n",
                    RtMidi::getApiName(RtMidi::RTMIDI_DUMMY).c_str());
        RtMidiIn monitor(RtMidi::RTMIDI_DUMMY, "ohos-midi-monitor");
        RtMidiOut producer(RtMidi::RTMIDI_DUMMY, "ohos-midi-producer");

        monitor.ignoreTypes(false, false, false);
        monitor.openVirtualPort("ohos-midi-monitor");
        producer.openVirtualPort("ohos-midi-producer");

        std::vector<unsigned char> note_on = {0x90, 60, 100};
        std::vector<unsigned char> note_off = {0x80, 60, 0};
        producer.sendMessage(&note_on);
        producer.sendMessage(&note_off);

        producer.closePort();
        monitor.closePort();
        std::printf("workflow: dummy MIDI session completed\n");
        return 0;
    } catch (const RtMidiError& error) {
        error.printMessage();
        return 1;
    }
}
