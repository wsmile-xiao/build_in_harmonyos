# mbrola-hu1

Hungarian female diphone voice data for the MBROLA speech synthesizer.

The database is installed at:

`share/mbrola/hu1/hu1`

With Conan build or run environments enabled, `MBROLA_VOICE_HU1` points to
that file and `MBROLA_HU1_EXAMPLES` points to the packaged PHO examples.

This package contains voice data only. A separately packaged MBROLA engine is
required to synthesize audio. The upstream example is:

```text
mbrola "$MBROLA_VOICE_HU1" "$MBROLA_HU1_EXAMPLES/kisk1.pho" kisk1.wav
```

HU1 uses a non-free custom license. Read the installed
`licenses/license.txt` before use or redistribution.
