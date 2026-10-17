# libconvolve

libconvolve is Florian Schmidt's C library for partitioned audio convolution.
The 0.0.8 recipe builds a static library using the upstream portable C complex
multiplication fallback, without the optional Apple libDSP dependency.

The public `convolve.h` header exposes FFTW's single-precision types. Consumers
therefore receive `fftw3f` headers transitively. See `0.0.8/notes.md` for the
upstream build and license caveats.
