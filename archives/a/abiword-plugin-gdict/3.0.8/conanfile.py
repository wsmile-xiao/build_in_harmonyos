#!/usr/bin/env python3
"""Conan recipe for the AbiWord 3.0.8 gdict plugin.

The upstream archive is the complete AbiWord tree. Only the gdict module is
packaged; the AbiWord host ABI remains a separate runtime dependency.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AbiwordPluginGdictConan(ConanFile):
    name = "abiword-plugin-gdict"
    version = "3.0.8"
    description = "AbiWord gdict dictionary plugin"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/World/AbiWord"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)
        # The GitLab archive omits generated Autotools files and the
        # Autoconf Archive/libgcrypt macros used by configure.ac.
        macro_dir = os.path.join(self.recipe_folder, "m4")
        if os.path.isdir(macro_dir):
            shutil.copytree(
                macro_dir,
                os.path.join(self.export_sources_folder, "m4"),
                dirs_exist_ok=True,
            )

    def requirements(self):
        # The plugin is compiled from the AbiWord source tree and leaves host
        # ABI symbols undefined for AbiWord to resolve at dlopen time. The
        # host package is therefore a runtime contract, not a build require.
        self.requires("glib/2.84.0.1.1", override=True)
        self.requires("boost/1.90.0.3")
        self.requires("libgsf/1.14.58")
        self.requires("wv/1.2.9")
        self.requires("libxslt/1.1.45.2")
        # libgsf and libxslt currently publish recipes with different libxml2
        # patch-level pins; keep the OHOS .1 package as the graph authority.
        self.requires("libxml2/2.15.3.1", override=True)
        self.requires("fribidi/1.0.16")
        self.requires("libpng/1.6.58")
        self.requires("libjpeg/10")
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        # GitLab source archives do not include configure/Makefile.in.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency_paths(self):
        includes = []
        libdirs = []
        for dep in self.dependencies.values():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            for include in dep.cpp_info.includedirs:
                includes.append(include if os.path.isabs(include)
                                else os.path.join(package_folder, include))
            for libdir in dep.cpp_info.libdirs:
                libdirs.append(libdir if os.path.isabs(libdir)
                               else os.path.join(package_folder, libdir))

        # These packages install public headers below their generic include
        # directory, while their aggregate Conan metadata only exports the
        # generic directory. AbiWord includes these headers directly.
        nested_includes = {
            "fribidi": (os.path.join("include", "fribidi"),),
            "glib": (
                os.path.join("include", "glib-2.0"),
                os.path.join("lib", "glib-2.0", "include"),
            ),
        }
        for dep_name, paths in nested_includes.items():
            package_folder = self.dependencies[dep_name].package_folder
            for path in paths:
                include = os.path.join(package_folder, path)
                if os.path.isdir(include) and include not in includes:
                    includes.append(include)
        return includes, libdirs

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-plugins=gdict",
            "enable_gdict=yes",
            "--disable-default-plugins",
            "--with-gtk2=no",
            # OHOS is not recognised by old config.guess files.
            "--build=aarch64-linux",
            "--host=aarch64-linux",
        ])

        boost_root = self.dependencies["boost"].package_folder
        tc.configure_args.append(f"--with-boost={boost_root}")
        includes, libdirs = self._dependency_paths()
        cppflags = " ".join(f"-I{path}" for path in includes)
        ldflags = " ".join(f"-L{path}" for path in libdirs)
        if includes:
            tc.configure_args.append("CPPFLAGS=" + cppflags)
        if libdirs:
            tc.configure_args.append("LDFLAGS=" + ldflags)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "DEPS_CFLAGS=" + cppflags,
                "DEPS_LIBS=" + ldflags + " -lpng -ljpeg",
            ])
        tc.configure_args.append(f"PKG_CONFIG_PATH={self.generators_folder}")
        tc.generate()

        if str(self.settings.os) == "OHOS":
            tools = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            compiler = tools.get("c", "clang")
            tool_dir = os.path.dirname(compiler)
            env = Environment()
            env.prepend_path("PATH", tool_dir)
            for variable, executable in {
                "LD": "ld.lld",
                "AR": "llvm-ar",
                "NM": "llvm-nm",
                "RANLIB": "llvm-ranlib",
                "STRIP": "llvm-strip",
                "OBJDUMP": "llvm-objdump",
            }.items():
                path = os.path.join(tool_dir, executable)
                if os.path.exists(path):
                    env.define_path(variable, path)
            env.define_path("PERL", os.path.join(tool_dir, "perl"))
            autoconf_candidates = sorted(glob.glob(
                "/data/service/hnp/autoconf.org/autoconf_*/bin/autoconf"),
                reverse=True,
            )
            if autoconf_candidates:
                env.prepend_path("PATH", os.path.dirname(autoconf_candidates[0]))
            m4_candidates = sorted(glob.glob(
                "/data/service/hnp/m4.org/m4_*/bin/m4"),
                reverse=True,
            )
            if m4_candidates:
                env.prepend_path("PATH", os.path.dirname(m4_candidates[0]))
                env.define_path("M4", m4_candidates[0])
            pkg_config_candidates = sorted(glob.glob(
                "/data/service/hnp/pkg-config.org/"
                "pkg-config_*/bin/pkg-config"), reverse=True)
            pkg_config = (pkg_config_candidates[0]
                          if pkg_config_candidates else
                          shutil.which("pkg-config") or shutil.which("pkgconf"))
            if pkg_config:
                env.define_path("PKG_CONFIG", pkg_config)
            make = shutil.which("make")
            if not make:
                make_candidates = sorted(glob.glob(
                    "/data/service/hnp/make.org/make_*/bin/make"),
                    reverse=True)
                if make_candidates:
                    make = make_candidates[0]
            if make:
                env.prepend_path("PATH", os.path.dirname(make))
            env.vars(self).save_script("abiword_plugin_gdict_linker")

    def _stage_libtool_data(self):
        libtool_root = self.dependencies.build["libtool"].package_folder
        pkgdatadir = os.path.join(
            os.environ.get("TMPDIR", self.build_folder),
            "gdict-libtool-" + os.path.basename(self.build_folder),
        )
        for subdir in ("build-aux", "m4", "libltdl"):
            os.makedirs(os.path.join(pkgdatadir, subdir), exist_ok=True)

        source_aux = os.path.join(libtool_root, "share", "libtool", "build-aux")
        for filename in os.listdir(source_aux):
            shutil.copy2(
                os.path.join(source_aux, filename),
                os.path.join(pkgdatadir, "build-aux", filename),
            )

        source_m4 = os.path.join(libtool_root, "share", "aclocal")
        for filename in os.listdir(source_m4):
            if filename.endswith(".m4"):
                shutil.copy2(
                    os.path.join(source_m4, filename),
                    os.path.join(pkgdatadir, "m4", filename),
                )

        # libtoolize checks that all three data directories are non-empty.
        with open(os.path.join(pkgdatadir, "libltdl", "keep.txt"), "w") as handle:
            handle.write("x\n")
        return pkgdatadir

    def _run_autogen(self):
        # Run the generators separately. This avoids the HMDFS autoreconf/m4f
        # issue and makes the tool_requires environment explicit.
        source = self.source_folder
        macro_dir = os.path.join(source, "m4")
        libtool_data = (self._stage_libtool_data()
                        if str(self.settings.os) == "OHOS" else None)
        # Generate the m4 include fragments consumed by configure.ac.
        self.run(
            'sh "{}/autogen-common.sh"'.format(source),
            cwd=source,
            env="conanbuild",
        )
        self.run(
            (('aclocal_dir="${{ACLOCAL%/*}}"; '
              'automake_prefix="${{aclocal_dir%/*}}"; '
              'ACLOCAL_PATH="{}:$ACLOCAL_PATH" '
              '"/data/service/hnp/bin/perl" "$aclocal_dir/.aclocal-real" '
              '--automake-acdir="$automake_prefix/share/aclocal-1.18" '
              '--system-acdir="$automake_prefix/share/aclocal" --force')
             if str(self.settings.os) == "OHOS" else
             'ACLOCAL_PATH="{}:$ACLOCAL_PATH" '
             '"${{ACLOCAL:-aclocal}}" --force').format(macro_dir),
            cwd=source,
            env="conanbuild",
        )
        self.run("autoconf -o configure configure.ac", cwd=source, env="conanbuild")
        self.run("autoheader", cwd=source, env="conanbuild")
        self.run(
            (('libtoolize="${LIBTOOLIZE:-libtoolize}"; '
              '_lt_pkgdatadir="' + libtool_data + '" '
              'sh "$libtoolize"'
              if str(self.settings.os) == "OHOS" else
              '"${LIBTOOLIZE:-libtoolize}"') +
             ' --copy --force --install'),
            cwd=source,
            env="conanbuild",
        )
        self.run(
            (('automake_dir="${AUTOMAKE%/*}"; '
              'automake_prefix="${automake_dir%/*}"; '
              '"/data/service/hnp/bin/perl" "$automake_dir/.automake-real" '
              '--libdir="$automake_prefix/share/automake-1.18" '
              '--add-missing --copy --no-force')
             if str(self.settings.os) == "OHOS" else
             '"${AUTOMAKE:-automake}" '
             '--add-missing --copy --no-force'),
            cwd=source,
            env="conanbuild",
        )

    def _prepare_ohos_source(self):
        plugin_source = os.path.join(
            self.source_folder, "plugins", "gdict", "unix", "GdictAbiPlugin.cpp",
        )
        unix_includes = (
            '#include "xap_UnixFrameImpl.h"\n'
            '#include "xap_UnixDialogHelper.h"\n'
            '#include "xap_Gtk2Compat.h"\n'
        )
        replace_in_file(
            self,
            plugin_source,
            unix_includes,
            "#ifndef USE_FORK_AND_EXEC_METHOD\n" + unix_includes + "#endif\n",
        )
        makefile = os.path.join(
            self.source_folder, "plugins", "gdict", "Makefile.am",
        )
        replace_in_file(
            self,
            makefile,
            "gdict_la_LDFLAGS = \\\n"
            "\t-avoid-version \\\n"
            "\t-module \\\n"
            "\t-no-undefined",
            "gdict_la_LDFLAGS = \\\n"
            "\t-avoid-version \\\n"
            "\t-module",
        )
        # A standalone module cannot link the in-tree AbiWord library because
        # that host is intentionally not built by this recipe. Its plugin ABI
        # symbols remain undefined and are resolved by AbiWord at dlopen time.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "plugins", "gdict", "plugin.m4"),
            "GDICT_LIBS='${PLUGIN_LIBS}'", "GDICT_LIBS=''",
        )

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._prepare_ohos_source()
        self._run_autogen()
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            replace_in_file(
                self, os.path.join(self.source_folder, "configure"),
                "umask 077", "umask 022")
            self.run('sh "{}/configure" {}'.format(
                self.source_folder, autotools._configure_args))
            # The fork/exec implementation has no GTK calls. Keeping this
            # compatibility macro makes generic AbiWord headers include
            # gtk/gtk.h solely to typedef AbiNativeWidget, pulling the full
            # GUI stack into this standalone plugin build.
            replace_in_file(
                self, os.path.join(self.build_folder, "config.h"),
                "#define TOOLKIT_GTK_ALL 1",
                "/* #undef TOOLKIT_GTK_ALL */")
        else:
            autotools.configure()
        # There is no gdict-specific upstream test target. Build only the
        # plugin module; test_package performs the ABI/ELF smoke test.
        autotools.make(target="-C plugins/gdict")

    def package(self):
        plugin_build = os.path.join(self.build_folder, "plugins", "gdict", ".libs")
        plugin_dst = os.path.join(self.package_folder, "lib", "abiword", "plugins")
        os.makedirs(plugin_dst, exist_ok=True)
        for filename in os.listdir(plugin_build) if os.path.isdir(plugin_build) else []:
            if filename.startswith("gdict") and ".so" in filename:
                copy(self, filename, plugin_build, plugin_dst)

    def package_info(self):
        # A plugin is loaded by AbiWord, not linked as a normal consumer lib.
        self.cpp_info.libs = []
        self.runenv_info.define_path(
            "ABIWORD_PLUGINS_DIR",
            os.path.join(self.package_folder, "lib", "abiword", "plugins"),
        )
