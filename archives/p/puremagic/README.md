# puremagic

`puremagic` is a pure Python file type identification library. This archive
contains the Conan recipe and versioned OpenHarmony PC adaptation for 2.2.0.

The task board currently labels task #9814 as `cpp`; the upstream source is
Python and the contribution materials disclose that eligibility mismatch.
No task label or framework language gate is changed here.

See `2.2.0/notes.md` for the fixed source, recipe design, and validation
evidence. The H1 #004 candidate passed one OHOS aarch64 `conan create` and its
four-scenario package consumer. The package reference is
`puremagic/2.2.0#589899285f20ac01d1e8b745fe341981:da39a3ee5e6b4b0d3255bfef95601890afd80709#c915ed033e4e2c47150dd52bc063037c`.
H1 #003's upstream 95/95 and W3 results apply to the earlier recipe revision;
the revised candidate has not rerun G1, W3, full `finish`, or official CI.
H1 #003's G0 log reports that the original tarball was not found at the
expected location. Separately, inventory of the fixed sdist shows no
`configure` or Makefile; that source-shape observation does not replace or
reinterpret the logged G0 result.
