# libseqlib

C++ htslib/bwa-mem/fermi interface for interrogating sequence data.

## OHOS adaptation

- Autotools recursive build (`bwa`, `htslib`, `fermi-lite`, `src`) with `--host=aarch64-unknown-linux-ohos`.
- Pinned submodule tarballs vendored from official GitHub (tag archive lacks them).
- OHOS configure shims (umask/TMPDIR/uname/install) and HMDFS `ln` hardening, following the proven `htslib/1.24-r0` recipe.
- Upstream 1.2.0 has no `make check` suite; Travis gate is `configure && make`. `seq_test/` holds 53 Boost cases needing external `test_data` absent from the tarball.

## Dependencies

- `zlib/1.3.1`
- `xz/5.6.2`
- `bzip2/1.0.8`

## References

- https://github.com/walaj/SeqLib
