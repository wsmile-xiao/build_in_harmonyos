# diff-pdf

diff-pdf is a tool for visually comparing two PDFs.

## OpenHarmony Adaptation

The original diff-pdf requires wxWidgets and poppler-glib, which are not available on OpenHarmony.
This adapted version uses poppler-cpp C++ API and removes wxWidgets dependency, providing a headless command-line mode only.

## Available Versions

| Version | Status | Notes |
|---------|--------|-------|
| v0.5.3 | built | Headless mode only (no GUI); uses poppler-cpp + cairo |