/*
 * midifile consumer test (C++) — HarmonyOS/OHOS aarch64.
 *
 * Real API roundtrip against the packaged static library:
 *  1. build a 2-track MIDI file in memory (tempo + 3 note events)
 *  2. write to a temp file (SMF binary), read it back
 *  3. assert track count, event counts, note pitch/ontime survive
 *  4. absolute ticks -> seconds conversion sanity via getFileTimeInTicks
 */
#include <cstdio>
#include <cstdlib>

#include "MidiFile.h"

using namespace smf;

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
    const char* tmp = "test_roundtrip.mid"; /* cwd: /tmp may be read-only on device */

    MidiFile out;
    out.absoluteTicks();
    out.addTrack(2);                      /* track 0 + track 1 */
    out.setTicksPerQuarterNote(480);

    /* tempo: 120 bpm = 500000 us per quarter */
    int tempo = 500000;
    std::vector<uchar> tmpev({0xFF, 0x51, 0x03,
                              (uchar)(tempo >> 16), (uchar)(tempo >> 8), (uchar)tempo});
    out.addEvent(0, 0, tmpev);

    /* 3 notes on track 1 */
    const int pitches[3] = {60, 64, 67};
    for (int i = 0; i < 3; i++) {
        out.addNoteOn(1, i * 480, 0, pitches[i], 100);
        out.addNoteOff(1, i * 480 + 240, 0, pitches[i], 0);
    }
    out.sortTracks();

    CHECK(out.write(tmp) != 0, "MidiFile::write succeeds");

    /* read back */
    MidiFile in;
    CHECK(in.read(tmp) != 0, "MidiFile::read succeeds");
    CHECK(in.getTrackCount() == 3, "track count survives roundtrip (default 1 + addTrack(2))");

    int noteons = 0;
    int first_pitch = -1;
    double first_ontime = -1.0;
    for (int t = 0; t < in.getTrackCount(); t++) {
        for (int e = 0; e < in[t].size(); e++) {
            const MidiEvent& ev = in[t][e];
            if (ev.isNoteOn()) {
                noteons++;
                if (first_pitch < 0) {
                    first_pitch = ev.getKeyNumber();
                    in.doTimeAnalysis();
                    first_ontime = ev.seconds;
                }
            }
        }
    }
    CHECK(noteons == 3, "3 note-ons survive roundtrip");
    CHECK(first_pitch == 60, "first note pitch == 60");
    CHECK(first_ontime == 0.0, "first note ontime == 0.0s (tempo applied)");

    std::remove(tmp);

    if (g_failures == 0) {
        printf("test_midifile: OK (SMF write/read roundtrip + time analysis)\n");
        return 0;
    }
    printf("test_midifile: FAILED (%d checks failed)\n", g_failures);
    return 1;
}
