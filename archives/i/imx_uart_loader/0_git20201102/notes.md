# imx_uart_loader 0_git20201102 — adaptation notes

## What this software is

`imx_uart` downloads and executes an image over the **serial boot protocol** on
NXP i.MX5/6/7/8 series SoCs. It ships inside the upstream project
[`boundarydevices/imx_usb_loader`](https://github.com/boundarydevices/imx_usb_loader),
whose Makefile builds **two** binaries from one tree:

| binary | objects | libusb? |
|---|---|---|
| `imx_usb`  | imx_usb.o imx_sdp.o **imx_sdp_simulation.o** imx_loader_config.o sdp.o sdps.o | yes (`$(USBLDFLAGS)`) |
| `imx_uart` | imx_uart.o imx_sdp.o imx_loader_config.o sdp.o | **no** |

The task names `imx_uart_loader`, so this recipe packages the **UART** variant
only — matching the Alpine `imx_loader` source package, whose `imx_uart_loader`
subpackage owns exactly `/usr/bin/imx_uart`, while `/usr/bin/imx_usb` and
`/etc/imx-loader.d/` belong to the separate `imx_usb_loader` subpackage.

## Version string and source

`0_git20201102` is Alpine's `pkgver` for the `imx_loader` source package. Its
APKBUILD pins

    _commit=30b43d69770cd69e84c045dc9dcabb1f3e9d975a

so the version string and the tree are tied together. The recipe downloads the
**upstream GitHub tarball for that exact commit** (not a distribution repack),
and the checked-in sha256 is computed from that tarball:

    sha256 = 4357907c9669874d3ccbf00395bf0b1733c26e6daea85d721f1c0cd897f4162c

(The APKBUILD publishes only a sha512; the sha256 above was computed from the
download and independently confirmed against the upstream tarball.)

## Upstream test audit

This is the part that must not be guessed, so it is stated with its evidence.

**Enumeration.** `tests/Makefile` declares exactly one aggregate target:

    tests: test.imx.test test-dcd.imx.test test-plugin.imx.test

and drives each case the same way:

    %.test: % FORCE
    	@$(IMX_USB) -v -S 0x15a2:0x0061 $* > $@
    	@diff -u $*.output $@

`IMX_USB` defaults to `../imx_usb`. The `-S 0x15a2:0x0061` argument selects the
project's **built-in SDP simulation** (implemented in `imx_sdp_simulation.c`),
which is why the suite runs with no i.MX hardware attached; each case compares
the produced output byte-for-byte against a checked-in golden file.

**Count.**

| # | case | golden file | size |
|---|---|---|---|
| 1 | `test.imx.test` | `tests/test.imx.output` | 43 145 B |
| 2 | `test-dcd.imx.test` | `tests/test-dcd.imx.output` | 43 464 B |
| 3 | `test-plugin.imx.test` | `tests/test-plugin.imx.output` | 773 471 B |
| | **total upstream = 3** | | |

There is no other test entry point: the top-level Makefile's only test target is
`tests: imx_usb ; $(MAKE) -C tests/ tests`, and no CTest, gtest or check
framework appears anywhere in the tree.

**Coverage caveat — stated plainly.** The suite exercises the **`imx_usb`**
binary, not the `imx_uart` binary this recipe packages. Its value here is real
but partial: `imx_uart` links `imx_sdp.o`, `imx_loader_config.o` and `sdp.o`, so
those translation units *are* covered, while **`imx_uart.c`'s own logic is not
covered by any upstream test**. `imx_uart` also omits `imx_sdp_simulation.o`, so
the simulation path the tests rely on is not part of the packaged artifact.

The Alpine packaging agrees that the suite is not runnable as a package check —
its APKBUILD carries `options="!check" # No tests available`. That statement is
about *not wiring the suite into apk's check phase*; the suite itself does exist
and is runnable by hand, which is what this recipe does from `build()`.

**Requirement consequence.** Running the suite needs `imx_usb`, hence libusb,
hence `libusb/1.0.27` is a declared requirement even though the **packaged**
`imx_uart` has no libusb dependency at load time.

## Adaptation decisions

* **No static-link requirement.** R26 forces static linking for
  *system-same-name libraries* so a `.so` cannot shadow `/lib` or `/lib64`.
  `imx_uart` publishes no library at all, so Conan-managed dynamic linking of
  its dependency chain is the correct default here.
* **Compiler from conf (R33).** `tools.build:compiler_executables["c"]` is used
  to drive `make CC=…`; no bare `$CC` is read from the environment.
* **libusb located without pkg-config.** The upstream Makefile resolves libusb
  through `pkg-config --cflags/--libs libusb-1.0`. pkg-config is not guaranteed
  to exist on the OHOS target nor to see the Conan package, so `USBCFLAGS` and
  `USBLDFLAGS` are supplied as **command-line make variables**, which override
  the Makefile's recursive `=` definitions.
* **RPATH for the bare CLI tool.** `imx_usb` is linked with
  `-Wl,-rpath,<libusb>/lib`. Unlike a library consumer, a standalone executable
  is not wrapped by the farm's `LD_LIBRARY_PATH` environment, so without this
  the test run could not find `libusb-1.0.so.0`.
* **`CONFIG_SHELL` for the harness (R5).** OHOS does not guarantee `/bin/sh`
  for a non-trivial script, so the harness is invoked through the
  profile-provided `CONFIG_SHELL` with a bash fallback.
* **`TMPDIR` inside the build folder.** The device's `/tmp` is a read-only
  erofs mount; every scratch path is kept in the build folder and an inherited
  `TMPDIR` is honoured.

## Device findings

Measured on the Harmony PC (aarch64/OHOS, clang 15.0.4) against the installed
binary:

| invocation | observed |
|---|---|
| *(no arguments)* | **HANGS** — no output, never exits (killed by `timeout`) |
| `-h`, `--help` | exit **0**, prints the usage banner |
| `-V` | exit **0**, prints `imx_usb 0.2pre` |
| `--definitely-not-an-option` | exit **0**, prints `unrecognized option` + usage |

Two things worth recording. First, **bare `imx_uart` with no arguments hangs**:
`parse_opts()` is expected to report the missing UART and return, but on this
platform the process never terminates. This is an upstream defect, not an OHOS
regression introduced here, and it is why every probe in `test_imx_uart.sh` is
wrapped in `timeout` — a first revision of that script called the binary
unguarded and wedged a real verify run until the device-side process tree was
killed.

Second, the `-V` banner reads **`imx_usb 0.2pre`** even in the `imx_uart`
binary, because upstream shares `IMX_LOADER_VERSION` between the two programs.

Exit codes are 0 for `-h`/`--help`/`-V` and even for an unrecognised option,
because `parse_opts()` returns a positive value there and `main()` maps any
`err > 0` to `EXIT_SUCCESS`.

## Status

**Device-verified on the Harmony PC** — `WIN01`, sha
`c5963113b50a5e1ecaf538b8a263a1bd58173941`, verify `PASS` (exit 0), 17.7 s.

| suite | result |
|---|---|
| upstream `tests/` | **3 / 3 passed** — `test.imx`, `test-dcd.imx`, `test-plugin.imx` |
| `test_package` | **4 / 4 passed** — help, long help, version, invalid option |

Both numbers are read off the device log for that exact SHA
(`logs/WIN01/imx_uart_loader-0_git20201102-c5963113b50a….log`), not restated
from the recipe.

Getting the upstream suite to pass required keeping `IMX_USB` **relative**: the
harness diffs its verbose output against golden files, and imx_usb derives the
config paths it echoes from `argv[0]`, so an absolute path failed the diff on
path strings alone with every protocol byte still matching.

`imx_uart.c`'s own logic remains **not covered by any upstream test** (see the
coverage caveat above); the `test_package` checks are a smoke test of the
installed binary's CLI surface, not a substitute for one.
