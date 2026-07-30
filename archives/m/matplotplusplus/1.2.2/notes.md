# Matplot++ 1.2.2 adaptation notes

## Configuration

- Build the static core library with bundled CImg and nodesoup.
- Disable examples, sanitizers, OpenCV, and the experimental OpenGL backend; enable the upstream compile-test target.
- Keep the public numerical and plotting model APIs available without requiring a display during tests.

## Verification

- The consumer test calls `matplot::linspace` and verifies the generated sequence.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
