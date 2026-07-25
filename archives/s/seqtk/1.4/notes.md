# seqtk 1.4 OpenHarmony adaptation

- Upstream: https://github.com/lh3/seqtk
- Source archive: https://github.com/lh3/seqtk/archive/refs/tags/v1.4.tar.gz
- License: MIT
- Build system: the upstream Makefile invokes the C compiler directly.
- Dependency: zlib 1.3.1 provides `zlib.h` and `libz`.
- The upstream Makefile hard-codes `-lz`; the recipe adds Conan zlib library
  directories to the compiler command so the packaged library is selected.
- Package output: `bin/seqtk` and `licenses/LICENSE`.
- OHOS packaging removes an existing `.codesign` section and uses the worker's
  `binary-sign-tool` by default. A WSL cross-build can set the `sign_tool` key
  in `tools.build:compiler_executables` to an empty value to validate compilation and
  packaging without claiming a worker-issued signature.
- Validation: the test package converts a FASTQ record to FASTA and checks the
  the resulting sequence and the `seqtk size` record-count output.
