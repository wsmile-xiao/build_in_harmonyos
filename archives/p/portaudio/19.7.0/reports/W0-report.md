# W0 dependency report

## Target

- Package: `portaudio/19.7.0`
- Issue: AtomGit #33
- Checked: 2026-08-18, serialized device run
- Remote: `ohpcd`
- Isolation: per-run `CONAN_HOME` under the HarmonyOS test runner

## Direct dependency availability

The recipe has no direct Conan dependencies. ALSA, JACK, OSS, and ASIHPI are
explicitly disabled because those host APIs are unavailable in the target
package graph and are not required by abx's PortAudio API use.

## Source and build-system checks

- Upstream archive downloaded successfully
- Official SHA-256 matched `47efbf42c77c19a05d22e627d42873e991ec0c1357219c0d74ce6a2948cb2def`
- Current Autotools release scripts expose independent backend switches
- Selected patches apply cleanly and sequentially to the verified source

## Device checks

- Conan setup resolved the isolated graph with zero direct requirements.
- The OHOS aarch64 profile and recipe passed the Shadow runner input checks.
- Final run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/b46c7b1eff9f-20260818T161314Z-run-42361`
- The consumer test initialized PortAudio and reported `host_apis=0 devices=0`.
- The final run completed with `status=pass`; no package publication was
  performed as part of this issue.
