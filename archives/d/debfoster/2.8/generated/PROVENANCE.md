# `generated/` — provenance of the restored autotools helper files

`debfoster_2.8.orig.tar.xz` is produced by `make dist`, and the upstream
`Makefile.am` `dist-hook` deletes the generated helper files from the
distribution directory while keeping `configure` and the per-directory
`Makefile.in`:

```make
dist-hook:
	rm -f $(distdir)/autom4te.cache
	rm -f $(distdir)/config.guess*
	rm -f $(distdir)/config.sub*
	rm -f $(distdir)/aclocal.m4
	rm -f $(distdir)/missing
	rm -f $(distdir)/install-sh
	rm -f $(distdir)/depcomp
```

Debian regenerates them at build time with `dh_autoreconf`. That is not
possible here: regenerating would need `autoconf`, `automake`, gettext's
`autopoint` **and** autoconf-archive (`configure.ac` uses `AX_CFLAGS_WARN_ALL`,
which the tree does not ship), and neither the device nor the CI worker has an
autotools toolchain. The tarball's own `autogen.sh` is a stale template that
still looks for `configure.in`.

The files below are therefore restored as ordinary recipe sources and copied
into the source tree by `source()`. Only `config.guess` is modified.

| file | origin | sha256 |
| --- | --- | --- |
| `config.guess` | automake 1.18.1 copy (`timestamp='2024-07-27'`), **patched** for HarmonyOS | `cb602d841844af4eda822780944e88e5f1173bdeb0102fc30f91beee861a884d` |
| `config.sub` | automake 1.18.1 copy, verbatim (`timestamp='2024-05-27'`) | `11c54f55c3ac99e5d2c3dc2bb0bcccbf69f8223cc68f6b2438daa806cf0d16d8` |
| `install-sh` | automake 1.18.1 copy, verbatim | `776876b3909b096439109a4c7642eb0f9100f6ba3fb42fa93d05351e50a0a7ef` |
| `missing` | automake 1.18.1 copy, verbatim | `4f17c4a66ec5b8000d44573a576f6b5d9c0c84848e8fd1286f84a52f439db4e9` |
| `depcomp` | automake 1.18.1 copy, verbatim | `ac3ae010382a83144ff6ec1c4a368a3f16a14ea2b12751aa73ddfb548d931574` |
| `aclocal.m4` | **placeholder written for this recipe**, see its own header | `b107acdf6138b9ec0b46511913febd9fdcc73b74364fda1f9f43c0abbb72dd12` |

## `config.guess`

The 2024-07-27 script only recognises `uname -s` values of `Linux` or `GNU`;
HarmonyOS reports `HarmonyOS`, so the upstream script aborts with

```
config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```

The patch adds the same `*:HarmonyOS:*:*` branch used by the other packages in
this repository, inserted immediately before the

```
# Note: order is significant - the case branches are not exclusive.
```

comment, so it takes precedence over the generic `*:Linux:*:*` probes:

```sh
case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in
    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64) MACHINE=aarch64 ;;
	    armv7*|armv8*) MACHINE=arm ;;
	    x86_64|amd64)  MACHINE=x86_64 ;;
	    i?86)          MACHINE=i686 ;;
	    *)             MACHINE="$UNAME_MACHINE" ;;
	esac
	GUESS=${MACHINE}-unknown-linux-ohos
	;;
esac
```

Measured on the device: `sh ./config.guess` → `aarch64-unknown-linux-ohos`.
`config.sub` in this vintage already accepts the canonical `ohos` OS component
(`config.sub aarch64-unknown-linux-ohos` → `aarch64-unknown-linux-ohos`), so it
is shipped verbatim.

## `aclocal.m4`

See the header comment inside the file. It exists only because the
automake-generated Makefiles declare `$(ACLOCAL_M4): $(am__aclocal_m4_deps)`;
without the file `make` runs `missing aclocal-1.16` and dies with exit 127. It
is an input of `autoconf` alone, and the recipe pins every autotools input and
product to one identical mtime, so no maintainer rule ever fires and the file
is never read.
