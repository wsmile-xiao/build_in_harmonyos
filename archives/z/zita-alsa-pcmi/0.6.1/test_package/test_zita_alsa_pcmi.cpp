// test_zita_alsa_pcmi.cpp — consumer-side test for zita-alsa-pcmi 0.6.1.
//
// R34: must really exercise the packaged library API, not just print text.
//  - zita_alsa_pcmi_major_version() / zita_alsa_pcmi_minor_version() are
//    checked against the header's version macros.
//  - An Alsa_pcmi object is constructed against (unavailable) ALSA devices;
//    the constructor must degrade gracefully to STATE_FAIL instead of
//    crashing, and the accessors must remain usable.
#include <zita-alsa-pcmi.h>
#include <cstdio>

int main()
{
    int major = zita_alsa_pcmi_major_version();
    int minor = zita_alsa_pcmi_minor_version();

    if (major != ZITA_ALSA_PCMI_MAJOR_VERSION || minor != ZITA_ALSA_PCMI_MINOR_VERSION)
    {
        std::fprintf(stderr, "zita-alsa-pcmi version mismatch: %d.%d != %d.%d\n",
                     major, minor, ZITA_ALSA_PCMI_MAJOR_VERSION, ZITA_ALSA_PCMI_MINOR_VERSION);
        return 1;
    }

    Alsa_pcmi pcm("default", "default", "default", 48000, 256, 4, 0);

    int st = pcm.state();
    if (st != Alsa_pcmi::STATE_OPEN && st != Alsa_pcmi::STATE_FAIL)
    {
        std::fprintf(stderr, "zita-alsa-pcmi unexpected state: %d\n", st);
        return 2;
    }

    // Extra accessor sanity: sample rate / frame size must echo the
    // constructor arguments even when no device could be opened.
    if (pcm.fsamp() != 48000 || pcm.fsize() != 256 || pcm.nfrag() != 4)
    {
        std::fprintf(stderr, "zita-alsa-pcmi accessor mismatch: %d %d %d\n",
                     pcm.fsamp(), pcm.fsize(), pcm.nfrag());
        return 3;
    }

    std::printf("zita-alsa-pcmi %d.%d OK (state=%d)\n", major, minor, st);
    return 0;
}
