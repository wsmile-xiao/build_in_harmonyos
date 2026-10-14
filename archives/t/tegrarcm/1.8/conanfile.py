#!/usr/bin/env python3
"""Conan recipe for tegrarcm 1.8 (NVIDIA Tegra RCM tool) on HarmonyOS PC.

Direct-compile (no autotools bootstrap): upstream tag tarball ships only
configure.ac/Makefile.am without generated configure, and preflight's
autoconf chain pulls conancenter m4 whose configure hardcodes
/data/service/hnp/bin/bash (Error 127, inaccessible). Vendored libusb +
cryptopp also avoid conancenter cmake (KeyError 'OHOS'). This recipe
vendors both libs (official sources, original sha256) and compiles
tegrarcm sources directly with clang, so the graph has zero library
requires and zero tool_requires.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class TegrarcmConan(ConanFile):
    name = "tegrarcm"
    version = "1.8"
    description = "Tegra ReCovery Mode tool; communicates with Tegra boot ROM to download code over USB"
    license = "LicenseRef-NVIDIA-tegrarcm"
    homepage = "https://github.com/NVIDIA/tegrarcm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Fully vendored: no library requires, no tool_requires.
        # Avoids conancenter cmake (KeyError OHOS) and m4 (bash 127).
        pass

    def build_requirements(self):
        # No autotools bootstrap: direct clang compile below.
        # System make/clang come from HMBS PATH (no conan tools).
        pass

    @property
    def _cryptopp_src(self):
        return os.path.join(self.source_folder, "vendor-cryptopp")

    @property
    def _libusb_src(self):
        return os.path.join(self.source_folder, "vendor-libusb")

    @property
    def _vendor_prefix(self):
        return os.path.join(self.build_folder, "vendor_prefix")

    def source(self):
        get(self, **self.conan_data["sources"]["tegrarcm"], strip_root=True)
        get(self, **self.conan_data["sources"]["cryptopp"],
            destination=self._cryptopp_src, strip_root=True)
        get(self, **self.conan_data["sources"]["libusb"],
            destination=self._libusb_src, strip_root=True)

    def generate(self):
        # Direct compile: flags passed explicitly in build().
        # No toolchain/env scripts needed; conanbuild env still provides
        # HMBS PATH (make/clang) from profile buildenv.
        pass

    def _resolve_compiler(self, kind, fallbacks):
        """Resolve a working compiler: conf path only if it exists, else PATH.

        Preflight profile may pin tools.build:compiler_executables to
        /data/service/hnp/bin/clang++ which does not exist on every worker
        (Error 127). Trust that path only after an existence+executable
        check; otherwise fall back to conanbuild env (CC/CXX) and PATH
        lookup (HMBS prepends real toolchain dirs to PATH).
        """
        import shutil
        compilers = {}
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        candidates = []
        conf_val = compilers.get(kind)
        if conf_val:
            candidates.append(conf_val)
        env_key = {"c": "CC", "cpp": "CXX", "ar": "AR"}.get(kind)
        if env_key and os.environ.get(env_key):
            candidates.append(os.environ[env_key].split()[0])
        candidates.extend(fallbacks)
        for cand in candidates:
            if not cand:
                continue
            prog = cand.split()[0]
            if os.path.isabs(prog):
                if os.path.isfile(prog) and os.access(prog, os.X_OK):
                    return cand
                base = os.path.basename(prog)
                found = shutil.which(base)
                if found:
                    return cand.replace(prog, found, 1) if prog in cand else found
                continue
            found = shutil.which(prog)
            if found:
                return cand.replace(prog, found, 1) if prog in cand else found
            if os.path.isfile(prog) and os.access(prog, os.X_OK):
                return cand
        # Last resort: return first fallback literally; make/configure will
        # surface a clear error instead of a stale absolute path.
        return fallbacks[0] if fallbacks else cand

    def _compilers(self):
        # R33: compilers from Conan conf, never bare $CC/$CXX -- but only
        # when the configured absolute path actually exists on this worker.
        cc = self._resolve_compiler("c", ["clang", "cc", "gcc"])
        cxx = self._resolve_compiler("cpp", ["clang++", "c++", "g++"])
        ar = self._resolve_compiler("ar", ["llvm-ar", "ar"])
        return cc, cxx, ar

    def _sanitize_hnp_shell(self, root):
        """Replace hardcoded /data/service/hnp/bin/bash with /bin/sh.

        Vendored libusb's configure re-execs $SHELL/$CONFIG_SHELL; the OHOS
        profile exports SHELL=/data/service/hnp/bin/bash which is not
        visible inside this preflight worker (./configure[139]: inaccessible
        or not found, Error 127). HMBS guarantees /bin/sh (see
        HMBS_PLATFORM_CAPABILITIES shell + injected SHELL=/bin/sh), so
        rewrite the stale absolute path wherever it appears.
        """
        stale = "/data/service/hnp/bin/bash"
        fixed = "/bin/sh"
        touched = 0
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, "rb") as f:
                        raw = f.read()
                except OSError:
                    continue
                if stale.encode() not in raw:
                    continue
                try:
                    text = raw.decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    continue
                # Skip binary blobs that merely mention the path.
                if "\x00" in text:
                    continue
                text = text.replace(stale, fixed)
                try:
                    with open(p, "w", encoding="utf-8", newline="") as f:
                        f.write(text)
                    touched += 1
                except OSError:
                    continue
        self.output.info("sanitized hnp bash path in %d files under %s" % (touched, root))
        return touched

    def _drop_umask_077(self, path):
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8", errors="replace") as f:
            data = f.read()
        orig = data
        data = data.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
        data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
        data = data.replace("umask 077", "umask 022")
        if data != orig:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)

    def _build_vendored_cryptopp(self):
        _, cxx, _ = self._compilers()
        prefix = self._vendor_prefix
        incdir = os.path.join(prefix, "include", "cryptopp")
        libdir = os.path.join(prefix, "lib")
        os.makedirs(incdir, exist_ok=True)
        os.makedirs(libdir, exist_ok=True)
        # Same as archives/c/cryptopp/8.9.0: plain Makefile, single job.
        # cxx already resolved to an existing binary (conf path verified).
        self.output.info("cryptopp CXX resolved to: %s" % cxx)
        self.run('make CXX="%s" -j1' % cxx, cwd=self._cryptopp_src, env="conanbuild")
        copy(self, "*.h", src=self._cryptopp_src, dst=incdir)
        copy(self, "libcryptopp.a", src=self._cryptopp_src, dst=libdir)

    def _fix_config_sub_for_ohos(self, libusb_src):
        """Normalize *-ohos triples to *-linux-gnu inside vendored config.sub.

        libusb-1.0.29 ships an old config.sub that rejects
        `aarch64-unknown-linux-ohos` with
        "Invalid configuration ...: OS `ohos' not recognized".
        OHOS uses the linux USB backend, so mapping to linux-gnu preserves
        backend selection. The shim is version-agnostic (inserted right after
        the shebang, only rewrites $1 when it ends in -ohos) and handles both
        `*-linux-ohos` (4-part) and bare `*-ohos` forms.
        """
        path = os.path.join(libusb_src, "config.sub")
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8", errors="replace") as f:
            data = f.read()
        marker = "HMBS ohos compat"
        if marker in data:
            self.output.info("config.sub already has ohos compat shim")
            return
        lines = data.splitlines(keepends=True)
        insert_at = 1 if lines and lines[0].startswith("#!") else 0
        shim = (
            "# HMBS ohos compat: normalize *-ohos to *-linux-gnu (old config.sub\n"
            "# rejects OS `ohos'; OHOS uses the linux USB backend).\n"
            'case "$1" in\n'
            "  *-linux-ohos)\n"
            '    set -- "${1%-linux-ohos}-linux-gnu"\n'
            "    ;;\n"
            "  *-ohos)\n"
            '    set -- "${1%-ohos}-linux-gnu"\n'
            "    ;;\n"
            "esac\n"
        )
        lines.insert(insert_at, shim)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)
        self.output.info("patched config.sub to accept *-ohos (normalize to linux-gnu)")

    def _build_vendored_libusb(self):
        netlink = os.path.join(self._libusb_src, "libusb", "os", "linux_netlink.c")
        if os.path.isfile(netlink):
            replace_in_file(
                self, netlink,
                "#include <sys/socket.h>\n#include <linux/netlink.h>",
                "#include <sys/socket.h>\n\n"
                "#define sockaddr_storage __linux_sockaddr_storage\n"
                "#include <linux/netlink.h>\n"
                "#undef sockaddr_storage\n",
            )
        for helper in ("configure", "config.guess", "config.sub", "install-sh"):
            path = os.path.join(self._libusb_src, helper)
            if os.path.isfile(path):
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass
        self._drop_umask_077(os.path.join(self._libusb_src, "configure"))
        self._fix_config_sub_for_ohos(self._libusb_src)
        self._sanitize_hnp_shell(self._libusb_src)
        prefix = self._vendor_prefix
        cc, cxx, _ = self._compilers()
        self.output.info("libusb CC/CXX resolved to: %s / %s" % (cc, cxx))
        self.run(
            'SHELL=/bin/sh CONFIG_SHELL=/bin/sh CC="%s" CXX="%s" sh ./configure --prefix="%s" '
            "--build=aarch64-unknown-linux-gnu "
            "--host=aarch64-unknown-linux-ohos "
            "--disable-dependency-tracking --disable-udev "
            "--disable-shared --enable-static" % (cc, cxx, prefix),
            cwd=self._libusb_src, env="conanbuild")
        self.run('make -j1 SHELL=/bin/sh CC="%s"' % cc, cwd=self._libusb_src, env="conanbuild")
        self.run("make install SHELL=/bin/sh", cwd=self._libusb_src, env="conanbuild")

    def _write_config_h(self):
        # Minimal config.h replacing autoconf output. All listed headers
        # exist on OHOS musl; error.h intentionally absent -> portable
        # error() fallback in 0001-musl-error-h-compat.patch.
        # PACKAGE_* mimic autoconf AC_INIT([tegrarcm],[1.8]): direct
        # compile has no generated config.h, but src/main.c prints
        # PACKAGE_NAME/PACKAGE_VERSION (--version).
        content = (
            "#pragma once\n"
            "#define PACKAGE_NAME \"tegrarcm\"\n"
            "#define PACKAGE_TARNAME \"tegrarcm\"\n"
            "#define PACKAGE_VERSION \"1.8\"\n"
            "#define PACKAGE_STRING \"tegrarcm 1.8\"\n"
            "#define PACKAGE_BUGREPORT \"\"\n"
            "#define PACKAGE_URL \"\"\n"
            "#define VERSION \"1.8\"\n"
            "#define CRYPTOLIB_HEADER_PREFIX cryptopp\n"
            "#define HAVE_FCNTL_H 1\n"
            "#define HAVE_STDINT_H 1\n"
            "#define HAVE_STDLIB_H 1\n"
            "#define HAVE_STRING_H 1\n"
            "#define HAVE_SYS_PARAM_H 1\n"
            "#define HAVE_UNISTD_H 1\n"
        )
        for d in (self.source_folder, self.build_folder):
            with open(os.path.join(d, "config.h"), "w", encoding="utf-8") as f:
                f.write(content)

    def _fix_main_c_for_ohos(self):
        """Ensure src/main.c sees PATH_MAX on OHOS musl.

        Upstream main.c uses PATH_MAX without including <limits.h>
        (glibc pulls it transitively via sys/param.h; musl does not).
        Insert the include plus a 4096 fallback guard idempotently.
        """
        path = os.path.join(self.source_folder, "src", "main.c")
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8", errors="replace") as f:
            data = f.read()
        orig = data
        if "#include <limits.h>" not in data:
            anchor = "#include <fcntl.h>"
            insert = "#include <fcntl.h>\n#include <limits.h>\n#ifndef PATH_MAX\n#define PATH_MAX 4096\n#endif"
            if anchor in data:
                data = data.replace(anchor, insert, 1)
            else:
                data = data.replace(
                    '#include "config.h"',
                    '#include "config.h"\n#include <limits.h>\n#ifndef PATH_MAX\n#define PATH_MAX 4096\n#endif',
                    1)
        elif "PATH_MAX" not in data or "#ifndef PATH_MAX" not in data:
            data = data.replace(
                "#include <limits.h>",
                "#include <limits.h>\n#ifndef PATH_MAX\n#define PATH_MAX 4096\n#endif",
                1)
        if data != orig:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(data)
            self.output.info("patched src/main.c for PATH_MAX (limits.h + fallback)")
        else:
            self.output.info("src/main.c already has PATH_MAX handling")

    def build(self):
        apply_conandata_patches(self)
        self._fix_main_c_for_ohos()
        cc, cxx, _ = self._compilers()
        prefix = self._vendor_prefix
        shutil.rmtree(prefix, ignore_errors=True)
        os.makedirs(prefix, exist_ok=True)
        self._build_vendored_cryptopp()
        self._build_vendored_libusb()
        self._write_config_h()

        src = os.path.join(self.source_folder, "src")
        inc_prefix = os.path.join(prefix, "include")
        lib_prefix = os.path.join(prefix, "lib")
        # -I order: build (config.h) -> source root (config.h copy) ->
        # vendor includes -> libusb includes.
        cflags = (
            '-Wall -std=c99 -O2 -I"%s" -I"%s" -I"%s" -I"%s" '
            % (self.build_folder, self.source_folder, inc_prefix,
               os.path.join(inc_prefix, "libusb-1.0"))
        )
        cxxflags = (
            '-Wall -std=c++11 -O2 -I"%s" -I"%s" -I"%s" -I"%s" '
            % (self.build_folder, self.source_folder, inc_prefix,
               os.path.join(inc_prefix, "libusb-1.0"))
        )
        ldflags = '-L"%s" ' % lib_prefix
        libs = "-lcryptopp -lusb-1.0 -lpthread"

        objs = []
        for fn in ("main.c", "usb.c", "nv3p.c", "debug.c", "rcm.c"):
            obj = os.path.join(self.build_folder, fn + ".o")
            self.run('"%s" %s -c "%s" -o "%s"' % (cc, cflags, os.path.join(src, fn), obj),
                     cwd=self.build_folder, env="conanbuild")
            objs.append('"%s"' % obj)
        for fn in ("rsa-pss.cpp", "aes-cmac.cpp"):
            obj = os.path.join(self.build_folder, fn + ".o")
            self.run('"%s" %s -c "%s" -o "%s"' % (cxx, cxxflags, os.path.join(src, fn), obj),
                     cwd=self.build_folder, env="conanbuild")
            objs.append('"%s"' % obj)
        binary = os.path.join(self.build_folder, "tegrarcm")
        self.run('"%s" %s -o "%s" %s %s' % (cxx, ldflags, binary, " ".join(objs), libs),
                 cwd=self.build_folder, env="conanbuild")
        # Man page (same sed as src/Makefile.am) + empty-check evidence.
        self.run('sed "s|VERSION|%s|g" "%s" > "%s"'
                 % (self.version, os.path.join(src, "tegrarcm.1.in"),
                    os.path.join(self.build_folder, "tegrarcm.1")),
                 cwd=self.build_folder, env="conanbuild")
        # No autotools Makefile: upstream registers no TESTS (audited in
        # test_package/MANIFEST.yml); test_package re-emits the no_tests
        # marker with file-level audit, so no make check here.

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "tegrarcm", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "tegrarcm.1", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
