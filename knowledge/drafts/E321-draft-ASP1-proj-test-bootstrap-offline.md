# E321 draft - Separate test-only bootstrap downloads from an offline package build

> Status: DRAFT | Source: PROJ 9.3.1 PR #3119, commit `aa07e49dd`

## Error signature

Some CMake projects download their test framework during configuration rather
than treating it as an already available build input. A target CI worker then
fails before compiling the production library:

```text
Performing download step (download, verify and extract) for 'googletest'
Using src='https://github.com/google/googletest/archive/release-1.11.0.zip'
Each download failed!
```

In PROJ 9.3.1 this path is activated by `BUILD_TESTING=ON`; the production
library and command-line tools do not require GoogleTest at runtime.

## Diagnosis boundary

This is not a replacement for the general source-download issue in E017. The
primary package source was checksum-pinned and did download in CI. The failure
was caused by an implicit, test-only `ExternalProject` bootstrap during CMake
configure. Retrying the same build leaves package reproducibility dependent on
an unrelated external test-framework service.

It is also not evidence that upstream tests have passed on OpenHarmony. Before
the final recipe change, a target-side attempt reached CTest and reported
`54/56` passing, but its detailed failure output was not retained in the
available CI artifact. That partial result cannot justify a tolerance or test
path patch as a general remedy.

## Recommended repair

When the package contract only requires a production library and its consumer
test, turn off the networked upstream suite in the Conan toolchain:

```python
tc.variables["BUILD_TESTING"] = "OFF"
```

Then keep an executable `test_package` that consumes the installed CMake target
using the generated Conan run environment. The test must exercise representative
public API paths, not merely configure or link an empty executable.

For PROJ, the consumer test covers version information, context lifecycle,
pipeline coordinate transformation, invalid projection rejection, and geodesic
inverse calculation. The local Linux preflight result remains separately
reported as upstream CTest `56/56`; it must not be labelled as an OHOS result.

## Full-suite fallback

If the contribution requires upstream CTest on the target, make the test
framework an explicit, checksummed offline input. Use the project-supported
injection point such as `FETCHCONTENT_SOURCE_DIR_*`, or an approved packaged
test dependency. Only then report the exact target CTest numerator and
denominator alongside the consumer test result.

## Related knowledge, not new entries

- E017 covers external source download instability. This draft distinguishes a
  hidden test bootstrap from the package's declared source URL.
- E217 covers how to layer and truthfully report large upstream CTest suites.
- E221 covers executing a Conan consumer test under its generated runtime
  environment.
- E224 covers correct routing of CTest options through Conan CMake helpers.
- E011 covers supplying a writable temporary directory to an upstream test; it
  does not make a configure-time test framework download reproducible.
- E018/E050 already cover replacing filesystem-hostile symbolic links with a
  wrapper or copy. PROJ's `invproj` and `invgeod` build aliases are an
  additional executable-alias instance of that existing rule, not a new rule.

## Prohibited reporting

- Do not call `BUILD_TESTING=OFF` a full upstream-test pass.
- Do not merge the local host `56/56` with target CI consumer-test results.
- Do not suppress the bootstrap download failure with `|| true` or an unchecked
  mirror URL.
- Do not disable the upstream suite without retaining a real consumer test.
