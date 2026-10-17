# mdk

GNU MIX Development Kit (MDK): an emulation of Donald Knuth's MIX computer
and its MIXAL assembly language.

- Upstream: https://www.gnu.org/software/mdk/
- Source: https://ftp.gnu.org/gnu/mdk/v1.3.1/mdk-1.3.1.tar.gz
- Tools: `mixasm` (MIXAL assembler), `mixvm` (MIX virtual machine)

## OHOS adaptation

- Build system: autotools (`configure` + `make`), native aarch64 build.
- Optional features disabled: GTK GUI (`--disable-gui`), Guile shell
  (`--without-guile`), readline editing (`--without-readline`).
- Required dependency: `glib/2.84.0.1` from the ohpcd artifact repository.
- Upstream `make check` runs 6 automake tests in `mixlib/testsuite`.
