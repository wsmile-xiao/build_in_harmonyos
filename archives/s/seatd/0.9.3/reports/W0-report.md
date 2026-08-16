# W0 dependency report

- Package: `seatd/0.9.3`
- Issue: `2146`
- Date: `2026-08-14`
- Result: **pass**

## Source identity

- Official repository: <https://git.sr.ht/~kennylevinsen/seatd>
- Tag: `0.9.3`
- Commit: `daa8196e10b180b8b0caeafa8e5f860eb1bd6706`
- Recipe archive: <https://github.com/kennylevinsen/seatd/archive/refs/tags/0.9.3.tar.gz>
- Expected SHA256: `302564d54d8e28191fadfd734f2675ecb0c9e0615a58011b89ef15dfa4dbaa96`

The tag and commit were verified with a shallow clone of the official SourceHut repository.
The 42086-byte GitHub archive was also downloaded through the codeload endpoint and hashed
locally; the result matches `conandata.yml`.

## Dependency classification

| Dependency | Kind | OHOS action | W0 result |
|---|---|---|---|
| libc | system, required | use platform libc | available |
| librt | system probe | use platform toolchain result | no Conan package needed |
| libsystemd / libelogind | optional | disable `libseat-logind` | not required |
| scdoc >= 1.9.7 | optional build tool | disable man pages | not required |

Meson, Ninja, and pkg-config are worker build tools rather than package requirements.
There are no required Conan references to query from `ohpcd`, so no dependency adaptation
issue or PR is needed before continuing with seatd.
