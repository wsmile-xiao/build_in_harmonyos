# abx 0.1 device integration prevalidation

Date: 2026-08-19

## Classification

This is a device-side integration diagnostic, not formal Shadow CI or R36
publication evidence. The direct GTK, libsndfile, and PortAudio recipes remain
unpublished. Their independently validated Conan caches were copied into a new
isolated `CONAN_HOME`; the source caches were not modified.

Dependency cache sources:

- libsndfile: `runs/f2707f8869c6-20260817T034613Z-run-38240/conan-home`
- portaudio: `runs/7a8ba84d2629-20260819T030503Z-run-33620/conan-home`
- GTK/transitive dependencies: `runs/aa8c09d961c5-20260819T035611Z-run-22249/conan-home`

## Reproduction metadata

- Conan: 2.29.1
- Profile: `ci/conan/profiles/ohos-aarch64` for host and build
- Run root:
  `/storage/Users/currentUser/ohpc-ci-shadow/abx-r10-0819`
- Base commit: `d7a52587f8e209b08bf64c2132f89f1b5ece3534`
- Working-tree input SHA256:
  `b4fced911d8f26d4610784393e979c49a2329a7b88806f074493d77676f9181d`
- Command:

```sh
conan create archives/a/abx/0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build="abx/*"
```

The run held `/storage/Users/currentUser/ohpc-ci-shadow/device1-shadow.lock` and
released it after completion.

## Results

| Stage | Result |
|---|---|
| Eight sequential source patches | PASS |
| aclocal/autoconf/autoheader/automake regeneration | PASS |
| HMDFS-safe configure/config.status | PASS |
| Dependency probes | PASS |
| `make -j1` and install | PASS |
| OHOS ELF self-sign and `.codesign` validation | PASS |
| Installed-binary CLI, libsndfile, ABX, GTK3, and PortAudio assertions | PASS (33/33) |
| Mismatched-duration and malformed-audio negative assertions | PASS (4/4) |
| test_package aggregate | PASS (37/37) |
| `conan create` | PASS (exit 0) |

Evidence:

- Log: `/storage/Users/currentUser/ohpc-ci-shadow/abx-r10-0819/conan-create.log`
- Log SHA256:
  `da9fb4f0ee8f919e6e2389ae58d1e93a5f860591a705435750d6e7bd05f3e4c7`
- Artifact: 64-bit LSB PIE arm64 dynamic ELF, 551360 bytes
- Artifact SHA256:
  `2351870532e510c81f4e6df86026b268119fe7c2d3110d063b14b48ad5517cd6`
- `.codesign` section count: 1
- Runtime output:
  `abx self-test: PASS files=2 frames=800 trials=8 gtk=3.24.38 portaudio-host-apis=0 portaudio-devices=0`
- Negative output includes `audio fixtures have different geometry` and
  `cannot open audio fixture`.
- Final output: `abx test_package: PASS`.

The zero PortAudio host API/device inventory is the expected state of the
current independent PortAudio package. It proves initialization and consistent
inventory handling only; this report does not claim hardware playback.

## Remaining gates

1. Publish `gtk/3.24.38`, `libsndfile/1.2.2`, and `portaudio/19.7.0`.
2. Repeat W0 against `ohpcd` from a fresh isolated Conan home.
3. Resolve the out-of-scope `archives/a/abx/commands.json` L0k requirement.
4. Run the repository Shadow CI wrapper and capture the formal L0-L5 summary.
