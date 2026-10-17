# mpgtx

mpgtx is a command-line MPEG toolbox: it splits, joins, demultiplexes and
fetches detailed information about MPEG audio/video/system streams, and
edits ID3v1 tags (`tagmp3`). The single `mpgtx` binary multiplexes its
behavior on `argv[0]` (`mpgjoin`, `mpgcat`, `mpgsplit`, `mpginfo`,
`mpgdemux`, `tagmp3` are symlinks to it).

## Upstream

- Homepage: https://mpgtx.sourceforge.net/
- Releases: https://sourceforge.net/projects/mpgtx/files/ (SourceForge is
  the only official distribution channel; there is no upstream git
  repository, only the historical SourceForge CVS)
- 1.3.1 is the final release (2005-01-02, "Happy New Year Release");
  the project has been inactive since.

## OHOS adaptation

- Builds the official release tarball with its hand-written `configure`
  (not autotools) using the OHOS clang++ injected via
  `tools.build:compiler_executables`.
- One minimal portability patch (see `1.3.1/patches/`): honor `CXX`,
  skip the GCC-3.x version probe when gcc is absent, stage via `DESTDIR`
  with `mkdir`/`cp`/`chmod` instead of coreutils `install -s`.
- The upstream release contains no test suite (`make check` / `make test`
  have no rule; Total=0 — evidence in `1.3.1/notes.md`), so verification
  is done by `test_package/`, which runs the installed CLI against a
  programmatically generated MPEG-1 Layer III fixture.

## Dependencies

None — the recipe is dependency-free (pure C++ with no third-party
libraries).

## References

- https://mpgtx.sourceforge.net/
- https://sourceforge.net/projects/mpgtx/
