# libkal

libkal is a small C library for converting dates between Julian, Gregorian,
Arabic, and Jewish calendar systems. It also provides date validation,
calendar-name lookup, Easter calculation, and day-of-week helpers.

## HarmonyOS adaptation

- Builds a static `libkal.a` with the C compiler selected by the Conan profile.
- Applies narrowly scoped C-prototype and test-entry-point portability patches.
- Runs all seven measured upstream test invocations natively on HarmonyOS.
- Provides a consumer API test and a separate HarmonyOS/aarch64 ABI test.

## Dependencies

- C standard library only.

## References

- Authoritative source archive: https://launchpad.net/debian/+archive/primary/+sourcefiles/libkal/0.9.0-6/libkal_0.9.0.orig.tar.gz
- Package history: https://tracker.debian.org/pkg/libkal
