# E2622: Pure resource CMake packages need path-preserving Conan consumers

## Symptom

A data-only Debian package has no linkable library dependency and no upstream
test suite. A generic Conan create can still succeed while resources are
installed under the wrong relative path or while a consumer never proves that
the files are present and readable.

## Root cause

Resource packages are validated by filesystem contracts rather than exported
link targets. CMake computes `CMAKE_INSTALL_FULL_DATADIR` from the install
prefix and the data-directory setting. Without an explicit data-directory
binding, the package can be structurally valid but incompatible with consumers
that expect a conventional `share/<resource>` tree. Package creation alone
also does not prove representative files survived extraction, install, and
packaging.

## Fix

1. Download the official source archive and bind its byte count and SHA-256.
2. Configure the upstream CMake project with an explicit data directory and
   install through the upstream install target so relative paths are retained.
3. Keep the recipe's package type consistent with a data/application payload
   and avoid inventing a library target for non-linkable files.
4. Add an independent consumer source that checks the resource root, a bounded
   inventory threshold, representative files from separate subdirectories,
   and non-empty bytes.
5. Keep resource presence separate from target playback or device integration;
   those require an independent runtime gate.

## Validation

For lomiri-sounds 25.01, the official GitLab archive was 18,823,555 bytes with
SHA-256 `00aeb6c36ef311145a270deffc02728067ef3bd18c00d3a90353712eadf2cc8c`.
The source CMake project installs `share/sounds` and `data/lomiri-sounds.pc`.
The consumer test is designed to validate the installed tree without relying
on an audio device or a linkable API.

## Reusable decision rule

When a package ships data rather than a binary or library, define the install
path as an explicit contract and test the contract from the consumer side. A
successful configure or package creation is not enough evidence for a data
consumer.

## Safety boundary

This pattern applies to CMake data/resource packages. It does not prove that
the target platform can play or interpret the resource format, and it does not
authorize claiming release or device success from file-presence checks alone.
