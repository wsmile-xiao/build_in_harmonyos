# king-probe

Probe reads PDB atomic coordinates and calculates molecular contact dots, overlaps and external surfaces.

It supports SELF, ONCE, BOTH and OUT selections, kinemage graphics, contact statistics and unformatted records. The upstream executable is named `probe`; the Conan package is `king-probe`.

## HarmonyOS

The recipe uses upstream CMake unchanged. One generated source patch adds only exact `--version` and `--help` aliases for native CI, preserving original flags and numerical behavior. It packages `bin/probe`, the two upstream README files under `share/doc/king-probe/`, and original source notices under `licenses/SOURCE-NOTICES.txt`.

Build requirements are Conan 2, CMake and a C/C++ toolchain (the upstream project enables both languages). Runtime dependencies are the system C runtime and math library; there are no third-party Conan dependencies. The consumer suite additionally needs native Python 3 and a C compiler for its platform helper.

Native OHOS PC tests check the installed program by absolute path and exercise the actual HarmonyOS kernel and numeric runtime. Cross builds cannot silently skip testing; a deliberately build-only run must explicitly disable the test folder and be reported as build-only.

The alias-patched recipe passed all eleven native ARM64 tests on OpenHarmony 6.1.0.115, including the HarmonyOS-specific runtime probe. The W3 local CI flow and Conan verification also passed. The package is built locally but not published. Older x86_64 emulator exploration is separate evidence.

## Source and usage

- [Upstream repository](https://github.com/rlabduke/probe)
- [02.21 tag](https://github.com/rlabduke/probe/tree/02.21)
- Run `probe -version` (alias `--version`) for the upstream version and `probe -h` or `-help` (alias `--help`) for options. Other options retain upstream single-dash syntax.
- Example: `probe -quiet -countdots -self all structure.pdb`

Scientifically meaningful packing analysis normally requires explicit hydrogen coordinates, as described in the bundled `README.probe.txt`. The small consumer fixture tests software behavior, not scientific validation of a real structure.

Licensing is recorded using local LicenseRef labels for this tag's custom Probe and hybrid36 notices. No license text from current master is substituted.
