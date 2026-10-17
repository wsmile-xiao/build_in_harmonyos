# libfdisk

libfdisk is the partition-table manipulation library from the util-linux
project: create, read and modify DOS/MBR, GPT, SGI, SUN and BSD disk labels
(`fdisk_new_context` / `fdisk_create_disklabel` / `fdisk_add_partition` /
`fdisk_apply_table` …).

## OHOS adaptation

- Library view of the `util-linux-2.42.3.tar.xz` release (no independent
  tarball): `--disable-all-programs` + `--enable-libfdisk` /
  `--enable-libuuid`, with the required libuuid bundled
  (`libs=["fdisk","uuid"]`).
- Same OHOS guards as the sibling `util-linux/2.42` recipe (same tarball
  family): `config.guess`/`config.sub` recognition, `configure` umask 077
  fix, `TMPDIR` to build folder, `getusershell`/`versionsort` compat headers.
- Runs the 6 upstream C unit binaries (`test_fdisk_ask/gpt/script/utils/
  version/item`, built by `make check` with `--enable-static`) in the recipe
  `build()` and reports real exit-code counts.

## Dependencies

None (libuuid is built and bundled from the same source).

## References

- https://github.com/util-linux/util-linux
- https://www.kernel.org/pub/linux/utils/util-linux/v2.42/
