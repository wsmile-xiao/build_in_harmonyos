# HarmonyOS aarch64 shadow CI report

## Result

- Issue: AtomGit #33
- Package: `archives/p/portaudio/19.7.0`
- Tested commit: `b46c7b1eff9f8602f8194a53db0a086efe650842`
- Runner: `local-ohos-shadow-device1`
- Device: HarmonyOS localhost, HongMeng Kernel 1.12.0, aarch64
- Toolchain: clang 15.0.4, Python 3.12.9, Conan 2.29.1
- Completed: 2026-08-18 16:17:11 UTC
- Final status: pass

The run was serialized through the device-global lock and the shadow runner
lock. Both locks were released after completion.

## Input verification

- Source archive SHA-256: `c4183aae99ef3625e413d43f4ee3253cb3f7c45453405c97a941e2d8b7995f33`
- `ci/conan/setup.sh`: `f47707554e0b21e6845fb4f007cb80192abb9de023d8acb457b4243c632b4b52`
- `ci/conan/build_and_test.sh`: `dc1194c6583d93b7c53a2fa5a8de2c3921589ab344034611bc59d0b9d21f9bf8`
- `ci/conan/profiles/ohos-aarch64`: `63085cfa7a03f55f2c490939df0f924a73e08005ca77db1bd851ce2c2e08d18e`
- Recipe: `3b6aeb734f37fb8e6f909a14be77cc5bbf64a5aa0ffd668211e02b8982ba1692`
- Input verification record: `5b3ea69951a05232541f1e9b68f7542780cccfeb76da19f06ee772fa7d166779`
- Environment fingerprint: `2b5f655920d0327af5dd1794761325d0d5e03976f75985b92a42558196fe8a9a`
- Setup log: `b73d7d271cc4cdbe3935e66df7a7ade8dbdb82d330eb729ac054ecabb1b6e716`
- Build log: `5e3f229ac8ad614b43c819e475cb8540fa0ead2b2841c1d272012ed32f3403d0`
- Gate results: `c133933448138962779f5d466bcb28dc995f7492108d759ff8f30cc6dc554459`

Preflight run:
`/storage/Users/currentUser/ohpc-ci-shadow/runs/b46c7b1eff9f-20260818T161138Z-preflight-40957`

Final run:
`/storage/Users/currentUser/ohpc-ci-shadow/runs/b46c7b1eff9f-20260818T161314Z-run-42361`

## Tests and gates

- Conan `test_package`: pass; the consumer linked `PortAudio::PortAudio`,
  initialized the library, and reported `host_apis=0 devices=0`.
- Consumer output: `PASS portaudio PortAudio V19.7.0-devel, revision
  147dd722548358763a8b649b3e4b41dfffbcfbb6 host_apis=0 devices=0`.
- The test package executed 10 deterministic assertions and verified the
  signed consumer ELF.
- R34 destructive dependency test: pass.
- L0: pass, all checks passed.
- L1: pass, `test_package` executed.
- L2: skip, the static library package has no `bin/` directory.
- L4: pass, patches clean.
- L5: pass, `lib/` has content.

## Failure and repair

The first run at
`/storage/Users/currentUser/ohpc-ci-shadow/runs/d39148d55c07-20260818T155505Z-run-19622`
failed before compilation because Conan's `Autotools.configure()` attempted to
execute the HMDFS-mounted `configure` script directly and received
`/system/bin/sh: .../configure: Permission denied`.

The recipe now preserves Conan's complete generated configure argument string
and invokes the script explicitly through `/system/bin/sh` on OHOS. The final
run passed configure, compilation, packaging, consumer execution, and all
applicable gates.

## Post-shadow official CI

The historical shadow run above predates packaging the hardware-independent
upstream QA executable. On commit
`826dcf72b4971547df74eeea8e0f7722c56557b9`, official CI #27925 additionally
signed and ran `package/tests/paqa_errs`, which reported `20 passed, 0 failed`,
then ran the existing consumer test. The official L0/L1 gate passed.
