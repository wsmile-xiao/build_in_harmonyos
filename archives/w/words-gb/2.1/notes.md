# words-gb 2.1 adaptation notes

`words-gb` is the distribution package version. Its immutable input is GNU
Aspell English dictionary release `2017.08.24-0`.

The recipe decodes the documented Aspell prezip (`.cwl`) format without a
host-installed Aspell executable. It merges `en-common.cwl` and all six
`en_GB*.cwl` inputs with bytewise sorting and deduplication, matching the
distribution packaging algorithm. The expected result contains 127466 entries.

The upstream release does not define a test target. The added consumer test
parses the installed list, checks ordering and uniqueness, validates British
spellings, rejects American-only spellings, and exercises a missing-file fault
path.
