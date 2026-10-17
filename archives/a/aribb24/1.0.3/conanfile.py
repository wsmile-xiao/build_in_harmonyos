#!/usr/bin/env python3
"""Conan recipe for aribb24 1.0.3 (Autotools).

ARIB STD-B24 caption/subtitle library.
"""
import os
import re
import shutil
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Aribb24Conan(ConanFile):
    name = "aribb24"
    version = "1.0.3"
    description = "ARIB STD-B24 caption/subtitle library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/nkoriyama/aribb24"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.name} only supports Linux/OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58")

    def build_requirements(self):
        # GitHub archive tarball has no pre-generated configure; CI Worker
        # lacks automake/aclocal (E178) — bring them as Conan build tools.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # PKG_CHECK_MODULES uses pkg.m4 from the hnp pkg-config install;
        # aclocal must find it when we bootstrap configure.ac.
        import glob
        env = tc.environment()
        for _d in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            env.append_path("ACLOCAL_PATH", _d)
        tc.generate(env=env)
        from conan.tools.gnu import PkgConfigDeps
        pc = PkgConfigDeps(self)
        pc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Generate autotools files (GitHub archive tarball has no configure)
        self.run("autoreconf -fi", cwd=self.source_folder)

        # Patch config.guess/config.sub for HarmonyOS (E007)
        self._patch_config_for_ohos()

        # Set PNG_CFLAGS/PNG_LIBS from Conan dependency
        png = self.dependencies["libpng"]
        png_inc = os.path.join(png.package_folder, "include")
        png_inc16 = os.path.join(png.package_folder, "include", "libpng16")
        png_libdir = os.path.join(png.package_folder, "lib")
        png_cflags = f"-I{png_inc} -I{png_inc16}"
        png_libs = f"-L{png_libdir} -lpng16 -lz"
        os.environ["PNG_CFLAGS"] = png_cflags
        os.environ["PNG_LIBS"] = png_libs

        # Set PWD and TMPDIR for HMDFS limitations
        os.environ["PWD"] = self.build_folder
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        bash = shutil.which("bash")
        configure_path = os.path.join(self.source_folder, "configure")

        # Fix configure shebang for HarmonyOS (E165)
        with open(configure_path, "r", errors="replace") as f:
            content = f.read()
        if "#!/bin/sh" in content[:20]:
            content = content.replace("#!/bin/sh", "#!/system/bin/sh", 1)
            with open(configure_path, "w") as f:
                f.write(content)

        # Run configure through bash
        self.run(f'{bash} "{configure_path}" --no-create '
                 f'--disable-shared --enable-static --prefix=/ '
                 f'"--bindir=${{prefix}}/bin" '
                 f'"--sbindir=${{prefix}}/bin" '
                 f'"--libdir=${{prefix}}/lib" '
                 f'"--includedir=${{prefix}}/include" '
                 f'"--oldincludedir=${{prefix}}/include"')

        # Fix umask in config.status
        cs_path = os.path.join(self.build_folder, "config.status")
        if not os.path.exists(cs_path):
            cs_path = "config.status"
        if os.path.exists(cs_path):
            with open(cs_path, "r", errors="replace") as f:
                cs_content = f.read()
            cs_content = cs_content.replace("umask 077", "umask 022")
            with open(cs_path, "w") as f:
                f.write(cs_content)
            self.run(f'{bash} "{cs_path}"')

        # Pre-create required directories
        for d in ["src/.libs", "src/.deps", ".libs"]:
            dp = os.path.join(self.build_folder, d)
            os.makedirs(dp, exist_ok=True)

        # Fix libtool tool paths
        libtool_path = None
        for lt_dir in [self.build_folder,
                       os.path.join(self.build_folder, "build-release"),
                       self.source_folder]:
            candidate = os.path.join(lt_dir, "libtool")
            if os.path.isfile(candidate):
                libtool_path = candidate
                break
        if libtool_path:
            with open(libtool_path, "r", errors="replace") as f:
                lt = f.read()
            lt = lt.replace("#!/bin/sh", "#!/system/bin/sh", 1)
            for tool_name in ["SED", "GREP", "EGREP", "FGREP"]:
                accessible = shutil.which(tool_name.lower())
                if accessible:
                    pattern = f'({tool_name}=")([^"]*)(")'
                    m = re.search(pattern, lt)
                    if m:
                        old_val = m.group(2)
                        old_path = old_val.split()[0]
                        try:
                            os.stat(old_path)
                        except (PermissionError, FileNotFoundError, OSError):
                            lt = re.sub(pattern, f'\\g<1>{accessible}\\g<3>', lt)
            with open(libtool_path, "w") as f:
                f.write(lt)

        self.run('make -j1 V=1 ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true')

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub to recognize HarmonyOS (E007)."""
        src = self.source_folder
        for d in [src, os.path.join(src, "build-aux")]:
            cg = os.path.join(d, "config.guess")
            cs = os.path.join(d, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                self._patch_config_guess(cg)
                self._patch_config_sub(cs)
                return

    def _patch_config_guess(self, cg_path):
        with open(cg_path, "r") as f:
            content = f.read()
        changed = False
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = ("#if defined(__ANDROID__)\n    LIBC=android"
                   "\n#elif defined(__OHOS__)\n    LIBC=ohos")
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True
        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _patch_config_sub(self, cs_path):
        with open(cs_path, "r") as f:
            content = f.read()
        changed = False
        if "ohos-linux" not in content:
            pattern = (r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown'
                       r'\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)')
            replacement = (r'\1\tohos-linux)\n'
                           r'\tbasic_machine=$field1-unknown\n'
                           r'\tbasic_os=linux-ohos\n\t;;\n')
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True
        if "ohos*" not in content:
            content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            changed = True
        if "linux-ohos" not in content:
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*\))',
                                     r'\1| linux-ohos*)', content)
            if count > 0:
                changed = True
        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include", "aribb24")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)
        # Search for the built library in build_folder and source_folder.
        # Library may be in .libs/ subdirectory (autotools libtool convention).
        for search_dir in [self.build_folder, self.source_folder]:
            if not search_dir or not os.path.isdir(search_dir):
                continue
            for root, _, files in os.walk(search_dir):
                if "libaribb24.a" in files:
                    src_lib = os.path.join(root, "libaribb24.a")
                    dst_lib = os.path.join(libdir, "libaribb24.a")
                    shutil.copy2(src_lib, dst_lib)
                    self.output.info(f"Packaged library from {src_lib}")
                    break
            else:
                continue
            break
        src_inc = os.path.join(self.source_folder, "src", "aribb24")
        copy(self, "*.h", src_inc, incdir)

    def package_info(self):
        self.cpp_info.libs = ["aribb24"]
        self.cpp_info.requires = ["libpng::libpng"]
        self.cpp_info.set_property("cmake_file_name", "aribb24")
        self.cpp_info.set_property("cmake_target_name", "aribb24::aribb24")
        self.cpp_info.set_property("pkg_config_name", "aribb24")
