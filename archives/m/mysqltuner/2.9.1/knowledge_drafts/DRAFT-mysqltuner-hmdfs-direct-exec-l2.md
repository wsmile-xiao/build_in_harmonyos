# DRAFT-mysqltuner-hmdfs-direct-exec-l2 - hmdfs package cache can make direct CLI smoke non-blocking while runenv Perl succeeds

- Trigger event: mysqltuner 2.9.1 shadow CI L2
- Path: Path B knowledge extension
- Phase: L2 smoke test / consumer verification

## Symptom

Shadow CI completed successfully, but L2 reported a non-blocking skip:

```text
[warn] L2: mysqltuner --version/--help failed (non-blocking)
[warn] L2: mysqltuner.pl --version/--help failed (non-blocking)
```

Manual probing of the packaged file showed:

```text
-rwxr-x--- ... p/bin/mysqltuner
sh: .../p/bin/mysqltuner: Permission denied
```

Explicit Perl execution under the generated Conan run environment succeeded:

```text
perl <package>/bin/mysqltuner --help
```

## Root Cause

The package files are stored under the user's hmdfs-backed Conan cache. The
file mode is executable, but direct execution from that storage path returned
permission denied in the manual device session. For Perl scripts, direct CLI
smoke also depends on the script shebang and the Perl package's relocated
`PERL5LIB` environment.

## Fix

Treat direct L2 smoke as a useful but non-blocking signal for this package.
Make the real consumer check explicit and environment-correct:

```python
self.run(f'"{python}" "{test_script}" "{dep.package_folder}" "{perl}"', env="conanrun")
```

The Python test then invokes the packaged script through the packaged Perl
interpreter, after Conan VirtualRunEnv has supplied `PATH` and `PERL5LIB`.

## Verification

`test_package` executed successfully in shadow CI. L1e then moved `bin/` away
and confirmed the negative test failed, proving the consumer test depends on
the packaged mysqltuner binary and is not a stub.

## Reuse

For script packages in an OHOS hmdfs Conan cache, do not rely solely on direct
`<tool> --help` as proof of package usability. Add a consumer test that invokes
the script through its interpreter with the generated Conan run environment.
