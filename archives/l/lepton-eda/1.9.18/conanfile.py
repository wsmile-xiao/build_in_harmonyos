#!/usr/bin/env python3
"""Conan recipe for Lepton EDA 1.9.18, an EDA suite (schematic capture,
netlister, symbol checker) built on GTK3 and Guile."""

import glob
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class LeptonEdaConan(ConanFile):
    name = "lepton-eda"
    version = "1.9.18"
    description = "Lepton EDA: suite of free software tools for electronics design"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/lepton-eda/lepton-eda"
    url = "https://atomgit.com/li_shuo/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def requirements(self):
        # GTK3 stack: lepton-schematic and libleptongui link against gtk3,
        # gdk, cairo, pango; configure discovers them through pkg-config.
        self.requires("gtk/3.24.38", transitive_headers=True, transitive_libs=True)
        # The Guile runtime is both a build and run dependency: liblepton
        # embeds libguile and the lepton-* programs are Guile scripts.
        self.requires("guile/2.2.7.1", run=True,
                      transitive_headers=True, transitive_libs=True)
        # libguile.h pulls in <gc/gc.h> and <gmp.h>; keep their headers
        # reachable for configure probes and compilation.
        self.requires("gc/8.2.12", run=True, transitive_headers=True)
        self.requires("gmp/6.3.0", run=True, transitive_headers=True)
        self.requires("libffi/3.4.4", run=True)
        self.requires("libunistring/1.0", run=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                f"lepton-eda supports Linux/OHOS builds, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        patches_dir = os.path.join(self.export_sources_folder, "patches")
        if not os.path.isdir(patches_dir):
            raise ConanException("exported patches folder not found")
        # Copy patch files and the two files the published Guile package
        # misses (the libguile.h umbrella header and sxml/sxml-match.ss for
        # the (sxml match) module) into the source folder.
        for name in os.listdir(patches_dir):
            copy(self, name, src=patches_dir, dst=self.source_folder)

    def generate(self):
        # configure discovers every host dependency through pkg-config.
        PkgConfigDeps(self).generate()
        pkg_config_dir = self.generators_folder
        # The published GTK/pango/cairo recipes do not provide every .pc
        # module the lepton configure script looks for (gdk-3.0, the cairo
        # backends, pangocairo, ...).  Generate thin shims that reuse the
        # dependency package folders; they are searched first.
        shims_dir = os.path.join(self.generators_folder, "pc-shims")
        os.makedirs(shims_dir, exist_ok=True)
        self._write_pkg_config_shims(shims_dir)

        VirtualBuildEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        env = toolchain.environment()
        # Shims must win over the generated pkgconfig directory.
        env.prepend_path("PKG_CONFIG_PATH", shims_dir)
        if os.path.isdir(pkg_config_dir):
            env.prepend_path("PKG_CONFIG_PATH", pkg_config_dir)
        for directory in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            env.append_path("ACLOCAL_PATH", directory)
        # OHOS /tmp may be read-only; keep temporary files in the build tree.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        self._add_guile_environment(env)
        toolchain.generate(env=env)

    def _dep_pkg(self, name):
        dep = self.dependencies[name]
        return dep.package_folder

    def _write_shim(self, directory, filename, text):
        with open(os.path.join(directory, filename), "w",
                  encoding="utf-8") as handle:
            handle.write(text)

    def _write_pkg_config_shims(self, shims_dir):
        gtk = self._dep_pkg("gtk")
        cairo = self._dep_pkg("cairo")
        pango = self._dep_pkg("pango")
        glib = self._dep_pkg("glib")
        libffi = self._dep_pkg("libffi")
        zlib = self._dep_pkg("zlib")

        def header(prefix):
            return ("prefix=%s\nlibdir=${prefix}/lib\n" % (prefix,))

        # gdk-3.0: published gtk recipe exposes gtk+-3.0 only.
        self._write_shim(shims_dir, "gdk-3.0.pc", header(gtk) +
            'includedir=${prefix}/include/gtk-3.0\n'
            'includedir1=${prefix}/include\n\n'
            'Name: GDK\nDescription: GTK+ Graphic Drawing Kit (shim)\n'
            'Version: 3.24.38\n'
            'Requires: glib-2.0 gobject-2.0 gio-2.0 cairo cairo-gobject '
            'pango harfbuzz gdk-pixbuf-2.0 atk fribidi epoxy zlib\n'
            'Libs: -L"${libdir}" -lgdk-3\n'
            'Cflags: -I"${includedir}" -I"${includedir1}"\n')

        # cairo image/backend modules consumed by libleptongui.
        for module in ("cairo-png", "cairo-ft", "cairo-pdf",
                       "cairo-ps", "cairo-svg", "cairo-gobject"):
            requires = ("" if module == "cairo-png"
                        else "Requires: pixman-1 fontconfig freetype2 libpng zlib\n")
            self._write_shim(shims_dir, module + ".pc", header(cairo) +
                'includedir=${prefix}/include/cairo\n'
                'includedir1=${prefix}/include\n\n'
                'Name: %s\nDescription: %s shim\nVersion: 1.18.4\n'
                '%s'
                'Libs: -L"${libdir}" -lcairo -lm -lpthread\n'
                'Cflags: -I"${includedir}" -I"${includedir1}"\n'
                % (module, module, requires))

        # pangocairo: published pango recipe exposes pango.pc only.
        self._write_shim(shims_dir, "pangocairo.pc", header(pango) +
            'includedir=${prefix}/include\n'
            'includedir1=${prefix}/include/pango-1.0\n\n'
            'Name: pangocairo\nDescription: pangocairo shim\n'
            'Version: 1.56.4\n'
            'Libs: -L"${libdir}" -lpango-1.0 -lpangocairo-1.0 -lpangoft2-1.0\n'
            'Cflags: -I"${includedir}" -I"${includedir1}"\n')

        # glib-2.0-unofficial: the published gio-2.0.pc Requires it.
        self._write_shim(shims_dir, "glib-2.0-unofficial.pc", header(glib) +
            'includedir=${prefix}/include\n'
            'includedir1=${prefix}/include/glib-2.0\n'
            'includedir2=${prefix}/lib/glib-2.0/include\n\n'
            'Name: glib-2.0-unofficial\nDescription: glib component shim\n'
            'Version: 2.84.0.1\n'
            'Libs: -L"${libdir}" -lglib-2.0 -lm -lpthread -ldl\n'
            'Cflags: -I"${includedir}" -I"${includedir1}" -I"${includedir2}"\n'
            'Requires: zlib\n')

        self._write_shim(shims_dir, "libffi.pc", header(libffi) +
            'includedir=${prefix}/include\n\n'
            'Name: libffi\nDescription: libffi shim\nVersion: 3.4.4\n'
            'Libs: -L${libdir} -lffi\n'
            'Cflags: -I${includedir}\n')

        self._write_shim(shims_dir, "zlib.pc", header(zlib) +
            'includedir=${prefix}/include\n\n'
            'Name: zlib\nDescription: zlib shim\nVersion: 1.3.1\n'
            'Libs: -L${libdir} -lz\n'
            'Cflags: -I${includedir}\n')

    def _add_guile_environment(self, env):
        """Expose the Guile interpreter to configure/build steps.

        The packaged guile-config/guild are shell scripts and HMDFS denies
        direct shebang execution, so route them through sh explicitly.
        """
        guile = self.dependencies["guile"]
        bin_dir = os.path.join(guile.package_folder, "bin")
        env.prepend_path("PATH", bin_dir)
        env.define("GUILE", os.path.join(bin_dir, "guile"))
        config = unix_path(self, os.path.join(bin_dir, "guile-config"))
        env.define("GUILE_CONFIG", "sh " + shlex.quote(config))
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for lib_dir in dependency.cpp_info.libdirs:
                resolved = lib_dir if os.path.isabs(lib_dir) else os.path.join(
                    dependency.package_folder, lib_dir)
                if os.path.isdir(resolved):
                    env.prepend_path("LD_LIBRARY_PATH", resolved)

    def _make_configure_tmp_writable(self, path):
        """Autoconf's mktemp -d forces mode 0700; HMDFS setgid semantics make
        that directory unwritable for config.status. Use a shared mkdir."""
        private_mktemp = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
        private_mkdir = '(umask 077 && mkdir "$tmp")'
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        if content.count(private_mktemp) != 1 or content.count(private_mkdir) != 1:
            raise ConanException(
                "unexpected Autoconf temporary-directory template in configure")
        content = content.replace(
            private_mktemp, 'tmp=./conf$$-$RANDOM; (umask 007 && mkdir "$tmp") &&')
        content = content.replace(
            private_mkdir, '(umask 007 && mkdir "$tmp")')
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def build(self):
        # Apply the OHOS adaptation patches declared in conandata.yml.
        apply_conandata_patches(self)
        self._make_configure_tmp_writable(
            os.path.join(self.source_folder, "configure"))
        # The Guile package also misses sxml/sxml-match.ss required by the
        # (sxml match) module used by the netlister. Put it on the build-time
        # Guile load path and install it with the package later.
        sxml_dir = os.path.join(self.build_folder, "extra-scheme", "sxml")
        os.makedirs(sxml_dir, exist_ok=True)
        copy(self, "sxml-match.ss", src=self.source_folder,
             dst=os.path.join(self.build_folder, "extra-scheme", "sxml"))

        extra_load_path = unix_path(self, os.path.join(self.build_folder,
                                                       "extra-scheme"))
        env = Environment()
        env.prepend_path("GUILE_LOAD_PATH", extra_load_path)
        with env.vars(self).apply():
            include_flag = "-I" + unix_path(self, self.source_folder)
            # Make `make`-time auxiliary scripts resolvable: configure is run
            # with an absolute path so install_sh etc. become absolute too.
            configure = unix_path(
                self, os.path.join(self.source_folder, "configure"))
            fake_ldconfig = unix_path(self, self._write_fake_ldconfig())
            args = [
                "--prefix=/",
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
                "--with-gtk3",
                "--without-libstroke",
                "--disable-nls",
                "--disable-update-xdg-database",
                "--disable-attrib",
                "USE_LDCONFIG={}".format(fake_ldconfig),
            ]
            self.run('CPPFLAGS="{} $CPPFLAGS" bash {} {}'.format(
                include_flag, shlex.quote(configure), " ".join(args)),
                cwd=self.build_folder, env="conanbuild")
            # A single job avoids make jobserver/FIFO failures on HMDFS.
            self.run("make -j1", cwd=self.build_folder, env="conanbuild")

    def _write_fake_ldconfig(self):
        """OHOS has no ldconfig and its dlopen does not append '.so'. The
        build generates scheme/lepton/m4.scm with the exact sonames from
        `USE_LDCONFIG -p`, so provide a minimal provider for the GTK3 stack.
        """
        bindir = os.path.join(self.build_folder, "fakebin")
        os.makedirs(bindir, exist_ok=True)
        script = os.path.join(bindir, "ldconfig")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(
                "#!/bin/sh\n"
                '# Minimal ldconfig -p replacement used at build time so the\n'
                '# generated (lepton m4) module carries full sonames, which\n'
                '# the OHOS dynamic linker requires (no automatic ".so"\n'
                "# suffix resolution).\n"
                'echo "libglib-2.0.so.0 (libc6,x86-64)"\n'
                'echo "libgobject-2.0.so.0 (libc6,x86-64)"\n'
                'echo "libgtk-3.so.0 (libc6,x86-64)"\n')
        os.chmod(script, 0o755)
        return script

    def package(self):
        # Install directly into the package folder; the configure prefix is
        # "/" and the installed scripts are made relocatable below.
        self.run("make install DESTDIR={}".format(
            shlex.quote(unix_path(self, self.package_folder))),
            cwd=self.build_folder, env="conanbuild")

        # Install the missing (sxml match) module next to the lepton scheme
        # tree; the (sxml match) name resolves via include-from-path.
        scheme_dir = os.path.join(self.package_folder, "share", "lepton-eda",
                                  "scheme", "sxml")
        os.makedirs(scheme_dir, exist_ok=True)
        copy(self, "sxml-match.ss",
             src=self.source_folder, dst=scheme_dir)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        bin_dir = os.path.join(self.package_folder, "bin")
        for name in os.listdir(bin_dir):
            path = os.path.join(bin_dir, name)
            # ELF executables (e.g. lepton-sch2pcb) get signed; the rest are
            # Guile shell scripts that need their baked paths rewritten.
            with open(path, "rb") as handle:
                magic = handle.read(4)
            if magic == b"\x7fELF":
                self._sign_ohos_elf(path)
            else:
                self._make_script_relocatable(path)
        for lib in ("lib",):
            lib_dir = os.path.join(self.package_folder, lib)
            if os.path.isdir(lib_dir):
                for name in os.listdir(lib_dir):
                    if name.endswith((".so", ".so.11", ".so.5")) or \
                       ".so." in name:
                        self._sign_ohos_elf(os.path.join(lib_dir, name))

    @staticmethod
    def _make_script_relocatable(path):
        """The installed lepton-* programs are Guile scripts with the build
        time Guile and prefix paths baked in. Rewrite them so they resolve
        Guile through GUILE/PATH and the scheme tree relative to the script
        location."""
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        original = content
        content = re.sub(
            r'^exec \S+ -s "\$0" "\$@"$',
            'exec "${GUILE:-guile}" -s "$0" "$@"',
            content, count=1, flags=re.M)
        content = re.sub(
            r'\(add-to-load-path "[^"]*/share/lepton-eda/scheme"\)',
            '(add-to-load-path (string-append (dirname (dirname '
            '(car (command-line)))) "/share/lepton-eda/scheme"))',
            content)
        content = re.sub(
            r'\(cons "[^"]*/share/lepton-eda/ccache" %load-compiled-path\)',
            '(cons (string-append (dirname (dirname (car (command-line)))) '
            '"/share/lepton-eda/ccache") %load-compiled-path)',
            content)
        if content != original:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.chmod(path, 0o755)

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or \
            "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or \
            "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output,
             "-selfSign", "1"],
            check=True, timeout=120)
        sections = subprocess.run(
            [readelf, "-SW", output], check=True, capture_output=True,
            text=True, timeout=60).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(
                "Signed packaged library has invalid .codesign count: "
                + path)
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

        package_share = os.path.join(self.package_folder, "share")
        scheme_dir = os.path.join(package_share, "lepton-eda", "scheme")
        ccache_dir = os.path.join(package_share, "lepton-eda", "ccache")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        # OHOS dlopen rejects versioned ".so.N" targets (it only accepts
        # names ending in ".so" or without an extension), so point lepton's
        # FFI override variables at the unversioned library files.
        self.runenv_info.define(
            "LIBLEPTON",
            os.path.join(self.package_folder, "lib", "liblepton.so"))
        self.runenv_info.define(
            "LIBLEPTONGUI",
            os.path.join(self.package_folder, "lib", "libleptongui.so"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # The scheme tree is made visible through the Guile load path so the
        # installed scripts do not depend on the build time prefix.
        self.runenv_info.prepend_path("GUILE_LOAD_PATH", scheme_dir)
        self.runenv_info.prepend_path(
            "GUILE_LOAD_PATH", os.path.join(scheme_dir, "backend"))
        if os.path.isdir(ccache_dir):
            self.runenv_info.prepend_path("GUILE_LOAD_COMPILED_PATH", ccache_dir)
        self.runenv_info.prepend_path(
            "XDG_DATA_DIRS", package_share)
        self.runenv_info.define("GUILE_AUTO_COMPILE", "0")
        # libc++_shared.so from the OHOS SDK must be resolvable at runtime.
        for sdk_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")):
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", sdk_lib)
