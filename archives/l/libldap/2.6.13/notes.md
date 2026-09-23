# libldap 2.6.13 HarmonyOS adaptation notes

## Scope

Client libraries `libldap` + `liblber` built from the official OpenLDAP
2.6.13 release for HarmonyOS PC (OHOS aarch64, native build). Server side
(`slapd`), backends, and overlays are disabled; only the LDAP client
stack ships.

- Upstream: https://www.openldap.org/
- Release archive: `openldap-2.6.13.tgz`
- SHA-256: `d693b49517a42efb85a1a364a310aed16a53d428d1b46c0d31ef3fba78fcb656`
- Build system: Autotools with release-provided `configure`
- Source mirrors (same hash): OSU BLFS mirror + Savoir-faire Linux mirror
  ahead of the official URL (openldap-overlay-rwm/2.6.13 precedent).

## W0 dependencies

No Conan dependencies. Optional OpenLDAP features (Cyrus SASL, TLS via
OpenSSL/GnuTLS, LMDB, libevent, argon2, systemd, fetch) are disabled, so
no dependency adaptation is included.

## HarmonyOS handling

- Reuses `patches/0001-configure-hmdfs-temp-permissions.patch` verbatim
  from `openldap-overlay-rwm/2.6.13`: shell-mediated helpers, HMDFS-safe
  `/bin/install`, OHOS `config.sub` triplet acceptance, no `umask 077`
  wrapper in generated `config.status` scratch dirs.
- Explicit `--build/--host` triplets (`aarch64-unknown-linux-ohos` on
  OHOS) avoid unsupported HarmonyOS `config.guess` results.
- Configure scratch dirs prefer the native OHOS cache
  (`/data/storage/el2/base/cache`), then injected `TMPDIR`, then a
  build-local fallback, each verified with a create/write/remove probe
  (E112/E114). `TMPDIR/TMP/TEMP` are exported before configure.
- `--enable-mdb=no`: OHOS musl lacks pthread robust mutex support.
- Serial `make -j1` avoids HMDFS jobserver FIFO failures.
- `make check -j1 -k` is attempted best-effort; without `slapd` the
  upstream slapd-tester suite cannot pass, so the recipe never lets that
  hide the `HMBS_UPSTREAM_TEST_RESULT` evidence marker.

## Tests

Upstream ships 90 slapd-tester integration tests
(`tests/scripts/test000-rootdse` ~ `test088-syncprov-glue-rwm`, incl.
`test081-totp.py`); `tests/run` exits with `Could not locate slapd(8)`
when slapd is absent. This recipe is client-only (`--disable-slapd`),
so those 90 entries are documented as not runnable in the Conan sandbox
(see `test_package/MANIFEST.yml` audit). `build()` still runs
`make check -k` best-effort and always emits a real-count
`HMBS_UPSTREAM_TEST_RESULT` marker.

`test_package` reuses the 6 offline consumer groups proven by
`openldap/2.6.7` (no network, no slapd; links `libldap` + `liblber`):

1. `ldap_create` / `set_option` / `get_option` / `unbind_ext`
2. `LDAP_OPT_API_INFO`
3. `ldap_url_parse` / `free` / `desc2str` / `is_ldap_url`
4. `ldap_str2dn` / `dn2str` / `dnfree`
5. `ldap_err2string`
6. `lber` `ber_alloc_t` / `ber_printf` / `ber_flatten2` / `ber_free`

Evidence markers use dual-channel output (`print(flush=True)` +
`self.output.info`) and the test_package re-emits the persisted
upstream marker every run so Conan cache hits never lose evidence.

## Validation

2026-09-19 preflight evidence: pinning `/bin/sh` + `CONFIG_SHELL` was not
enough — the `pwd` binary itself failed `getcwd` in the conan cache tree,
proving the fault is the HMDFS directory, not the shell choice. The recipe
now probes for a getcwd-healthy directory (injected `TMPDIR`, then the OHOS
native cache), copies the whole source tree there, and runs
configure/make/check/install inside it with `cd <healthy>` as the first
command word plus `CONFIG_SHELL/SHELL` re-asserted per command (E386).
`TMPDIR/TMP/TEMP` point into the healthy base; no third-party bash path is
hardcoded anywhere. CMake consumer names are pinned lowercase
(`find_package(libldap)` + `libldap::ldap`/`libldap::lber`, openldap/2.6.7
precedent) after preflight showed CMakeDeps declares `libldap::libldap`.

Pending HMBS preflight on HarmonyOS aarch64 (native build). Local checks
done in this round: Python syntax compile of both conanfiles, YAML parse
of conandata/MANIFEST/manifest, patch file present, `self.run` literal
present in test_package (PF3 gate), consumer `test.c` calls real
libldap/liblber APIs (R34, no stub).

2026-09-19 OOM mitigation (tar Cannot fork: Out of memory): prefer
disk-backed OHOS cache over TMPDIR tmpfs for the healthy tree, clean
stale libldap-healthy-* dirs, copy via hardlink-preserving helper, and
unlink configure before patching to avoid polluting the Conan cache.
