# STIFF 2.4.0

- Builds the command-line converter against fixed-hash upstream libtiff source
  and the published zlib and libjpeg Conan dependencies.
- The release does not provide an automated upstream test suite.
- The consumer validates the exact version output, generates a standards-based
  2x2 FITS image, converts it, and verifies the resulting TIFF signature.
- Optional worker threads are disabled for a small portable baseline.
- Official OHOS test and CI results remain pending.
