# autoenv 0.4.0

autoenv is a directory-based shell environment hook. This archive packages the upstream `activate.sh` script as a Conan resource package for HarmonyOS PC/OHOS arm64.

## Package Contents

- `res/autoenv/activate.sh`: shell hook loaded by the user shell
- `res/autoenv/README.md`: upstream usage documentation
- `licenses/LICENSE`: MIT license

## Verification

The package is verified with `conan create` using `ci/conan/profiles/ohos-aarch64`. The consumer test sources the packaged `activate.sh`, enters a directory containing `.env`, and checks that the environment variable is loaded.
