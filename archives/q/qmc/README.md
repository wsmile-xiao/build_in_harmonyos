# qmc

qmc is a command-line tool that simplifies Boolean expressions with the Quine-McCluskey method. It can print a simplified result, show a truth table, and accept interactive input.

## OpenHarmony PC adaptation

The upstream 0.94 archive contains C++ source files and manual `g++` build instructions. This archive supplies a small CMake build file so Conan can use the target compiler and install the `qmc` executable. The command-line program has no third-party C++ dependencies.

Upstream also includes `qmc-gui.tcl`, an optional Tcl/Tk frontend. The current Conan package provides the CLI executable; the frontend is not run or claimed as tested on OpenHarmony PC.

The source is retrieved from the [Debian original-source archive](https://deb.debian.org/debian/pool/main/q/qmc/qmc_0.94.orig.tar.gz) with a fixed SHA256. The original project homepage recorded in the source is `http://qmc.pollaknet.at/`.

The [OHPCD PR build 65742](https://ohpcd.atomgit.com/buildbot/#/builders/1/builds/65742) built adaptation commit `31591bf0` on OHOS 6.0 armv8 and passed eight installed CLI behavior checks plus the L0/L1/L2/L4/L5 gates. The package has not been uploaded to the public Conan registry.
