# wput

Wput is a command-line FTP uploader. This archive contains the HarmonyOS PC
AArch64 build of the official upstream snapshot `0.6.2-git20130413`.

## Build and test

The package builds the `wput` executable with the upstream optional SSL backend
disabled because the published HarmonyOS GnuTLS package lacks Wput's required
OpenSSL-compatibility interface. Its consumer test runs on native HarmonyOS and
checks the executable version plus a binary upload to a local FTP test server.

See [`0.6.2-git20130413/notes.md`](0.6.2-git20130413/notes.md) for the pinned
upstream revision and adaptation details.
