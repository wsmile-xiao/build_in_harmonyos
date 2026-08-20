# libsndfile 1.2.2 W0 report

Date: 2026-08-17
Issue: AtomGit #31

The minimal CMake build disables the optional FLAC, Vorbis, Ogg, Opus, mpg123,
and LAME integrations, so it has no Conan runtime or build requirements.

The target check used:

```sh
conan download libsndfile/1.2.2 -r=ohpcd --only-recipe
```

The command returned exit code 1 with `system acceleration policy not enabled`.
The same configured remote downloaded published recipes during the parent abx
W0 check, so this is the remote's missing-package response. The target reference
was unoccupied at check time.
