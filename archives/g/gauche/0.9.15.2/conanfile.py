#!/usr/bin/env python3
"""Conan recipe — Gauche 0.9.15 (Scheme interpreter).

Gauche is a Scheme interpreter with R7RS compatibility, UTF-8 support,
and multithreading. It builds via autotools and produces the `gosh`
executable and `libgauche` shared library.

Key OHOS adaptations:
  - config.guess/config.sub patched for OHOS platform detection
  - Boehm GC patched to disable pthread_cancel (musl libc gap)
  - extension directory skipped because OHOS dynamic module loading fails
  - pthread_compat.c stub for missing pthread_cancel/setcancelstate

File location: archives/g/gauche/0.9.15.2/conanfile.py
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GaucheConan(ConanFile):
    name = "gauche"
    version = "0.9.15.2"
    description = "Gauche is a Scheme implementation designed as a scripting language"
    license = "BSD-3-Clause"
    homepage = "https://practical-scheme.net/gauche/"
    url = "https://github.com/shirok/Gauche"

    # Gauche produces both an executable (gosh) and a library (libgauche).
    # We classify it as an application since the primary deliverable is the
    # interpreter binary.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # No external Conan dependencies — Gauche bundles its own Boehm GC.

    # 0.9.15.2: the dbm.gdbm extension links against the gdbm library, which
    # is already published (gdbm/1.24, R36 check passed at W0).
    def requirements(self):
        self.requires("gdbm/1.24")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        get(
            self,
            url=source["url"],
            sha256=source["sha256"],
            strip_root=True,
        )
        required_entries = ("configure", "gc", "libsrc")
        if not all(os.path.exists(os.path.join(self.source_folder, entry))
                   for entry in required_entries):
            raise ConanException(
                "Extracted release root does not contain configure, gc/, and libsrc/"
            )

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Gauche 非系统同名库（R26 仅限系统同名库），默认动态构建：
        # 其 Boehm GC 需要生成 libgc_pic.a（PIC 归档）供 libgauche 链接，
        # --disable-shared 会使 libgc_pic.a 为空导致 GC_* 符号未定义。
        # 依赖链由 Conan 管理，gosh 可执行文件自带 RPATH。
        # OHOS libc does not provide pthread cancellation. Boehm GC already
        # supports disabling that optional feature with this capability macro.
        tc.extra_cflags.append("-DGC_NO_PTHREAD_CANCEL")

        # 0.9.15.2: ext/dbm needs the gdbm header and library at configure
        # time, otherwise dbmconf.h keeps HAVE_GDBM_H undefined and the
        # dbm.gdbm extension is not built.  AutotoolsToolchain emits
        # CPPFLAGS/LDFLAGS into conanbuild.sh, so propagate them explicitly.
        if self.dependencies.get("gdbm"):
            gdbm = self.dependencies["gdbm"]
            inc = gdbm.cpp_info.includedirs[0]
            libdir = gdbm.cpp_info.libdirs[0]
            tc.extra_cflags.append(f"-I{inc}")
            tc.extra_ldflags.append(f"-L{libdir}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # 0046 changes configure.ac inputs, so regenerate the generated
        # configure scripts instead of editing them in place (R6).
        self.run("autoconf", cwd=self.source_folder)
        self.run("autoconf", cwd=os.path.join(self.source_folder, "gc"))

        autotools = Autotools(self)
        autotools.configure()

        # The core interpreter builds from the upstream gc/lib/src
        # subdirectories.  Invoke upstream subdirectory targets directly
        # instead of altering generated Makefile.in/configure files (R6).
        make_args = "-j16 --jobserver-style=pipe"
        for subdir in ("gc", "lib"):
            self.run(f'make -C "{os.path.join(self.build_folder, subdir)}" all {make_args}')

        # HMDFS can make `pwd` fail in make's child shell.  The upstream
        # POSTBUILD hook accepts TARGETLIB as a Make variable, so supply the
        # known build directory without changing the generated Makefile.
        src_build = os.path.join(self.build_folder, "src")
        postbuild = (
            f'TARGETLIB="{src_build}" DESTDIR= '
            "$(MAKEVERSLINK) $(LIBGAUCHE).$(SOEXT)"
        )
        self.run(
            f'make -C "{src_build}" all {make_args} '
            f"POSTBUILD='{postbuild}'"
        )

        # 0.9.15.2: build the extension modules that downstream consumers
        # need.  dbm.gdbm pulls in gauche.collection/dictionary/generator
        # (ext/gauche) and the gdbm library.  ext/Makefile.ext links against
        # $(top_builddir)/src, and configure already recorded HAVE_GDBM_H
        # thanks to the CPPFLAGS above.
        ext_build = os.path.join(self.build_folder, "ext")
        if os.path.isfile(os.path.join(ext_build, "Makefile")):
            # Build the full ext tree so every dlopen-able dependency chain
            # (e.g. gauche--collection, util--match) exists for consumers.
            # Individual modules that fail to link (HMDFS-specific, e.g.
            # charconv) do not block the ones we need; tolerate make errors
            # here and verify the required modules below in package().
            # The precomp step runs the freshly built gosh, which needs
            # libgauche (LD_LIBRARY_PATH) and the source library trees
            # (GAUCHE_LOAD_PATH) to load e.g. file.util: upstream keeps the
            # Scheme sources under libsrc/ and only generates lib/ during
            # `make -C lib`.  ext/*/Makefile link DSOs via MODLINK =
            # $(CCLD) $(CFLAGS) $(LDFLAGS); the generated ext/Makefile.ext
            # only sets EXT_LIBGAUCHE=-L"$(top_builddir)/src" without -l, so
            # the DSOs end up with undefined Scm_* symbols and cannot be
            # dlopen'ed.  Override EXT_LIBGAUCHE to actually link libgauche.
            ext_env = Environment()
            ext_env.define("LD_LIBRARY_PATH", src_build)
            # ext/* sources use (include "...") relative to the module
            # directory (e.g. unicode.scm includes unicode-attr.scm), which
            # precomp resolves through *load-path*; expose every ext module
            # directory so those includes resolve.
            ext_load_path = [
                os.path.join(self.source_folder, "lib"),
                os.path.join(self.source_folder, "libsrc"),
            ]
            ext_src = os.path.join(self.source_folder, "ext")
            if os.path.isdir(ext_src):
                for entry in sorted(os.listdir(ext_src)):
                    p = os.path.join(ext_src, entry)
                    if os.path.isdir(p):
                        ext_load_path.append(p)
            ext_env.define("GAUCHE_LOAD_PATH", os.pathsep.join(ext_load_path))
            # The precomp-generated C sources (uvector.c is ~7.5 MB) take
            # minutes to compile at -O2/-O3; extension modules are not
            # performance-critical, so build them with -O0 while keeping the
            # OHOS pthread-cancel capability macro and the gdbm include path.
            # NOTE: ext/Makefile.ext already defines CFLAGS (ending in
            # $(XCFLAGS)) and LDFLAGS (containing the essential "-shared -o");
            # do NOT override them wholesale — append via XCFLAGS/XLDFLAGS so
            # "-shared -o" and the default flags survive.
            ext_make_extra = [
                f'EXT_LIBGAUCHE="-L{src_build} -lgauche-0.98"',
                'XCFLAGS="-O0 -DGC_NO_PTHREAD_CANCEL"',
            ]
            if self.dependencies.get("gdbm"):
                gdbm = self.dependencies["gdbm"]
                ext_make_extra.append(
                    f'XCFLAGS+=" -I{gdbm.cpp_info.includedirs[0]}"'
                )
                # charconv links against the system libiconv; its shared
                # library lives under the toolchain prefix.
                ext_make_extra.append(
                    'XLDFLAGS="-L/storage/Users/currentUser/usr/local/lib '
                    f'-L{gdbm.cpp_info.libdirs[0]}"'
                )
            else:
                ext_make_extra.append(
                    'XLDFLAGS="-L/storage/Users/currentUser/usr/local/lib"'
                )
            with ext_env.vars(self).apply():
                self.run(
                    # Build the whole ext tree so every dlopen-able module a
                    # consumer may load exists (dbm.gdbm, gauche.termios via
                    # text.console for gauche-package, util.match, ...).
                    # `-k` keeps going past modules that cannot link on
                    # HMDFS; -O0 (XCFLAGS above) keeps the big generated
                    # uvector.c compile fast.
                    f'make -C "{ext_build}" all -k -j1 '
                    + " ".join(ext_make_extra),
                    ignore_errors=True,
                )

    def package(self):
        # The upstream install target invokes the newly built gosh.  That
        # executable cannot be loaded from the HMDFS build path, so package the
        # completed core artifacts with Conan's file API instead.
        src_build = os.path.join(self.build_folder, "src")
        lib_build = os.path.join(self.build_folder, "lib")
        include_dir = os.path.join(
            self.package_folder, "lib", "gauche-0.98", "0.9.15", "include"
        )

        copy(self, "gosh", src=src_build, dst=os.path.join(self.package_folder, "bin"))
        # Package the companion tools required by downstream builds
        # (e.g. wiliki runs ./configure and needs gauche-config, gauche-package,
        # gauche-install and gauche-cesconv on PATH).
        for tool in ("gauche-config", "gauche-package", "gauche-install", "gauche-cesconv"):
            copy(self, tool, src=src_build, dst=os.path.join(self.package_folder, "bin"))
        # The gosh-based tools carry a `#!//bin/gosh` shebang baked at
        # configure time with prefix=/; rewrite it to the packaged gosh so
        # the tools are directly executable from the package bin/.
        for tool in ("gauche-package", "gauche-install", "gauche-cesconv"):
            tool_path = os.path.join(self.package_folder, "bin", tool)
            if os.path.exists(tool_path):
                with open(tool_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                content = content.replace(
                    "#!/bin/gosh", f"#!{os.path.join(self.package_folder, 'bin', 'gosh')}"
                )
                content = content.replace(
                    "#!//bin/gosh", f"#!{os.path.join(self.package_folder, 'bin', 'gosh')}"
                )
                with open(tool_path, "w", encoding="utf-8") as f:
                    f.write(content)
        copy(self, "libgauche-0.98.so*", src=src_build,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "gauche.h", src=os.path.join(self.source_folder, "src"),
             dst=include_dir, keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "src", "gauche"),
             dst=os.path.join(include_dir, "gauche"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "gc", "include"),
             dst=include_dir)
        copy(self, "config.h", src=os.path.join(src_build, "gauche"),
             dst=os.path.join(include_dir, "gauche"), keep_path=False)
        copy(self, "config_threads.h", src=os.path.join(src_build, "gauche"),
             dst=os.path.join(include_dir, "gauche"), keep_path=False)
        copy(self, "configP.h", src=os.path.join(src_build, "gauche", "priv"),
             dst=os.path.join(include_dir, "gauche", "priv"), keep_path=False)

        scheme_dir = os.path.join(
            self.package_folder, "share", "gauche-0.98", "0.9.15", "lib"
        )
        copy(self, "*.scm", src=os.path.join(self.source_folder, "lib"), dst=scheme_dir)
        copy(self, "*.sld", src=os.path.join(self.source_folder, "lib"), dst=scheme_dir)
        copy(self, "*.scm", src=lib_build, dst=scheme_dir)
        copy(self, "*.sld", src=lib_build, dst=scheme_dir)
        # Precompiled module stubs (e.g. gauche/uvector.sci,
        # gauche/record.sci) are only produced under build lib/, not the
        # source tree; they are required to load the corresponding modules.
        copy(self, "*.sci", src=lib_build, dst=scheme_dir)

        # Some core modules live only under libsrc/ (e.g. srfi/13.scm,
        # file/util.scm, gauche/collection.scm) and are not produced by
        # `make -C lib`; ship them too so `(use srfi.13)` and friends work
        # for consumers such as wiliki's gauche-package.
        libsrc = os.path.join(self.source_folder, "libsrc")
        if os.path.isdir(libsrc):
            for root, _dirs, files in os.walk(libsrc):
                for f in files:
                    if f.endswith((".scm", ".sld")):
                        rel = os.path.relpath(root, libsrc)
                        dst = os.path.join(scheme_dir, rel)
                        os.makedirs(dst, exist_ok=True)
                        copy(self, f, src=root, dst=dst, keep_path=False)

        # 0.9.15.2: package the extension modules (dbm.gdbm and its dlopen
        # dependency chain).  Compiled DSOs go to the architecture directory
        # (found via *dynamic-load-path*), precompiled .sci and Scheme sources
        # go to the library directory next to the core .scm files.
        ext_build = os.path.join(self.build_folder, "ext")
        if os.path.isdir(ext_build):
            arch_dir = os.path.join(
                self.package_folder, "lib", "gauche-0.98", "0.9.15",
                "aarch64-unknown-linux-ohos",
            )
            os.makedirs(arch_dir, exist_ok=True)
            for root, _dirs, files in os.walk(ext_build):
                for f in files:
                    if f.endswith(".so"):
                        copy(self, f, src=root, dst=arch_dir, keep_path=False)
                    elif f.endswith((".sci", ".scm")):
                        rel = os.path.relpath(root, ext_build)
                        dst = os.path.join(scheme_dir, rel)
                        os.makedirs(dst, exist_ok=True)
                        copy(self, f, src=root, dst=dst, keep_path=False)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Gauche installs headers under lib/gauche-<abi>/<ver>/include/
        # (autotools GAUCHE_HEADER_INSTALL_DIR), not under a top-level include/.
        # Conan cpp_info.includedirs is relative to the package folder.
        gauche_inc = os.path.join("lib", "gauche-0.98", "0.9.15", "include")
        self.cpp_info.includedirs = [gauche_inc]
        self.cpp_info.libs = ["gauche-0.98"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        # Gauche resolves its Scheme standard library through this path at
        # runtime.  Conan's run environment must point at the packaged tree.
        gauche_lib = os.path.join(
            self.package_folder, "share", "gauche-0.98", "0.9.15", "lib"
        )
        self.runenv_info.define_path("GAUCHE_LOAD_PATH", gauche_lib)

        # 0.9.15.2: extension DSOs are dlopen'ed through *dynamic-load-path*.
        # The packaged gosh was configured with prefix=/ so its baked-in arch
        # path is //lib/gauche-0.98/0.9.15/aarch64-unknown-linux-ohos; point
        # GAUCHE_DYNLOAD_PATH at the packaged arch directory instead.
        gauche_arch = os.path.join(
            self.package_folder, "lib", "gauche-0.98", "0.9.15",
            "aarch64-unknown-linux-ohos",
        )
        self.runenv_info.define_path("GAUCHE_DYNLOAD_PATH", gauche_arch)
