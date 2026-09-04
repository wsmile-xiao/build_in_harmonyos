# libgee 0.6.8

## Source and build

The official GNOME tarball is an Autotools release. It contains generated C
sources, `gee.h`, `gee-1.0.vapi`, and `gee.vala.stamp`, so the recipe does not
need a Vala compiler. The package provides the `gee-1.0` pkg-config module.

## OpenHarmony changes

- `config.guess` recognizes `HarmonyOS` and returns `aarch64-unknown-linux-ohos`.
- `config.sub` accepts `linux-ohos` in the target triplet.
- `configure` uses umask 022 for temporary files, which avoids HMDFS permission
  failures during configure.

## Dependencies and verification

The only Conan dependency is `glib/2.84.0`. The upstream `make check -j1` suite
must run during the Conan build. The test package then links against `gee-1.0`
and asserts that two inserted strings produce collection size two.

Local Windows verification is limited to recipe syntax and patch applicability;
the OHOS Conan build and target execution remain CI/device gates.
