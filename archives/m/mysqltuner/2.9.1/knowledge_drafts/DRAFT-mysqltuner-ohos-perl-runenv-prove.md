# DRAFT-mysqltuner-ohos-perl-runenv-prove - OHOS Conan Perl package must run prove through perl -S under conanrun

- Trigger event: mysqltuner 2.9.1 HarmonyOS adaptation
- Path: Path B knowledge extension
- Phase: Conan build() upstream TAP execution

## Symptom

`perl -c mysqltuner.pl` passed on the OHOS device, but the next upstream test
command failed:

```text
RUN: prove "tests/cli_options.t" ...
/system/bin/sh: <conan perl package>/bin/prove: No such file or directory
```

Manual reproduction showed that the `prove` script exists, but direct execution
is unreliable because its shebang is `#!//bin/perl`. Running it without the
Conan run environment also fails with:

```text
Can't locate strict.pm in @INC
```

## Root Cause

The published `perl/5.42.2` package is relocatable only when Conan's generated
run environment is applied. Its compiled default `@INC` points at `//lib/...`;
standard modules such as `strict.pm` are found through `PERL5LIB` exported by
`runenv_info`. Directly executing `prove` asks `/system/bin/sh` to honor a bad
absolute shebang, while running `perl <prove>` without `PERL5LIB` cannot load
core modules.

## Fix

In the recipe, keep `VirtualRunEnv` and run upstream TAP tests with an explicit
interpreter lookup:

```python
self.run('perl -c "mysqltuner.pl"', cwd=self.source_folder, env="conanrun")
self.run(f"perl -S prove {tests}", cwd=self.source_folder, env="conanrun")
```

`perl -S prove` uses `PATH` from `conanrun` to locate the packaged `prove`
script, while the same environment provides `PERL5LIB` for the relocated Perl
core modules.

## Verification

On the OHOS shadow-CI device:

- `perl -c mysqltuner.pl` passed.
- `perl -S prove` ran 6 upstream TAP files.
- TAP result: 65 tests, all successful.

## Reuse

For pure Perl CLI packages on OHOS, do not call helper scripts such as `prove`
directly from `self.run()` when they come from the Conan Perl package. Prefer
`perl -S <tool>` with `env="conanrun"` or `env="conanbuild"` as appropriate.
