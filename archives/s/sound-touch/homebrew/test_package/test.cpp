#include <cstdio>
#include <cstdlib>
#include <soundtouch/SoundTouch.h>

int main(void) {
    // Create a SoundTouch instance and verify basic API works
    soundtouch::SoundTouch st;

    // Set sample rate and channels
    st.setSampleRate(44100);
    st.setChannels(2);

    // Set tempo change
    st.setTempoChange(0.0f);

    // Verify version string is accessible
    const char *ver = st.getVersionString();
    printf("SoundTouch version: %s\n", ver);
    printf("test_soundtouch homebrew: OK\n");

    return 0;
}