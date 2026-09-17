/*
 * test.cpp — soundtouch test_package smoke test.
 *
 * soundtouch is a library package (with a soundstretch CLI).  This test
 * links against libSoundTouch and exercises the real WSOLA DSP:
 *   1. getVersionId()  — returns SOUNDTOUCH_VERSION (20000 for 2.0.0)
 *   2. real DSP round-trip — push a synthetic sine through SoundTouch with
 *      tempo=1.0 (identity tempo) and verify the output sample count is
 *      nonzero and the pipeline completes without error.
 *
 * Build: linked by test_package/conanfile.py with -lSoundTouch.
 */
#include <soundtouch/SoundTouch.h>
#include <soundtouch/STTypes.h>
#include <cstdio>
#include <cstdlib>
#include <cmath>
int main(void) {
    // 1) library identity check
    int ver = soundtouch::SoundTouch::getVersionId();
    printf("SoundTouch version id: %d\n", ver);
    if (ver != 20000) {
        fprintf(stderr, "FAIL: expected version id 20000 (2.0.0), got %d\n", ver);
        return 1;
    }
    printf("PASS: getVersionId() == 20000 (2.0.0)\n");

    // 2) real WSOLA pipeline: sine through tempo 1.0 → samples flow out
    soundtouch::SoundTouch st;
    st.setSampleRate(44100);
    st.setChannels(1);
    st.setTempo(1.0);   // identity tempo — output length ≈ input length

    const int N = 44100;                    // 1 second
    soundtouch::SAMPLETYPE in[N];
    for (int i = 0; i < N; i++) {
        in[i] = (soundtouch::SAMPLETYPE)(0.6 * 32767.0 *
                std::sin(2.0 * M_PI * 440.0 * i / 44100.0));
    }
    st.putSamples(in, N);
    st.flush();

    soundtouch::SAMPLETYPE out[65536];
    int total = 0;
    int n;
    while ((n = st.receiveSamples(out, 65536)) > 0) {
        total += n;
    }
    printf("WSOLA round-trip: pushed %d samples, received %d samples\n",
           N, total);
    if (total < N / 2 || total > N * 2) {
        fprintf(stderr, "FAIL: unexpected output length %d for tempo=1.0\n",
                total);
        return 1;
    }
    printf("PASS: WSOLA pipeline produced %d samples at tempo 1.0\n", total);
    return 0;
}
