mhash is a hash algorithm and key generation library used by legacy tools such
as mcrypt.

## Features

- Provides message digest algorithms including MD5, SHA1, SHA2, RIPEMD, TIGER,
  GOST, SNEFRU, and WHIRLPOOL.
- Provides HMAC and key generation helpers.
- Installs the public `mhash.h` API and `libmhash`.

## OHOS adaptation

- Upstream uses Autotools.
- The recipe builds a static `libmhash.a` for OHOS consumers.
- Old `config.guess` and `config.sub` scripts are patched during `build()` for
  OHOS triplet recognition.
- The upstream `make check` suite is executed during the Conan build; OHOS r7
  passes all 5 registered upstream tests and the Conan consumer test package.

## References

- https://mhash.sourceforge.net/
- https://downloads.sourceforge.net/project/mhash/mhash/0.9.9.9/
