#include <cmath>
#include <cstdio>
#include <cstring>

// soloud_wav.h declares FILE*-taking members without including <cstdio>
// (upstream relies on the .cpp TU having pulled it in first). Include it
// here before the soloud headers so the public headers parse standalone.
#include "soloud.h"
#include "soloud_sinewave.h"
#include "soloud_speech.h"
#include "soloud_wav.h"
#include "soloud_filter.h"

// Headless consumer test: drive SoLoud's pure-software mixing core directly
// via Soloud::init()/mix() (no audio back-end needed) and validate the mixed
// PCM output, handle-based channel control, and the speech synthesizer.
int main(void) {
    SoLoud::Soloud soloud;

    // Backend-less initialization: 2 channels, 44100 Hz, 2048-sample buffer.
    soloud.init(2, 44100, 2048, 0);

    // 1) Sine wave source: play and mix one buffer.
    // (version_1_0 semantics: play() returns -1 on failure; channel 0 with
    // mPlayIndex 0 yields handle 0 on the very first play — valid.)
    SoLoud::Sinewave sinewave;
    sinewave.mFreq = 441.0f;  // 44100/100 -> exact integer period
    int handle = soloud.play(sinewave);
    if (handle < 0) {
        fprintf(stderr, "play() returned failure handle %d\n", handle);
        return 1;
    }

    const int SAMPLES = 512;
    static float buffer[SAMPLES * 2];
    memset(buffer, 0, sizeof(buffer));
    soloud.mix(buffer, SAMPLES);

    // A live 441 Hz sine must produce non-silent, finite, bounded output.
    float peak = 0.0f;
    for (int i = 0; i < SAMPLES * 2; i++) {
        if (!std::isfinite(buffer[i])) {
            fprintf(stderr, "non-finite sample at %d\n", i);
            return 1;
        }
        float a = buffer[i] < 0 ? -buffer[i] : buffer[i];
        if (a > peak) peak = a;
    }
    if (peak < 0.05f) {
        fprintf(stderr, "mix produced near-silent output (peak=%.4f)\n", peak);
        return 1;
    }
    if (peak > 1.5f) {
        fprintf(stderr, "mix output out of range (peak=%.4f)\n", peak);
        return 1;
    }

    // 2) Channel control via handle: volume, pan, stream time.
    soloud.setVolume(handle, 0.5f);
    soloud.setPan(handle, -0.5f);
    float t1 = soloud.getStreamTime(handle);
    memset(buffer, 0, sizeof(buffer));
    soloud.mix(buffer, SAMPLES);
    float t2 = soloud.getStreamTime(handle);
    if (!(t2 > t1)) {
        fprintf(stderr, "stream time did not advance (%f -> %f)\n", t1, t2);
        return 1;
    }

    // 3) Speech synthesizer (Klatt TTS, pure C++ DSP, no back-end needed).
    // Stop the sine voice first so the speech measurement below captures the
    // Speech source alone (not a sine+speech mix — the sine keeps playing
    // until stopAll otherwise, which would make the assertion vacuous).
    soloud.stop(handle);
    SoLoud::Speech speech;
    char text[] = "Hello HarmonyOS";  // upstream setText takes char* (non-const)
    speech.setText(text);
    int shandle = soloud.play(speech);
    if (shandle < 0) {
        fprintf(stderr, "speech play() returned failure handle %d\n", shandle);
        return 1;
    }
    static float sbuf[SAMPLES * 2];
    memset(sbuf, 0, sizeof(sbuf));
    soloud.mix(sbuf, SAMPLES);
    float speak = 0.0f;
    for (int i = 0; i < SAMPLES * 2; i++) {
        float a = sbuf[i] < 0 ? -sbuf[i] : sbuf[i];
        if (a > speak) speak = a;
    }
    if (speak < 0.001f) {
        fprintf(stderr, "speech mix produced silence\n");
        return 1;
    }

    // 4) stopAll cleans up all voices (version_1_0 core has no deinit;
    //    the back-end owns shutdown — headless mode simply drops the object).
    soloud.stopAll();

    printf("soloud headless mix: PASS (sine peak=%.4f, speech peak=%.4f)\n",
           peak, speak);
    return 0;
}
