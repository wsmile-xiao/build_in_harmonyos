# virtualpg 2.0.1 HarmonyOS target validation

## Environment

- Date: 2026-07-31 (Asia/Hong_Kong)
- Platform: HarmonyOS PC, AArch64
- Conan profiles: `os=OHOS`, `os.version=6.0`, `arch=armv8`, Release for host and build
- Toolchain: Clang 15.0.4 and Conan 2.29.1
- Source SHA256: `be2aebeb8c9ff274382085f51d422e823858bca4f6bc2fa909816464c6a1e08b`
- Post-fix isolation roots: `/storage/Users/currentUser/tmp/virtualpg-w3-1272-r6-shared` and `/storage/Users/currentUser/tmp/virtualpg-w3-1272-r6-static`
- Recipe SHA256: `9b12a0ef24d837886484b84c801d5d8c3bb051a0e4feff4c651a2f203d22ed06`
- Test recipe SHA256: `18ef21cc8c400ddd1eddb89cf6afd51a580ea84f5004517d7f89005b53cd9b78`
- API consumer SHA256: `1789259315eddb92c8c9bbbb2a5b333b013225220adb9d29b596c4615376bf93`
- Module consumer SHA256: `fad81b3ffcbfb86462138e5bb83fb6013668d5f9c1c170a650786cb05f7d0187`

## Dependency lock

| Dependency | Recipe revision | Package ID | Binary revision |
| --- | --- | --- | --- |
| `sqlite3/3.49.1` | `669361066cc2c76e0ed897e6b6a27e38` | `6b129b068851896169fae42d399fa922d239ce8a` | `9bae7e00509d3fd4c2f65da552f63fad` |
| `libpq/18.1` | `6f9e9c128f7c346abe8bbf26fa729453` | `01d92cf349a0dd98ff915f4bd99a04430171517f` | `f5e4e7897968df850e6f578157f31290` |

Both binaries were downloaded from `ohpcd`; the isolated run did not build either dependency from source.

## Test summary

| Scope | Logical cases | Assertions | Result |
| --- | ---: | ---: | ---: |
| Upstream Automake `make check` | 0 | 0 | `0/0` (not applicable) |
| Public API and real libpq forwarding consumer | 1 | 7 | `1/1`, `7/7` PASS |
| SQLite loadable-module consumer | 1 | 4 | `1/1`, `4/4` PASS |
| Total added consumers | 2 | 11 | `2/2`, `11/11` PASS |

Upstream provides no registered Automake `TESTS`. The recipe still executed `make check` in both shared and static builds and both invocations returned 0. Shared/static runs validate two packaging modes and are not counted as separate logical test cases. The static package cannot contain the loadable module by contract, so it reruns only the seven-assertion API consumer.

## Conan results

- Shared: command returned 0; `virtualpg assertions: 7/7`; `virtualpg module assertions: 4/4`.
- Static: command returned 0; `virtualpg assertions: 7/7`.
- Shared full reference: `virtualpg/2.0.1#c3884da26f3ddaa0e4282f0d911a4a23:fc4a2cce07d1fa2f165214c9f7352c0ad2a2921e#1f292dad8b8249fc0bd7b9e6a7550fe6`.
- Static full reference: `virtualpg/2.0.1#c3884da26f3ddaa0e4282f0d911a4a23:aaeb458f7741d374067a5406dd8398f821fe6b30#f7f632488bcd75da9a8fa5abc0437b3d`.

## Artifact audit

- Shared library payload: exactly `libvirtualpg.so` and `mod_virtualpg.so`; no `.a`, `.la`, or versioned `.so` aliases.
- `libvirtualpg.so`: SONAME `libvirtualpg.so`.
- `mod_virtualpg.so`: SONAME `mod_virtualpg.so`; NEEDED includes `libpq.so.5`.
- Neither shared object has RPATH or RUNPATH.
- Static library payload: exactly one non-empty `libvirtualpg.a`; no `.so` or `.la` files.
- Both modes include `virtualpg.h`, `COPYING`, and a relocatable `virtualpg.pc` with `prefix=${pcfiledir}/../..` and `Requires: sqlite3 libpq`.
- Package-file and string scans found no Conan build-folder paths in the delivered payload.

## Preserved logs

- Shared post-fix target log SHA256: `050ff2a48cd16021642e7119427064503c975a365dbf77abd218c090c5d63af4`.
- Static post-fix target log SHA256: `a7847f3749043ea5685079f3bad8a657481e3a3dc1f19283bf719e4159b9c18b`.
- Local copies: `E:/HarmonyPC/validation/virtualpg-2.0.1/patch-gen-r5/shared-w3-r6.stderr` and `patch-gen-r5/static-w3-r6.stderr`.
- Both target temporary roots were removed after the logs were copied, and each absence check passed.

## Local W3 approximation

- Runtime: Ubuntu-D under WSL, Linux/x86_64, Clang 15, Conan 2.29.1. A private mount namespace temporarily bound the Linux profile and LF runtime files over the repository paths expected by `finish`; no framework file was changed.
- The remote has no Linux/x86_64 binary for `sqlite3/3.49.1`. Its official recipe revision `669361066cc2c76e0ed897e6b6a27e38` hard-codes the link command without `-lm`, so a temporary PATH wrapper appended `-lm` only while prebuilding that Linux prerequisite. Standard PATH was restored before `finish`.
- Linux prerequisite result: package ID `0ade6466c592f1ea55d37085609f8a5ef91e981f`, package revision `1292236de85bd0eb3ef33043f42c4ea7`; log SHA256 `b0f2ff1d6e84bf64141c460d4f7f53e7a29675169e9250755146390f48253e19`.
- Post-fix `finish` Conan verification passed G2 and G3, then the independent W3 `build_and_test.sh` passed. Its root package reference was `virtualpg/2.0.1@ohpcd/stable#c3884da26f3ddaa0e4282f0d911a4a23:75a5a311f61cad7910e43119f79ee3e2a3b91b38#666f71ae775ad7ffdd095d20b283177c`; both consumers again reported `7/7` and `4/4` assertions.
- Post-fix W3 Conan log SHA256: `d9944888f72d492bbede0c181a5cb3e020b154e4c04f75da3248ac4b2689e440`.
- `finish` automatically generated `.ci-result.json` at `2026-07-31T21:13:05.872616` with `exit_code=0` and integrity hash `85a0a36c9b2b1a8f`. Independent recomputation of `sha256(timestamp:software:version:exit_code)[:16]` matched. That formula does not bind the log, profile, environment, commit, or toolchain.
- After W3 and the knowledge check had completed, the legacy full-repository `SUMMARY.md` scan entered WSL 9P I/O. Only the isolated r7 process group was terminated; its EXIT trap recorded 143, removed every bind mount, and left no task process. The finish log SHA256 is `a1407104e4dbd8ae608e9314bc2712a40a12baf9ae5b447970f3568f4c27ae6e`.

## Final patch packaging continuity

- Final `0001-config.guess.patch` SHA256: `8d6e81bf1c483db209624efa223b6bb399edef7c8b237eb40b9cb3d49c6b7153`.
- Final `0002-config.sub.patch` SHA256: `8873575666754867d36549ea82647b3112056b0b528c0d0e941aac81355bf9b0`.
- Final `0003-configure.patch` SHA256: `1373f68575fe2dcefb4c9d8eecd1c9d928d14ebe1c90d175629a50b8407e9b62`.
- Git (`core.autocrlf=false`, `--whitespace=error-all`) check and apply: `3/3` PASS.
- GNU patch 2.7.6 (`--fuzz=0`) dry-run and apply: `3/3` PASS.
- Windows patch-ng 1.19.1 (`fuzz=False`) apply: `3/3` PASS.
- HarmonyOS Toybox patch and HarmonyOS patch-ng each applied `3/3` patches. Both result trees contain 28 files with the same sorted full-tree manifest SHA256 `b3b9af7a5522fe3d17d88e72c62497508982bb6723723ac9a7c7c8b1bc9f6c11`.
- Final `config.sub` and controlled-`uname` `config.guess` probes both returned `aarch64-unknown-linux-ohos`.

The regeneration of `0001` and `0002` changes only their nested diff representation for the outer repository whitespace gate. `0003` is the targeted E129 fix for the two proven `confXXXXXX` directory-creation sites. The post-fix target reruns consumed the complete exported three-patch set; the formal PR CI must still rebuild that set and bind the result to the pushed full revision.

## Evidence boundary

This report records genuine HarmonyOS 6.0/AArch64 target builds and target execution. The WSL result is a separate Linux/x86_64 pipeline approximation; it is not added to the target test count. The formal PR Buildbot result must later be bound to the exact pushed commit through `ci_pr_number` and the full `ci_revision`.

## W5 knowledge-graph boundary

`ohc-run.py graph validate` read 214 `.kv` files, 214 `.md` files, and 214 index rows, then returned 1 with 123 errors and 91 warnings. The first errors are pre-existing schema failures in `E007`, `E009`, and other repository knowledge entries; they are not generated by this adaptation.

The candidate worktree and the main worktree are both based on `e8393fd1754b96dc522f49e7746fe6b1db52fa7e`. Working-tree and staged diffs under `knowledge/` are `0` in the candidate, and the main working-tree diff under `knowledge/` is also `0`, so both validations consume the same graph inputs. This dependency PR does not claim W5 PASS and does not modify shared knowledge infrastructure outside its atomic scope.
