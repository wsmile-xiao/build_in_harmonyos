# reop

reop 2.1.1 is a command line file encryption and signing tool packaged for HarmonyOS PC (aarch64). The Conan package contains the native `reop` executable, its manual page, and its ISC license notice.

Build from the repository root with its OHOS Conan profile:

```sh
conan create archives/r/reop/2.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

It depends on the published `libsodium/1.0.22` recipe. See `2.1.1/notes.md` for the source checksum, compatibility patch, and native test results.
