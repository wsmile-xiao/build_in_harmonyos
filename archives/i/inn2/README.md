# inn2 (InterNetNews)

INN is a complete Usenet news server suite: `innd` (the server), `nnrpd`
(readers), `innfeed` (feeds), the expiry/overview tooling, and the `libinn` /
`libinnhist` / `libinnstorage` libraries that backends link against.

The `2.7.4` recipe builds from the upstream Autotools release with no Conan
package requirements; it links only the OpenHarmony system zlib and libm.

Three portability patches plus one upstream-bug patch are required on
OpenHarmony — the setgid `hmdfs` volume rejecting `umask 077` temporary
directories, the bundled `config.guess`/`config.sub` not knowing HarmonyOS, the
`install-sh -o news -g news` install step finding no `chown`/`chgrp`, and an
invalid `(void(0))` macro in `innfeed/article.c` that only surfaces in Release
builds. See `2.7.4/notes.md` for the full analysis.
