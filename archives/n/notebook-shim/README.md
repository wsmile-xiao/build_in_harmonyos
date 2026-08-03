# notebook-shim

Shim layer for Notebook traits and configuration used by Jupyter Server based applications.

## Version

- 0.2.3

## Build notes

- Pure Python package; no C/C++ compilation is required.
- Packages the `notebook_shim` module and upstream Jupyter Server extension config.
- Runtime integration with a full Jupyter stack still requires `jupyter_server`, as declared upstream.

## Test notes

The Conan `test_package` verifies the installed Python module metadata and extension config without launching Jupyter Server.
