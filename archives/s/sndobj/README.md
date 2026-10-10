# SndObj

SndObj is a C++ sound-synthesis and signal-processing library. This Conan recipe packages the 2.6.7 portable core for HarmonyOS PC arm64, including upstream's bundled FFTW 2 implementation.

The recipe defines `NO_RTIO`: realtime audio device backends, Python/Java wrappers, and hardware-driven examples are outside this package's verified scope. The installed `HarmTable`/`Oscili` consumer runs on the target device.

Upstream: https://sndobj.sourceforge.net/sndobj.html
