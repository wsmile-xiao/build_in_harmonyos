# PCRE2 draft - Restore Autotools helper execute bits before configure

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-13
> **Severity**: medium | **Category**: autotools / conan / OHOS filesystem

## Usage

Use this pattern when an Autotools package fails on HarmonyOS PC because
`configure` or its helper scripts are present but not executable after source
extraction, patch application, or transfer through a filesystem that does not
preserve POSIX mode bits.

## Scope

- Conan recipes that invoke upstream Autotools `configure`.
- Source trees containing `configure`, `config.guess`, `config.sub`,
  `install-sh`, or `missing`.
- HarmonyOS PC or HMDFS-style paths where executable bits can be missing even
  when the file content is correct.

This is not a workaround for a missing script. If the file is absent or
generated incorrectly, regenerate the Autotools files with the upstream
supported bootstrap command instead.

## Symptom

Typical failures appear before compilation starts:

```text
Permission denied
./configure: cannot execute
config.guess: Permission denied
```

Calling `sh configure` can make the top-level script run, but nested helper
scripts can still fail if their execute bits are missing.

## Root Cause

Autotools projects treat several generated helper files as executable programs.
Some HarmonyOS PC adaptation paths unpack or copy sources through environments
that preserve file content but not the executable mode. The build then fails
for filesystem metadata reasons rather than source compatibility reasons.

## Implementation

Before running `configure`, walk the recipe, source, and build folders and add
owner/group/other execute bits to the known Autotools helper scripts:

```python
script_names = {"configure", "config.guess", "config.sub", "install-sh", "missing"}
for root in (self.recipe_folder, self.source_folder, self.build_folder):
    if not root or not os.path.isdir(root):
        continue
    for current, _, files in os.walk(root):
        for name in script_names.intersection(files):
            path = os.path.join(current, name)
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
```

Then run upstream configure through the shell or the normal Autotools helper,
depending on the project:

```python
self.run('sh "{}/configure" {}'.format(self.source_folder, autotools._configure_args))
autotools.make(args=["-j1"])
autotools.make(args=["-j1", "check"])
```

## Forbidden Approaches

- Do not edit generated Autotools script content just to bypass execute-bit
  failures.
- Do not grant executable permissions to every file in the source tree.
- Do not skip upstream tests after changing build-system execution behavior.
- Do not report pending CI placeholders as final pass rates.

## Verification

1. Run a clean Conan build on the HarmonyOS PC CI or target runner.
2. Require `configure` to complete without permission errors.
3. Run the upstream test target, for example `make -j1 check`, and report the
   real pass rate from the CI log.
4. Run the Conan `test_package` consumer and report its pass rate separately.
5. Keep the package version suffix bumped when a previously published recipe
   must be changed.

## Validated Example

PCRE2 10.45.1.1 restores execute bits for the Autotools helper scripts before
running configure. The recipe then builds the static 8/16/32-bit libraries and
executes upstream `make -j1 check` in the build stage. The enabled top-level
suites are `pcre2posix_test`, `RunTest`, and `RunGrepTest`; CI builds #20031,
#20032, #20179, and #20322 passed all three suites (3/3, 100%) and the OHOS
`test_package` consumer (1/1, 100%).
