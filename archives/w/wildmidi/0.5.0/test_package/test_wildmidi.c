/* test_wildmidi.c — Conan L1 test for wildmidi 0.5.0
 *
 * Exercises the public library API end-to-end without any external data
 * files, using the built-in OPL3 FM synthesizer (config "@opl3"):
 *   1. version string / numeric version checks
 *   2. WildMidi_Init with the embedded OPL3 bank
 *   3. WildMidi_OpenBuffer on a minimal generated MIDI file
 *   4. WildMidi_GetOutput synthesis of PCM samples
 *   5. WildMidi_Close / WildMidi_Shutdown teardown
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wildmidi_lib.h>

/* Build a minimal Type-0 MIDI file in memory:
 * - one track, 4/4 @ 120bpm (500000 us/qn), a C4 note on/off pair,
 * - end-of-track meta event. Bytes are complete (no running status).
 * Layout: MThd(14) + MTrk(8) + track payload(19) = 41 bytes. */
static unsigned char midi_file[] = {
    'M', 'T', 'h', 'd', 0, 0, 0, 6, 0, 0, 0, 1, 0, 96,      /* header */
    'M', 'T', 'r', 'k', 0, 0, 0, 19,                          /* track hdr, len */
    0x00, 0xFF, 0x51, 0x03, 0x07, 0xA1, 0x20,                /* tempo 500000 */
    0x00, 0x90, 0x3C, 0x64,                                  /* note on C4 */
    0x60, 0x80, 0x3C, 0x64,                                  /* note off C4 */
    0x00, 0xFF, 0x2F, 0x00                                   /* end of track */
};

int main(void) {
    int rc = 1;
    midi *song = NULL;
    struct _WM_Info *info = NULL;
    int8_t pcm[16384];
    long ver;
    const char *vstr;

    /* 1. version string */
    vstr = WildMidi_GetString(WM_GS_VERSION);
    if (!vstr || strstr(vstr, "WildMidi") == NULL) {
        fprintf(stderr, "FAIL: version string: %s\n", vstr ? vstr : "()");
        goto cleanup;
    }
    printf("OK: version string = %s\n", vstr);

    /* 2. numeric version: 0x000500 (0.5.0) */
    ver = WildMidi_GetVersion();
    if (ver != 0x000500L) {
        fprintf(stderr, "FAIL: version 0x%06lx != 0x000500\n", ver);
        goto cleanup;
    }
    printf("OK: numeric version = 0x%06lx\n", ver);

    /* 3. init with the built-in OPL3 FM synthesizer ("@opl3"), 44.1 kHz */
    if (WildMidi_Init("@opl3", 44100, WM_MO_LOG_VOLUME) != 0) {
        fprintf(stderr, "FAIL: WildMidi_Init(@opl3): %s\n", WildMidi_GetError());
        goto cleanup;
    }
    printf("OK: WildMidi_Init with built-in OPL3 bank\n");

    /* 4. master volume */
    if (WildMidi_MasterVolume(100) != 0) {
        fprintf(stderr, "FAIL: WildMidi_MasterVolume\n");
        goto cleanup;
    }

    /* 5. open the generated MIDI from memory */
    song = WildMidi_OpenBuffer(midi_file, sizeof(midi_file));
    if (!song) {
        fprintf(stderr, "FAIL: WildMidi_OpenBuffer: %s\n", WildMidi_GetError());
        goto cleanup;
    }
    printf("OK: WildMidi_OpenBuffer\n");

    info = WildMidi_GetInfo(song);
    if (!info) {
        fprintf(stderr, "FAIL: WildMidi_GetInfo\n");
        goto cleanup;
    }
    printf("OK: info: total_midi_time=%u ms, approx_total_samples=%u\n",
           info->total_midi_time, info->approx_total_samples);

    /* 6. synthesize PCM output */
    int got = WildMidi_GetOutput(song, pcm, sizeof(pcm));
    if (got <= 0) {
        fprintf(stderr, "FAIL: WildMidi_GetOutput returned %d\n", got);
        goto cleanup;
    }
    /* stereo 16-bit samples: at least one full period of audio */
    printf("OK: WildMidi_GetOutput produced %d bytes of PCM\n", got);

    rc = 0;

cleanup:
    if (song) WildMidi_Close(song);
    WildMidi_ClearError();
    WildMidi_Shutdown();
    if (rc == 0) printf("ALL CHECKS PASSED\n");
    return rc;
}
