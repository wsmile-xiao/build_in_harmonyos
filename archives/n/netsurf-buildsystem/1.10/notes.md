Tested on HarmonyOS PC (OHOS 6.0, aarch64) with conan 2.29.1.

## Upstream

- Name: netsurf-buildsystem
- Version: 1.10
- URL: https://download.netsurf-browser.org/libs/releases/buildsystem-1.10.tar.gz
- License: MIT (COPYING file)

## Build system

Plain GNU Make. The Makefile supports `make install PREFIX=...` but this
recipe uses Conan 2's no_copy_source + manual copy in `package()` to put the
files into the standard package layout under `share/netsurf-buildsystem`.

`make test` is a no-op target upstream. We invoke it anyway to capture the
build step record in the Conan log.

## Patches

No patches applied. The release builds clean as-is.

## Notes

- package_type = "build-scripts"
- no_copy_source = True
- exports NSSHARED via buildenv_info and runenv_info
- Defines a virtual `lib` directory so consumers can `include $(NSSHARED)/makefiles/Makefile.tools`
