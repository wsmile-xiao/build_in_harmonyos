#!/usr/bin/env python3
"""Conan recipe for ale (Anti-Lamenessing Engine) 0.9.0.3 — Autotools.

HarmonyOS PC adaptation: shebang fix, config.guess/sub update, 
C++11 narrowing fix, pthread_cancel guard, -iquote include path.
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AleConan(ConanFile):
    name = "ale"
    version = "0.9.0.3"
    description = "Anti-Lamenessing Engine (ALE) — synthetic capture engine and renderer"
    license = "GPL-3.0-or-later"
    homepage = "https://repo.or.cz/Ale.git"
    url = "https://repo.or.cz/Ale.git"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import os, shutil
        
        # The build folder is a subdirectory (e.g. build-release/), but configure
        # lives in the parent directory. Determine the actual build root.
        build_root = self.build_folder
        if os.path.basename(build_root) in ("build-release", "build"):
            build_root = os.path.dirname(build_root)
        
        # Copy patched files from source folder to the actual build root
        if os.path.exists(self.source_folder) and os.path.exists(build_root):
            src = self.source_folder
            # Critical files: if any of these fail to copy, abort the build
            critical_files = {"configure", "Makefile.in", "config.guess",
                              "config.sub", "config.h.in"}
            for f in ["configure", "Makefile.in", "config.guess", "config.sub",
                       "config.h.in", "ale.cc", "thread.cc", "rand.cc", "d2.cc", "d3.cc",
                       "ui/input.h", "ui/ui_tty.h", "ui/input.cc", "ui/ui.cc", "ui/ui_log.cc",
                       "d3/focus.h", "d2.h", "d3.h", "thread.h", "rand.h"]:
                src_f = os.path.join(src, f)
                dst_f = os.path.join(build_root, f)
                if os.path.exists(src_f):
                    try:
                        # Skip if src and dst are the same file (e.g. in-tree build)
                        if os.path.realpath(src_f) == os.path.realpath(dst_f):
                            continue
                        dst_dir = os.path.dirname(dst_f)
                        os.makedirs(dst_dir, exist_ok=True)
                        shutil.copy2(src_f, dst_f)
                    except (OSError, IOError) as e:
                        if f in critical_files:
                            raise ConanException(
                                f"Failed to copy critical file {f}: {e}")
                        self.output.warning(f"Failed to copy file {f}: {e}")
        
        # Patch configure script in build root
        configure_path = os.path.join(build_root, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            # HarmonyOS: fix configure shebang - resolve bash from PATH/env
            # (not hardcoded, so the recipe stays portable across environments)
            ohos_bash = shutil.which("bash") or os.environ.get("SHELL", "/bin/bash")
            content = content.replace(
                "#! /bin/sh", f"#!{ohos_bash}"
            )
            content = content.replace(
                '#!/bin/sh', f"#!{ohos_bash}"
            )
            # HarmonyOS: fix config.status temp directory creation
            content = content.replace(
                'mktemp -d "./confXXXXXX"', 'echo "."'
            )
            content = content.replace(
                "tmp=./conf$$-$RANDOM", "tmp=."
            )
            # HarmonyOS: skip 'make clean' at end of configure (triggers auto-regen)
            content = content.replace(
                "make clean &> /dev/null", "# make clean skipped"
            )
            with open(configure_path, "w") as f:
                f.write(content)
        
        # HarmonyOS: fix all #include <config.h> to "config.h" in build root
        # This is needed because -I. was changed to -iquote . which only affects
        # quoted includes, not angle-bracket includes.
        import re
        for root, dirs, files in os.walk(build_root):
            for fname in files:
                if fname.endswith((".c", ".cc", ".h", ".cpp")):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r") as f:
                            content = f.read()
                        # Match both '#include <config.h>' and '# include <config.h>' (with spaces)
                        if re.search(r'#\s*include\s*<config\.h>', content):
                            content = re.sub(r'#\s*include\s*<config\.h>', '#include "config.h"', content)
                            with open(fpath, "w") as f:
                                f.write(content)
                            print(f"  [PATCH] Fixed <config.h> in {os.path.relpath(fpath, build_root)}")
                    except (OSError, IOError) as e:
                        self.output.warning(f"Failed to patch <config.h> in {fpath}: {e}")
        
        # Run configure with bash to avoid HarmonyOS /bin/sh syntax issues
        # Build configure args from the shared option (mirrors generate())
        if self.options.shared:
            shared_args = "--enable-shared --disable-static"
        else:
            shared_args = "--enable-static --disable-shared"
        configure_cmd = ("bash ./configure --prefix=/ --bindir=${prefix}/bin "
                         "--sbindir=${prefix}/bin --libdir=${prefix}/lib "
                         "--includedir=${prefix}/include --oldincludedir=${prefix}/include "
                         + shared_args)
        self.run(configure_cmd, cwd=build_root)
        # Patch generated Makefile to use -iquote instead of -I
        for d in [build_root, os.path.join(build_root, "build-release"),
                  self.build_folder]:
            mf = os.path.join(d, "Makefile")
            if os.path.exists(mf):
                with open(mf, "r") as f:
                    content = f.read()
                content = content.replace("-I.", "-iquote .")
                content = content.replace("-I$(top_builddir)", "-iquote $(top_builddir)")
                content = content.replace("-I$(builddir)", "-iquote $(builddir)")
                with open(mf, "w") as f:
                    f.write(content)
                break
        # Also patch lib/Makefile
        for d in [build_root, os.path.join(build_root, "build-release"),
                  self.build_folder]:
            mf = os.path.join(d, "lib/Makefile")
            if os.path.exists(mf):
                with open(mf, "r") as f:
                    content = f.read()
                content = content.replace("-I.", "-iquote .")
                content = content.replace("-I$(top_builddir)", "-iquote $(top_builddir)")
                with open(mf, "w") as f:
                    f.write(content)
                break
        # Run make from build_root (where Makefile was created by configure)
        # Add a rule to prevent the built-in make rule from linking 'ale' as a binary
        # (ale is a shell script wrapper, not a binary - ale-bin is the actual binary)
        with open(os.path.join(build_root, "Makefile"), "a") as mf:
            mf.write("\n# Prevent built-in rule from linking 'ale' as a binary\n")
            mf.write("ale: $(srcdir)/ale\n")
            mf.write("\tcp $(srcdir)/ale $@\n")
        self.run("make -j1", cwd=build_root)

    def package(self):
        import os
        # Use make install with -j1 to avoid jobserver mkfifo issues on HarmonyOS
        self.run("make install DESTDIR={} -j1".format(self.package_folder), cwd=os.path.dirname(self.build_folder) if os.path.basename(self.build_folder) in ("build-release", "build") else self.build_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
