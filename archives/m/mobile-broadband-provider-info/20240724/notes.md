# mobile-broadband-provider-info 20240724 adaptation notes

## Source identity

The task and Conan package version are **20240724**. GNOME publishes no
20240724 directory in its official release index, and the GitLab tag listing
has no 20240724 tag. The newest available upstream release is 20240407, so
this recipe uses that source archive as the nearest-release fallback. The
archive SHA-256 was recomputed locally as
`89bfeff215f4bff8e9c3ff2ec25250fdb080d11e9bfa59c6fc71982ac01c814a`.
The package metadata therefore distinguishes the task version (20240724)
from the data's upstream pkg-config version (20240407).

## Build environment and steps

- Build system: Meson; no C/C++ object or library is produced.
- Target: native OHOS aarch64 HarmonyOS PC.
- Build inputs: Meson 1.12.1, Ninja 1.13.2, xsltproc/libxslt 1.1.45_1,
  xmllint, and OHOS clang 15.0.4; no Conan runtime dependencies.
- `meson.build` declares the C language, so Meson still probes a compiler and
  archiver even though the package is data-only. `MesonToolchain` supplies the
  device compiler, and the recipe adds the absolute `llvm-ar`/`ar` path to the
  machine file to avoid PATH symlink resolution failures.
- Configure with `--prefix=/` so Conan's destination staging yields the
  package's `share/` layout.
- Upstream tests run during `build()`. `test_package` then runs a Python
  consumer validator against the installed package and replays `xmllint` on
  the installed XML/DTD pair.

## Installed-data consumer contract

The consumer verifies that the installed tree contains `serviceproviders.xml`,
`serviceproviders.2.dtd`, generated `apns-conf.xml` and the pkg-config file;
parses the XML; validates its DTD declarations and exact country/provider
counts; checks the generated APN schema; and resolves `pkgdatadir` relative to
`${pcfiledir}`. `package()` rewrites the upstream absolute `pkgdatadir` to this
relocatable location so consumers do not depend on the build prefix.

## Source and tests

- Upstream: <https://gitlab.gnome.org/GNOME/mobile-broadband-provider-info>
- Task-version source check: GNOME source index and GitLab tags checked on
  2026-09-26; 20240724 absent, newest published release 20240407.
- Source archive: <https://download.gnome.org/sources/mobile-broadband-provider-info/20240407/mobile-broadband-provider-info-20240407.tar.xz>
- Upstream suite: 2 registered Meson tests (`check-blanks` and `xmllint`);
  on-device result was 1 OK + 1 declared EXPECTEDFAIL, 0 failures, exit 0
  (2/2 pass by upstream semantics).
- Adapted consumer: `test_package/test_verify.py` parses the installed XML and
  passed 19/19 assertions. `test_package/conanfile.py` checked Conan package
  version 20240724, invoked the consumer validator with `self.run()`, and
  passed installed-tree xmllint DTD validation. `conan create` exited 0.

## Validation result

HarmonyOS PC aarch64 command:

```text
conan create .../archives/m/mobile-broadband-provider-info/20240724 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
CREATE_EXIT:0
Meson: 1/2 OK, 1/2 EXPECTEDFAIL, 0 failures
test_package: MBPI_VALIDATION_PASS assertions=19; installed xmllint PASS
```

The `EXPECTEDFAIL` is the upstream `check-blanks` test's declared
`should_fail: true` behavior; its nonzero grep result is the expected pass
condition and Meson exited successfully.

## Reusable adaptation experience

For data-only Meson projects that still declare C, provide an absolute archiver
in the Meson machine file, configure with `--prefix=/` for Conan staging, and
test the installed data through a real consumer. Validate relocatable metadata
after installation instead of relying only on successful source-tree tests.
