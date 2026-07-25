# iir1 1.10.0 W0/W1 report

## Result

iir1 is a leaf dependency and can proceed immediately. No third-party Conan
requirement, system feature library, private toolchain, assembly source, or
closed binary is present in upstream tag 1.10.0.

## Evidence

- W1 base: `origin/main` commit `8c5703f967b606bc454831e265005d440d26dce5`.
- Official release: tag `1.10.0`, published 2025-07-06, commit
  `0a331a85e2ef58e550bed58d2485eee9858f61b8`.
- Official archive: 2,327,584 bytes, SHA-256
  `13b53f14d276adf6cafd3564fcda1d4b3e72342108d1c40ec4b4f0c7fc3ac95a`.
- Tag tree: 727 files; 11 files under `test/`; 8 CTest registrations.
- Build files contain no third-party dependency discovery or download.
- cmd-pkgs README blob `5b7e201c84be715eb3993f07287406a9b649bd39`:
  no `iir1` or `libiir` match.
- ohpcd control: `zlib/1.3.1.1` recipe download succeeded.
- ohpcd target: `iir1/1.10.0` recipe download failed with the CNB generic
  missing-package response, so no published recipe can be verified.
- Issue scan before creation: 1,002 all-state Issues, zero iir1 matches.
- Issue scan after creation: exactly one match, Issue #1246, open, author
  `2301_80739235`, fixed applicant fields present, linked to downstream #1093.
- PR scan: 2,969 all-state PRs; only merged #964, which has no Conan recipe.

The exact capacity error text was not observed in this task or Issue #1246.
