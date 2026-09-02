# abx 0.1 local validation

Date: 2026-08-19

## Local preparation

| Check | Result | Evidence |
|---|---|---|
| Source integrity | PASS | Downloaded `abx_0.1.orig.tar.gz` SHA256 is `3eed66f4b70e826b469f8e7fa28ee7ecd84036bf1e384980636c9c3e985a10bb`, matching `conandata.yml` and Debian's signed `.dsc`. |
| Patch application | PASS | All eight patches were accepted sequentially by Conan's strict patch parser in the device integration build. |
| Python syntax | PASS | `ast.parse` accepted the main recipe, test-package recipe, and PCM fixture generator. |
| YAML syntax | PASS | PyYAML loaded `conandata.yml`, `manifest.yaml`, and `test_package/MANIFEST.yml`. |
| Conan load/export | PASS | The recipe loaded as `abx/0.1`, package type `application`, and exported its conandata and patch assets. |
| Shell syntax | PASS | Git `sh -n` accepted `test_package/test_abx.sh`. |
| Text format | PASS | Package text files are LF-only and have no UTF-8 BOM. |
| Change scope | PASS | Repository changes are confined to `archives/a/abx/0.1/`. |

## Device integration prevalidation

The unpublished dependency PR artifacts were copied from their independently
validated caches into a new isolated Conan home. Their original caches were not
modified. This makes the result useful integration evidence, but not an R36 or
formal Shadow CI result.

| Check | Result | Evidence |
|---|---|---|
| Input integrity | PASS | Working-tree archive SHA256 `b4fced911d8f26d4610784393e979c49a2329a7b88806f074493d77676f9181d`. |
| Autotools bootstrap | PASS | SDK Perl ran the Conan-cache aclocal/automake real entry points; autoconf and autoheader completed. |
| Configure | PASS | PortAudio, libsndfile, gthread-2.0, and gtk+-3.0 probes all succeeded; config.status generated both Makefiles and config.h. |
| Build/package | PASS | `make -j1`, install, and package creation completed. |
| Artifact | PASS | 64-bit arm64 PIE dynamic ELF, 551360 bytes, SHA256 `2351870532e510c81f4e6df86026b268119fe7c2d3110d063b14b48ad5517cd6`. |
| Signature | PASS | `llvm-readelf -SW` found exactly one `.codesign` section. |
| Consumer test | PASS | Installed-binary CLI, libsndfile I/O/seek, ABX statistics/bounds, GTK3 objects, PortAudio initialization, and two negative inputs passed 37/37 assertions. |
| Conan create | PASS | Exit 0; log SHA256 `da9fb4f0ee8f919e6e2389ae58d1e93a5f860591a705435750d6e7bd05f3e4c7`. |

PortAudio reported `host_apis=0` and `devices=0`. The test validates clean
initialization, inventory consistency, and termination, but hardware playback
is not available from the current independent PortAudio package and is not
claimed here.

Formal W0, project L0-L5, and Shadow CI remain blocked by unpublished direct
dependencies and the out-of-scope software-level `commands.json` requirement.
