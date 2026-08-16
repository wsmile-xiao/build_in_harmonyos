# acf-openssh 0.11.2 source analysis

## Verified archive

```text
URL: https://distfiles.alpinelinux.org/distfiles/v3.18/acf-openssh-v0.11.2.tar.gz
size: 6429 bytes
sha256: 668be900964b2e42e55c3f921e2d2a1d54ca618583a6681ccaefc01fbf2aa793
release timestamp in archive: 2017-03-01
```

The archive root is `acf-openssh-v0.11.2/` and contains 16 entries including
the root directory. Twelve entries match the Makefile's `openssh*` install
set; the remaining files are `Makefile`, `config.mk`, and `README`.

## Build system

The package uses one hand-written Makefile and `config.mk`:

```make
all:
install:
	mkdir -p "$(DESTDIR)/$(appdir)/openssh"
	cp -a openssh* "$(DESTDIR)/$(appdir)/openssh"
```

`config.mk` sets `prefix=/usr` and `appdir=${prefix}/share/acf/app`. There is
no configure phase, compiler invocation, generated code, or compiled output.
`make -j1 all` is a parse/no-op check; packaging is the substantive operation.

## Installed artifacts

- Lua: `openssh-controller.lua`, `openssh-model.lua`
- Views: config, connected peers, expert, authorized keys, users, logfile,
  status, and welcome LSP files
- Authorization/navigation: `openssh.menu`, `openssh.roles`
- Upstream links: expert, logfile, and status point to acf-core shared views

The target HMDFS storage does not preserve those three dangling links and
rejects explicit symlink creation. The OHOS package therefore uses a no-link
layout: it copies the exact three templates from the declared `acf-core`
dependency into the upstream names. Tests byte-compare the materialized files
with their dependency sources.

The package is a pure application resource bundle. It has no `bin`, `lib`,
headers, or ELF and no command declaration requirement.

## Code-level integration points

The controller delegates status, configuration, connected-peer, user,
authorized-key, and logfile actions to the model. The model:

- reads and writes `/etc/ssh/sshd_config` upstream;
- controls an `sshd` service through acf-core `modelfunctions`;
- enumerates `/home` with `posix.files`;
- parses configuration and validates IP addresses/ports with acf-lib;
- inspects `ps` and `netstat` output for connected peers;
- manages user `authorized_keys` files.

The current `openssh/10.0p1` recipe installs under `usr/local`, including its
configuration directory, so the upstream Alpine config path needs a focused,
environment-driven portability patch. Service control is a separate runtime
limitation because the model assumes Alpine OpenRC commands and init scripts.

## Test analysis

There is no upstream test suite, test directory, test framework, `make check`,
or `make test` target. Validation therefore counts only consumer checks:

1. Verify all twelve packaged resources as regular files on OHOS.
2. Byte-compare the three materialized views with the real acf-core templates.
3. Load real `posix`, `subprocess`, acf-core, and acf-lib modules.
4. Load the controller and verify its default action plus ten action methods.
5. Point the model at a temporary `sshd_config`; verify parsing, validation,
   update, persistence, and the environment-provided path.
6. Keep start/stop and live peer discovery as integration limitations; never
   fake successful OpenRC control on HarmonyOS.

The final suite contains 16 layout checks and 32 Lua checks, for 48 total.
