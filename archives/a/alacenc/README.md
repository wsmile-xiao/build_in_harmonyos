# alacenc

alacenc is a command-line encoder for Apple Lossless Audio Codec (ALAC)
files. It reads PCM WAV input and writes ALAC/M4A output.

This package builds the upstream `v0.4.1` CMake project as a HarmonyOS PC
application. The upstream tarball vendors the ALAC codec sources and docopt.cpp,
so no external Conan dependencies are required.

## Conan

```bash
alacenc input.wav output.m4a
```

The package exposes the executable through the Conan run environment. Consumers
that need to execute it in tests should use `VirtualRunEnv`.

## References

- https://github.com/flacon/alacenc
