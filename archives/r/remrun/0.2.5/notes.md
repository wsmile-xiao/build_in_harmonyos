# remrun 0.2.5 adaptation notes

## Upstream source

- Upstream version: `0.2.5`
- Source URL: `https://devel.ringlet.net/files/sys/remrun/remrun-0.2.5.tar.xz`
- SHA-256: `8009b6980f46643db5f5eafe8b38ae0961c8e49d8ba61f8e20bc2d37c8da4fe4`
- Build system: Makefile

## Configuration

`remrun` is a POSIX shell script plus a manpage. The recipe runs:

```text
make SKIP_SHELLCHECK=1 all
```

`SKIP_SHELLCHECK=1` avoids making ShellCheck a package build dependency. The
recipe does not use `make install` because the upstream install target passes
owner and group flags such as `-o root -g root`, which are not appropriate for
Conan package creation. Instead, the generated `remrun` script and compressed
manpage are copied into the package.

The script shebang is changed from `/bin/sh` to `/usr/bin/env sh` so it does
not depend on a fixed `/bin/sh` path.

The software-level `archives/r/remrun/commands.json` declares the packaged
`remrun` command for the repository command registry. It uses `type: tool` and
`binary: false` because the installed executable is a POSIX shell script rather
than a compiled binary.

## Upstream tests

`tests/test-data/tests.json` defines 14 upstream SSH functional scenarios:

1. Fail with a nonexistent local file.
2. Do not run `whoami` on the remote host in noop mode.
3. Run `whoami` on the remote host.
4. Fail with mismatched local checksum command.
5. Fail with mismatched remote checksum command.
6. Use the same non-default checksum command on both sides.
7. Run `wc` on an empty stream.
8. Run `wc` on a non-empty stream.
9. Run a script that fails.
10. Run a script read from standard input.
11. Reject `-s` with `-` as the filename.
12. Pass one argument to the remote program.
13. Pass no argument to the remote program.
14. Reject an unsupported argument combination.

The full upstream suite is executed by `make test` and requires an sshd-backed
functional test environment. It was run in a Linux Docker container with
`openssh-client` and `openssh-server` installed. The upstream harness exercised
the same 14 scenarios in both default-home and explicit-remote-temp modes, and
all scenarios passed.

The Rust workspace under `rust/generate-tests/` is a test-generation helper,
not a build requirement for the packaged shell script.

## test_package

`test_package/test_remrun.sh` performs six offline CLI checks:

1. `remrun --version`
2. `remrun --features`
3. `remrun --help`
4. Invalid long option rejection.
5. Nonexistent local file rejection before any SSH call.
6. `-s` plus `-` filename rejection before any SSH call.

These checks verify that the script is installed, executable, and able to
handle local argument/validation paths without requiring a remote SSH service.

## Local evidence

Completed local checks for this candidate:

```text
static_recipe_check.py ... passed: true
conan source .: Sources correctly downloaded from https://devel.ringlet.net/files/sys/remrun/remrun-0.2.5.tar.xz
conan export .: Exported remrun/0.2.5
conan graph info . --profile Linux ...: graph resolved with no Conan dependencies
make SKIP_SHELLCHECK=1 test with OpenSSH service dependencies: 14/14 upstream SSH scenarios passed
conan create archives/r/remrun/0.2.5 -s build_type=Release --build=missing: passed
test_package/test_remrun.sh: 6/6 offline CLI checks passed; output `remrun test: OK`
```

The upstream `make test` log is kept at
`F:\jifensai\.tmp\remrun-upstream-make-test-20260730-2.log` for local evidence.
The Conan `create` log is kept at
`F:\jifensai\.tmp\remrun-conan-create-20260730.log`. Conan validation is
performed separately from the upstream SSH suite because that suite needs an
active sshd test environment, while the Conan recipe itself should not add
OpenSSH server or ShellCheck as package build dependencies.
