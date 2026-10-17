# bpytop

bpytop is a Python terminal resource monitor for Linux-like systems. It shows
CPU, memory, disk, network, and process information in an interactive terminal
UI.

## OHOS adaptation

This archive packages bpytop as a Conan application package. The recipe installs
the pinned `psutil` runtime dependency from source and provides a `bpytop`
wrapper that sets `PYTHONPATH` before launching the upstream script.

The test package uses the non-interactive `bpytop --version` command and checks
that the packaged themes are present.
