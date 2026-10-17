#!/usr/bin/env python3
"""Conan recipe — xidle 20200802 (X11 idle/edge-sensitive action launcher)

Build system: BSD bmake + bsd.prog.mk (upstream), unavailable on HarmonyOS.
This recipe builds xidle directly with clang, linking against the
pre-installed X11 libraries (libXss, libXext, libX11).

Approach mirrors the Debian/rules build:
  - compile xidle.c   with -DNEED_STRTONUM -DMBSDPORT_H=\"ports/ohos-mbsdport.h\"
  - compile strtonum.c
  - link both objects against -lXss -lXext -lX11

The portability header (ports/ohos-mbsdport.h) is generated in source()
and provides __RCSID, __dead, __progname (aliased to musl's
program_invocation_short_name) and the strtonum forward declaration.

The X11 dev headers (Xlib.h, Xresource.h, scrnsaver.h and their
transitive deps X.h, Xfuncproto.h, Xosdefs.h, keysym.h, keysymdef.h,
Xatom.h, saver.h, Xutil.h) are *vendored* into the source tree under
X11/ in source(). This is necessary because the HarmonyOS PC preflight
environment does not pre-install X11 dev headers under any of the
standard candidate prefixes ($HOME/usr/local, /usr, /usr/local,
/usr/X11R6) — the previous prefix-probing approach therefore raised
ConanException at build time. The vendored headers come verbatim from
upstream libX11 1.8.4, xorgproto 2024.1 and libXss 1.2.3 (the same
releases shipped by cmd-pkgs) so they match the installed .so libraries'
ABI. xidle.c calls many real Xlib APIs (XOpenDisplay, XCreateWindow,
XrmParseCommand, XScreenSaverQueryExtension, ...) so the headers cannot
be stubbed — they must be the genuine upstream declarations.

The X11 libraries (libXss.so, libXext.so, libX11.so) are still resolved
from the system pre-install; we only vendor headers, not libraries.

Upstream: Debian native package
  https://deb.debian.org/debian/pool/main/x/xidle/
License: BSD-2-Clause (see xidle.c header)
Homepage: https://www.mirbsd.org/xidle.htm
"""
import io
import os
import ssl
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    get,
    copy,
    download,
    apply_conandata_patches,
    export_conandata_patches,
)


class XidleConan(ConanFile):
    name = "xidle"
    version = "20200802"
    description = "Run program after inactivity or on edge-sensitive mouse motion"
    license = "BSD-2-Clause"
    homepage = "https://www.mirbsd.org/xidle.htm"
    url = "https://deb.debian.org/debian/pool/main/x/xidle/"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 libs (libXss, libXext, libX11) come from the system pre-install
        # (cmd-pkgs), not from Conan dependencies.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Generate HarmonyOS portability header (mirrors debian/mbsdport.h
        # verbatim — upstream does NOT define __progname; xidle.c declares
        # `extern char *__progname;` and relies on the libc to provide the
        # symbol). musl (HarmonyOS libc) does not provide __progname, nor
        # any glibc extension like program_invocation_short_name; so we keep
        # __progname an external symbol here and supply it ourselves via a
        # constructor shim (ohos-progname.c) generated below. Defining
        # __progname as a macro alias to program_invocation_short_name (the
        # glibc symbol) was the earlier approach — it produced ld.lld
        # "undefined symbol: program_invocation_short_name" because musl has
        # no such symbol either.
        ports_dir = os.path.join(self.source_folder, "ports")
        os.makedirs(ports_dir, exist_ok=True)
        with open(os.path.join(ports_dir, "ohos-mbsdport.h"), "w") as f:
            f.write(
                "#ifndef _OHOS_MBSDPORT_H_\n"
                "#define _OHOS_MBSDPORT_H_\n"
                "#ifndef __RCSID\n"
                "#define __RCSID(x) static const char __rcsid[] __attribute__((__used__)) = x\n"
                "#endif\n"
                "#ifndef __dead\n"
                "#define __dead __attribute__((__noreturn__))\n"
                "#endif\n"
                "#ifdef NEED_STRTONUM\n"
                "extern long long strtonum(const char *, long long, long long, const char **);\n"
                "#endif\n"
                "#endif\n"
            )
        # musl has no __progname (BSD libc global) nor any program_invocation*
        # extension; supply the symbol ourselves. A __constructor__ runs
        # before main(), reads /proc/self/cmdline (argv[0]) and stores its
        # basename into __progname, matching BSD libc semantics. Falls back
        # to the literal "xidle" if cmdline is unreadable. xidle.c itself
        # declares `extern char *__progname;` so providing the definition
        # satisfies the link; the constructor ensures it is non-empty by
        # the time any xidle function reads it.
        with open(os.path.join(ports_dir, "ohos-progname.c"), "w") as f:
            f.write(
                "#include <string.h>\n"
                "#include <unistd.h>\n"
                "#include <fcntl.h>\n"
                "char *__progname = (char *)\"xidle\";\n"
                "__attribute__((constructor)) static void _ohos_init_progname(void) {\n"
                "    static char buf[4096];\n"
                "    int fd = open(\"/proc/self/cmdline\", O_RDONLY | O_CLOEXEC);\n"
                "    if (fd < 0) return;\n"
                "    ssize_t n = read(fd, buf, sizeof(buf) - 1);\n"
                "    close(fd);\n"
                "    if (n <= 0) return;\n"
                "    buf[n] = '\\0';\n"
                "    char *base = strrchr(buf, '/');\n"
                "    __progname = (base && base[1]) ? (base + 1) : buf;\n"
                "}\n"
            )
        # Vendor the X11 dev headers into the source tree under X11/. The
        # vendored headers are pulled verbatim from the upstream libX11
        # 1.8.4, xorgproto 2024.1 and libXss 1.2.3 source archives (same
        # releases shipped by cmd-pkgs) so they match the installed .so
        # libraries' ABI. See conandata.yml `x11_headers` for provenance.
        self._vendor_x11_headers()

    # ---- vendored X11 dev headers --------------------------------------------
    # The HarmonyOS PC preflight environment does not pre-install X11 dev
    # headers under any standard prefix, so we vendor the genuine upstream
    # headers and let xidle.c #include <X11/...> resolve against them.
    def _vendor_x11_headers(self):
        x11_cfg = self.conan_data.get("x11_headers") or []
        if not x11_cfg:
            raise ConanException(
                "conandata.yml: 'x11_headers' missing — cannot vendor X11 dev headers"
            )
        for entry in x11_cfg:
            name = entry["name"]
            strip_root = entry["strip_root"]
            files = entry["files"]
            # Download the source archive verbatim into a scratch dir under
            # the source tree. Conan's `get` helper auto-extracts archives
            # (so it would not leave a single file behind), whereas
            # `download` writes the raw bytes to destination/<filename>,
            # letting us then extract only the needed headers via tarfile.
            scratch = os.path.join(self.source_folder, ".x11-src", name)
            os.makedirs(scratch, exist_ok=True)
            filename = entry["url"].rsplit("/", 1)[-1]
            download(
                self,
                entry["url"],
                os.path.join(scratch, filename),
                sha256=entry["sha256"],
            )
            downloaded = [
                os.path.join(scratch, f)
                for f in os.listdir(scratch)
                if os.path.isfile(os.path.join(scratch, f))
            ]
            if len(downloaded) != 1:
                raise ConanException(
                    "vendored X11 headers '{}': expected 1 downloaded archive in {}, found {}".format(
                        name, scratch, downloaded
                    )
                )
            # Extract only the needed headers into the source tree's X11/
            # directory, stripping the archive's top-level dir (strip_root).
            # Some archives also carry build-critical source we must vendor
            # (cmd-pkgs ships no prebuilt libXss, so we compile libXss.so.1
            # ourselves from src/XScrnSaver.c — see _build_libxss). Such
            # entries list `src_files` in conandata.yml; extract those
            # verbatim into X11-src/<name>/ beside the vendored headers.
            src_files = entry.get("src_files") or []
            with tarfile.open(downloaded[0], "r:*") as tf:
                members = []
                for wanted in files:
                    # tarfile stores member paths with forward slashes, so
                    # build the lookup key the same way (do not use
                    # os.path.join, which would emit "\" on Windows).
                    member_path = strip_root + "/" + wanted
                    try:
                        members.append(tf.getmember(member_path))
                    except KeyError:
                        raise ConanException(
                            "vendored X11 headers '{}': {} not in archive {}".format(
                                name, member_path, downloaded[0]
                            )
                        )
                # Extract members into the source tree without their
                # strip_root prefix so the result is X11/<header>.
                for m in members:
                    rel = m.name
                    if rel.startswith(strip_root + "/"):
                        rel = rel[len(strip_root) + 1:]
                    elif rel.startswith(strip_root):
                        rel = rel[len(strip_root):]
                    # All entries under include/ — drop that prefix so the
                    # headers land at X11/... (matching #include <X11/...>).
                    if rel.startswith("include/"):
                        rel = rel[len("include/"):]
                    rel_parts = [p for p in rel.split("/") if p]
                    dst = os.path.join(self.source_folder, *rel_parts)
                    if m.isdir():
                        os.makedirs(dst, exist_ok=True)
                        continue
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with tf.extractfile(m) as src_f, open(dst, "wb") as dst_f:
                        dst_f.write(src_f.read())
                # Extract any src_files verbatim into X11-src/<name>/,
                # preserving the upstream path inside the archive so
                # _build_libxss can locate XScrnSaver.c reproducibly.
                for wanted_src in src_files:
                    member_path = strip_root + "/" + wanted_src
                    try:
                        m = tf.getmember(member_path)
                    except KeyError:
                        raise ConanException(
                            "vendored X11 src '{}': {} not in archive {}".format(
                                name, member_path, downloaded[0]
                            )
                        )
                    rel = m.name
                    if rel.startswith(strip_root + "/"):
                        rel = rel[len(strip_root) + 1:]
                    elif rel.startswith(strip_root):
                        rel = rel[len(strip_root):]
                    rel_parts = [p for p in rel.split("/") if p]
                    dst = os.path.join(self.source_folder, "X11-src", name, *rel_parts)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with tf.extractfile(m) as src_f, open(dst, "wb") as dst_f:
                        dst_f.write(src_f.read())
            # Clean up the downloaded archive to keep the source tree lean.
            try:
                os.remove(downloaded[0])
                os.rmdir(scratch)
            except OSError:
                pass
        # Sanity check: the closure must include the headers xidle.c
        # directly #includes.
        for required in ("X11/Xlib.h", "X11/Xresource.h", "X11/extensions/scrnsaver.h"):
            if not os.path.isfile(os.path.join(self.source_folder, required)):
                raise ConanException(
                    "vendored X11 headers incomplete: {} missing after extraction".format(required)
                )

    # ---- X11 library installation + discovery -----------------------------
    # The HarmonyOS PC preflight environment is clean: the cmd-pkgs
    # pre-built X11 runtime libraries (libX11/libXext/libXss) are NOT
    # pre-installed under any candidate prefix. _ensure_x11_libs fetches
    # them verbatim from the canonical cmd-pkgs release into ~/usr/local
    # (the prefix autocutsel/xclip use and that cmd-pkgs' install.sh
    # defaults to). _x11_dirs then probes a de-duplicated candidate list.
    def _ensure_x11_libs(self):
        """Install libX11/libXext from cmd-pkgs if missing.

        cmd-pkgs package naming/version follow the upstream releases:
          libx11 6.4.0, libxext 6.4.0. libXss is NOT shipped by cmd-pkgs
        at all (no version), so it is built from source by _build_libxss
        instead of fetched here.
        The tarballs are flat (bin/ lib/ share/ at top level), so a plain
        tarfile.extractall into the prefix is sufficient.
        """
        home = os.path.expanduser("~")
        if not home or home == "~":
            return
        prefix = os.path.join(home, "usr", "local")
        lib_dir = os.path.join(prefix, "lib")
        # (cmd-pkgs name, version, sentinel .so we look for in lib_dir)
        pkgs = [
            ("libx11", "6.4.0", "libX11.so.6"),
            ("libxext", "6.4.0", "libXext.so.6"),
        ]
        missing = [
            (n, v, s) for n, v, s in pkgs
            if not os.path.exists(os.path.join(lib_dir, s))
        ]
        if not missing:
            return
        # Use the default TLS context (full certificate verification) so a
        # tampered CDN or MITM cannot silently replace the prebuilt .so. The
        # cmd-pkgs tarballs are trusted release assets of
        # OpenHarmonyPCDeveloper/cmd-pkgs; sha256 pinning of arbitrary
        # prebuilt binaries is out of scope here (no upstream-published
        # binary checksums exist), so transport integrity is what we enforce.
        ctx = ssl.create_default_context()
        os.makedirs(prefix, exist_ok=True)
        prefix_abs = os.path.realpath(prefix)
        for name, ver, sentinel in missing:
            url = (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                f"download/pkgs/{name}-{ver}-ohos-aarch64.tar.gz"
            )
            self.output.info(f"Fetching cmd-pkgs {name} {ver} from {url}")
            try:
                req = urllib.request.urlopen(url, context=ctx, timeout=180)
                data = req.read()
                tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
                # Guard against path-traversal (e.g. members containing "../")
                # by validating every member resolves inside prefix before
                # extraction.
                for m in tf.getmembers():
                    target = os.path.realpath(os.path.join(prefix, m.name))
                    if not (target == prefix_abs
                            or target.startswith(prefix_abs + os.sep)):
                        tf.close()
                        raise ConanException(
                            "cmd-pkgs {}: unsafe tar member path: {}".format(
                                name, m.name
                            )
                        )
                tf.extractall(prefix)
                tf.close()
                self.output.info(f"  installed {name} {ver} into {prefix}")
            except Exception as e:
                # Network/CDN failures are non-fatal here — _x11_dirs will
                # raise a precise diagnostic if the libs are still missing.
                self.output.warning(f"  cmd-pkgs fetch of {name} {ver} failed: {e}")

    def _build_libxss(self, x11_lib_dir):
        """Build libXss.so.1 ourselves from the vendored upstream source.

        cmd-pkgs (OpenHarmonyPCDeveloper/cmd-pkgs) ships no prebuilt libXss
        at all — neither 1.2.0 nor 1.2.3 — so the runtime libXss.so.1 the
        xidle link line needs (-lXss) cannot be fetched. We instead compile
        the single-file implementation src/XScrnSaver.c (vendored verbatim
        from the upstream libXss 1.2.3 source archive in source()) into a
        shared library and install it into ~/usr/local/lib beside the
        cmd-pkgs libX11/libXext.

        XScrnSaver.c's transitive X11 *internal* headers (Xlibint.h,
        extensions/Xext.h, extensions/extutil.h, extensions/saverproto.h,
        extensions/saver.h) are all shipped inside the cmd-pkgs libx11-6.4.0
        tarball under include/X11/..., so we point -I at that prefix once
        libx11 is installed; only scrnsaver.h (the public API header) is
        vendored from the libXss source tree in _vendor_x11_headers.

        x11_lib_dir: the discovered lib dir holding libX11.so/libXext.so
        (passed in from _x11_dirs so we reuse the same candidate prefix).
        """
        home = os.path.expanduser("~")
        if not home or home == "~":
            raise ConanException(
                "cannot resolve $HOME to install self-built libXss.so.1"
            )
        prefix = os.path.join(home, "usr", "local")
        lib_dir = os.path.join(prefix, "lib")
        inc_dir = os.path.join(prefix, "include")
        sentinel = os.path.join(lib_dir, "libXss.so.1")
        if os.path.exists(sentinel):
            return
        src_c = os.path.join(self.source_folder, "X11-src", "libxss", "src", "XScrnSaver.c")
        if not os.path.isfile(src_c):
            raise ConanException(
                "vendored libXss source missing: {} — did _vendor_x11_headers "
                "extract src_files?".format(src_c)
            )
        # The cmd-pkgs libx11 tarball flattens its headers to include/X11/...
        # under the prefix; XScrnSaver.c #includes <X11/Xlibint.h> etc. so a
        # single -I<prefix>/include resolves them. scrnsaver.h is vendored
        # into the source tree's X11/ alongside the other vendored headers,
        # so also pass -I<source>/X11-src/libxss/include is unnecessary —
        # the source tree's own X11/ (from _vendor_x11_headers) already
        # provides scrnsaver.h and is searched via -I<source>.
        if not os.path.isdir(inc_dir):
            raise ConanException(
                "X11 dev headers not installed under {} (cmd-pkgs libx11 "
                "fetch failed); cannot compile libXss. Set DEFAULT_PREFIX.".format(inc_dir)
            )
        os.makedirs(lib_dir, exist_ok=True)
        cc = self._cc()
        cflags = os.environ.get("CFLAGS", "")
        # Compile XScrnSaver.c → libXss.so.1. -fPIC + -shared for a shared
        # lib; link against the already-installed libX11/libXext (sonames
        # libX11.so.6/libXext.so.6 from cmd-pkgs). -Wl,-soname makes the
        # NEEDED entry match what xidle's link line expects (libXss.so.1).
        build_cmd = (
            f'{cc} -Wall -Wextra -fPIC -shared '
            f'-I{inc_dir} '
            f'-I{self.source_folder} '
            f'{cflags} '
            f'{src_c} '
            f'-L{lib_dir} -lXext -lX11 '
            f'-Wl,-soname,libXss.so.1 '
            f'-o {sentinel}'
        )
        self.output.info(f"Building libXss.so.1 from vendored source: {build_cmd}")
        self.run(build_cmd, cwd=self.source_folder)
        # ld.so resolves -lXss via libXss.so → libXss.so.1 symlink. cmd-pkgs
        # prebuilts ship both the sonamed file and the linker symlink; mirror
        # that so the xidle link line (-lXss) finds it under -L<lib_dir>.
        so_link = os.path.join(lib_dir, "libXss.so")
        try:
            if os.path.lexists(so_link):
                os.remove(so_link)
            os.symlink("libXss.so.1", so_link)
        except OSError as e:
            self.output.warning(f"  failed to create libXss.so symlink: {e}")
        if not os.path.exists(sentinel):
            raise ConanException(
                "self-built libXss.so.1 missing after compile command"
            )

    def _x11_dirs(self):
        src = self.source_folder
        inc_root = src
        if not os.path.isfile(os.path.join(src, "X11", "Xlib.h")):
            raise ConanException(
                "vendored X11/Xlib.h missing in source tree {}; did _vendor_x11_headers run?".format(src)
            )
        # cmd-pkgs installs the X11 runtime libraries under ~/usr/local/lib
        # (autocutsel/xclip precedent; cmd-pkgs install.sh defaults to
        # $HOME/usr/local). $DEFAULT_PREFIX is the broader cmd-pkgs root but
        # on the preflight host it coincides with /storage/Users/currentUser/usr/local.
        # We prefer os.path.expanduser("~") over the HOME env var because the
        # HarmonyOS preflight environment may not export HOME to the conan
        # subprocess (observed: candidate list missing the $HOME/usr/local
        # entry entirely). expanduser falls back to the passwd entry when HOME
        # is unset, so it still resolves /storage/Users/currentUser on OHOS.
        home = os.path.expanduser("~")
        default_prefix = os.environ.get("DEFAULT_PREFIX", "")
        x11_lib_names = ("libX11.so", "libX11.so.6", "libX11.a")
        # De-duplicated candidate prefixes, highest priority first.
        seen = set()
        cands = []
        def _add(p):
            if p and p not in seen:
                seen.add(p)
                cands.append(p)
        if home and home != "~":
            _add(os.path.join(home, "usr", "local"))
        if default_prefix:
            _add(default_prefix)
        _add("/storage/Users/currentUser/usr/local")
        _add("/usr")
        _add("/usr/local")
        _add("/usr/X11R6")
        lib_root = ""
        for p in cands:
            lib_dir = os.path.join(p, "lib")
            if os.path.isdir(lib_dir) and any(
                os.path.exists(os.path.join(lib_dir, name))
                for name in x11_lib_names
            ):
                lib_root = lib_dir
                break
        if not lib_root:
            raise ConanException(
                "X11 libraries (libXss/libXext/libX11) not found under any candidate "
                "prefix ({}); set DEFAULT_PREFIX to the cmd-pkgs install root.".format(
                    ", ".join(cands)
                )
            )
        return inc_root, lib_root

    def _cc(self):
        # Prefer HMBS-injected compiler when available, then CC env, then PATH.
        execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return execs.get("c") or os.environ.get("CC") or "clang"

    def build(self):
        apply_conandata_patches(self)
        # The preflight environment is clean: cmd-pkgs X11 runtime libs
        # are not pre-installed. Fetch them into ~/usr/local before probing.
        self._ensure_x11_libs()
        x_includes, x_libraries = self._x11_dirs()
        # cmd-pkgs ships no prebuilt libXss (verified: the pkgs release has
        # 2193 assets, none named libxss), so -lXss would fail at link time
        # (observed: ld.lld: error: unable to find library -lXss). Build it
        # ourselves from the vendored upstream source into ~/usr/local/lib
        # before the link step. Pass the discovered lib dir so _build_libxss
        # reuses the same candidate prefix as _x11_dirs.
        self._build_libxss(x_libraries)

        cc = self._cc()
        cflags = os.environ.get("CFLAGS", "")
        ldflags = os.environ.get("LDFLAGS", "")

        src = self.source_folder
        mbsdport = '-DMBSDPORT_H=\\"ports/ohos-mbsdport.h\\"'

        # Compile xidle.c with the same defines Debian/rules uses.
        compile_xidle = (
            f'{cc} -Wall -Wextra -Wformat '
            f'-D_FILE_OFFSET_BITS=64 '
            f'-DNEED_STRTONUM '
            f'{mbsdport} '
            f'-I{x_includes} '
            f'{cflags} '
            f'-c {src}/xidle.c -o {src}/xidle.o'
        )
        self.run(compile_xidle, cwd=src)

        # Compile strtonum.c. The upstream source guards its __RCSID(...)
        # usage behind `#ifdef MBSDPORT_H` → `#include MBSDPORT_H`, so we
        # must pass the same -DMBSDPORT_H=\"ports/ohos-mbsdport.h\" define
        # as xidle.c: without it the #include is skipped and __RCSID stays
        # undefined, so clang parses __RCSID("...") as a function call and
        # the `$MirOS: ...$` rcsid string breaks declaration parsing.
        compile_strtonum = (
            f'{cc} -Wall -Wextra -Wformat '
            f'-D_FILE_OFFSET_BITS=64 '
            f'{mbsdport} '
            f'{cflags} '
            f'-c {src}/strtonum.c -o {src}/strtonum.o'
        )
        self.run(compile_strtonum, cwd=src)

        # Compile the __progname shim (ports/ohos-progname.c). musl has no
        # __progname BSD libc global nor any program_invocation* extension,
        # so we supply the symbol ourselves; the shim defines __progname
        # and a constructor that reads /proc/self/cmdline to populate the
        # basename before main(). xidle.c declares `extern char *__progname;`
        # so linking the object resolves the undefined symbol. Needs the
        # same -DMBSDPORT_H define is NOT required (shim does not include it).
        compile_progname = (
            f'{cc} -Wall -Wextra -Wformat '
            f'-D_FILE_OFFSET_BITS=64 '
            f'{cflags} '
            f'-c {src}/ports/ohos-progname.c -o {src}/ohos-progname.o'
        )
        self.run(compile_progname, cwd=src)

        # Link xidle against libXss, libXext, libX11 (in that order).
        link_libs = f'-L{x_libraries} ' if x_libraries else ''
        link_cmd = (
            f'{cc} {src}/xidle.o {src}/strtonum.o {src}/ohos-progname.o '
            f'{link_libs}'
            f'-lXss -lXext -lX11 '
            f'{ldflags} '
            f'-o {src}/xidle'
        )
        self.run(link_cmd, cwd=src)

    def package(self):
        # Install the binary into bin/
        copy(self, "xidle", dst=os.path.join(self.package_folder, "bin"), src=self.source_folder)
        # Install the man page (Debian ships xidle.1)
        copy(self, "xidle.1", dst=os.path.join(self.package_folder, "share", "man", "man1"), src=self.source_folder)

    def package_info(self):
        # Terminal tool: no libs to expose, only the binary on PATH.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
