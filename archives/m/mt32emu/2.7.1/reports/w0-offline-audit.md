# mt32emu 2.7.1 W0 offline audit

## Source evidence

- Official tag: `libmt32emu_2_7_1`
- Commit: `6d68fbb84b018df495fafa3e154e4ba1ffbfd0df`
- Official archive URL:
  `https://codeload.github.com/munt/munt/tar.gz/refs/tags/libmt32emu_2_7_1`
- Archive bytes: `583822`
- Archive SHA-256:
  `e4524d52d6799a4e32a961a2e92074f14adcb2f110a4e7a06bede77050cfdaf4`
- Archive entries: `343`
- Archive roots: one, `munt-libmt32emu_2_7_1`
- Unsafe archive member paths: `0`

The source declares version 2.7.1 in
`mt32emu/cmake/project_data.cmake`. The core tree contains 91 files, of
which 75 are C/C++ source or headers and 6 are CMake files.

## Dependency result

The default internal resampler is enabled at `mt32emu/CMakeLists.txt:43` and
selected at lines 249-258. The external branch prefers SOXR 0.1.2 at lines
260-270 and tries SampleRate 0.1.8 only in the SOXR fallback at lines 271-282.
The recipe therefore has no third-party library requirement under its chosen
default configuration.

## Registered-test result

The following PowerShell logic was run across all core `CMakeLists.txt` and
`*.cmake` files:

```powershell
$files = Get-ChildItem mt32emu -Recurse -File |
  Where-Object { $_.Name -eq 'CMakeLists.txt' -or $_.Extension -eq '.cmake' }
$hits = $files | Select-String -CaseSensitive:$false `
  -Pattern 'enable_testing\s*\(|include\s*\(\s*CTest|BUILD_TESTING|add_test\s*\('
```

Observed result: `6` CMake files and `0` registration hits. There are also
zero test-named files or directories in the 91-file core tree. The upstream
registered-test count is therefore 0, not an unknown value and not a count of
source assertions or helpers.

## Boundaries

- This report does not claim an OHOS package build or device execution.
- The consumer test is one independent installed-package flow.
- Full synthesis requires user-supplied compatible control and PCM ROM images;
  no ROM content is included or assumed.
