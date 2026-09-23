#!/usr/bin/env python3
"""Conan recipe for libvips 8.18.4, a demand-driven image processing library.

Meson build. Dependency surface is intentionally narrowed to the libraries
that are already adapted for OHOS in this repository: glib, expat, zlib,
lcms2, libpng, libexif, orc. All other optional loaders (jpeg/webp/tiff/
heif/fftw/rsvg/...) are disabled so the cross-compiled package focuses on a
reproducible core.
"""

import os
import posixpath
import re
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    get,
    replace_in_file,
    rmdir,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibvipsConan(ConanFile):
    name = "libvips"
    version = "8.18.4"
    description = (
        "libvips is a demand-driven, horizontally threaded image processing library"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://www.libvips.org"
    url = "https://github.com/libvips/libvips"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "deprecated": [True, False],
        "with_exif": [True, False],
        "with_lcms": [True, False],
        "with_orc": [True, False],
        "with_png": [True, False],
        "with_zlib": [True, False],
        "with_nsgif": [True, False],
        "with_ppm": [True, False],
        "with_analyse": [True, False],
        "with_radiance": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "deprecated": True,
        "with_exif": True,
        "with_lcms": True,
        "with_orc": True,
        "with_png": True,
        "with_zlib": True,
        "with_nsgif": True,
        "with_ppm": True,
        "with_analyse": True,
        "with_radiance": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "libvips target adaptation is validated only for AArch64"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("glib/2.88.3", transitive_headers=True, transitive_libs=True)
        self.requires("expat/2.8.2.1")
        if self.options.with_exif:
            self.requires("libexif/0.6.26.1")
        if self.options.with_lcms:
            self.requires("lcms2/2.19")
        if self.options.with_orc:
            self.requires("orc/0.4.42")
        if self.options.with_png:
            self.requires("libpng/1.6.58.2")
        if self.options.with_zlib:
            self.requires("zlib/1.3.2")

    def build_requirements(self):
        # Pin the exact published version (gulkan/0.15.1 precedent): the L0i
        # registry probe fails to resolve a version range when multiple meson
        # versions are published, misreporting "registry unreachable".
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # glib's published .pc lacks glib_mkenums/glib_genmarshal variables,
        # which meson's gnome.mkenums() needs (include/vips/meson.build).
        # Provide them via runpy wrappers so the cross build can execute the
        # target's Python tool scripts on the build machine (atk precedent).
        self._augment_glib_pkg_config()

        tc = MesonToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            tools = self._resolve_llvm_tools(
                executables, target_os=self.settings.os
            )
            tc.ar = tools["ar"]
            tc.strip = tools["strip"]
            tc.binaries["ranlib"] = tools["ranlib"]
            tc.binaries["nm"] = tools["nm"]
            tc.binaries["objcopy"] = tools["objcopy"]

        true_false = lambda value: "true" if value else "false"
        enabled_disabled = lambda value: "enabled" if value else "disabled"

        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["wrap_mode"] = "nofallback"
        # libvips core switches
        tc.project_options["deprecated"] = true_false(self.options.deprecated)
        tc.project_options["examples"] = "false"
        # The C++ binding is not packaged; the project still requires a C++
        # compiler at configure time, which the OHOS clang toolchain provides.
        tc.project_options["cplusplus"] = "false"
        tc.project_options["docs"] = "false"
        tc.project_options["cpp-docs"] = "false"
        tc.project_options["modules"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "false"
        # External library features (all optional loaders disabled except the
        # dependency set above; --wrap-mode=nofallback keeps the build hermetic)
        for option in (
            "archive", "cfitsio", "cgif", "fftw", "fontconfig", "heif",
            "heif-module", "highway", "imagequant", "jpeg", "jpeg-xl",
            "jpeg-xl-module", "magick", "magick-module", "matio", "nifti",
            "openexr", "openjpeg", "openslide", "openslide-module",
            "pangocairo", "pdfium", "poppler", "poppler-module", "quantizr",
            "raw", "rsvg", "spng", "tiff", "uhdr", "webp",
        ):
            tc.project_options[option] = "disabled"
        tc.project_options["exif"] = enabled_disabled(self.options.with_exif)
        tc.project_options["lcms"] = enabled_disabled(self.options.with_lcms)
        tc.project_options["orc"] = enabled_disabled(self.options.with_orc)
        tc.project_options["png"] = enabled_disabled(self.options.with_png)
        tc.project_options["zlib"] = enabled_disabled(self.options.with_zlib)
        # In-tree formats that need no external library
        tc.project_options["nsgif"] = true_false(self.options.with_nsgif)
        tc.project_options["ppm"] = true_false(self.options.with_ppm)
        tc.project_options["analyze"] = true_false(self.options.with_analyse)
        tc.project_options["radiance"] = true_false(self.options.with_radiance)
        tc.generate()

    def _augment_glib_pkg_config(self):
        """Add glib_mkenums/glib_genmarshal variables to the generated
        glib-2.0.pc so meson's gnome.mkenums() can find the host tools.
        """
        glib_mkenums = self._create_python_tool_wrapper("glib-mkenums")
        glib_genmarshal = self._create_python_tool_wrapper("glib-genmarshal")
        variables = {
            "glib-2.0": [
                f"glib_mkenums={glib_mkenums}",
                f"glib_genmarshal={glib_genmarshal}",
            ],
        }
        for pc_name, entries in variables.items():
            pc_file = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            inserted = []
            for entry in entries:
                key = entry.split("=", 1)[0] + "="
                if key not in content:
                    inserted.append(entry)
            if not inserted:
                continue
            name_index = content.find("\nName:")
            addition = "\n" + "\n".join(inserted)
            if name_index >= 0:
                content = content[:name_index] + addition + content[name_index:]
            else:
                content = "\n".join(inserted) + "\n" + content
            with open(pc_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _create_python_tool_wrapper(self, tool_name):
        """Wrap a target-glib Python tool (glib-mkenums etc.) in a runpy
        launcher executed by the build-machine python, so gnome.mkenums()
        can run it despite the .pc / shebang pointing into the OHOS sysroot.
        """
        tool_path = None
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                tool_path = candidate
                break
        if not tool_path:
            return f"${{bindir}}/{tool_name}"
        wrapper_path = os.path.join(self.generators_folder, f"{tool_name}-python")
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"#!{sys.executable}\n"
                "import runpy\n"
                "import sys\n"
                f"sys.argv = [{tool_path!r}] + sys.argv[1:]\n"
                f"runpy.run_path({tool_path!r}, run_name='__main__')\n"
            )
        os.chmod(wrapper_path, 0o755)
        return wrapper_path.replace("\\", "/")

    def _patch_sources(self):
        apply_conandata_patches(self)
        meson_build = os.path.join(self.source_folder, "meson.build")
        # Upstream test/ references Python and a git-submodule image fixture
        # directory that is absent from the release archive, and fuzz/ targets
        # need libFuzzer. Drop both subdirectories so the cross build is clean.
        replace_in_file(self, meson_build, "subdir('test')", "")
        replace_in_file(self, meson_build, "subdir('fuzz')", "")
        # Disable NLS: the OHOS musl libc exports ngettext, so the probe below
        # sets ENABLE_NLS in config.h, yet gettext()/libintl.h are not usable,
        # turning every _() call in tools/ into an undeclared gettext error.
        replace_in_file(
            self,
            meson_build,
            """if cc.has_function('ngettext')
    cfg_var.set('ENABLE_NLS', true)
    have_bind_textdomain_codeset = cc.has_function('bind_textdomain_codeset')
else
    libintl_dep = cc.find_library('intl', required: false)
    if libintl_dep.found()
        other_deps += libintl_dep
        cfg_var.set('ENABLE_NLS', true)
        have_bind_textdomain_codeset = cc.has_function('bind_textdomain_codeset', prefix: '#include <libintl.h>', dependencies: libintl_dep)
    else
        have_bind_textdomain_codeset = false
    endif
endif""",
            """have_bind_textdomain_codeset = false""",
        )
        # The CLI tools include <glib/gi18n.h> directly: its _()/N_() macros
        # expand to gettext() unconditionally, which the OHOS musl libc does
        # not provide (no usable libintl.h), even with ENABLE_NLS unset.  Route
        # them through vips/intl.h, which maps _()/N_() to identity when
        # ENABLE_NLS is not defined.
        for tool in ("vips.c", "vipsedit.c", "vipsheader.c", "vipsthumbnail.c"):
            replace_in_file(
                self,
                os.path.join(self.source_folder, "tools", tool),
                "#include <glib/gi18n.h>",
                "#include <vips/intl.h>",
            )

    def build(self):
        self._patch_sources()
        self._set_ohos_tmpdir()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        self._set_ohos_tmpdir()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        Meson(self).install()
        # Keep the runtime library surface; drop generated pc/docs directories.
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "vips")
        self.cpp_info.set_property("cmake_target_name", "vips::vips")
        self.cpp_info.set_property("pkg_config_name", "vips")
        self.cpp_info.libs = ["vips"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.requires = [
            "glib::glib",
            "glib::gio",
            "glib::gobject",
            "expat::expat",
        ]
        if self.options.with_exif:
            self.cpp_info.requires.append("libexif::libexif")
        if self.options.with_lcms:
            self.cpp_info.requires.append("lcms2::lcms2")
        if self.options.with_orc:
            self.cpp_info.requires.append("orc::orc")
        if self.options.with_png:
            self.cpp_info.requires.append("libpng::libpng")
        if self.options.with_zlib:
            self.cpp_info.requires.append("zlib::zlib")

    @staticmethod
    def _require_absolute_tool(value, label, target_posix=False):
        if not isinstance(value, (str, os.PathLike)):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] must be a path"
            )
        path = os.fspath(value)
        if target_posix:
            if not posixpath.isabs(path):
                raise ConanInvalidConfiguration(
                    f"tools.build:compiler_executables[{label!r}] must be an "
                    "absolute POSIX target path"
                )
            return posixpath.normpath(path)
        if not os.path.isabs(path) or not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] must name an "
                "absolute regular file"
            )
        if not os.access(path, os.X_OK):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] is not executable"
            )
        return os.path.normpath(path)

    @classmethod
    def _resolve_llvm_tools(cls, executables, target_os=None):
        if not isinstance(executables, dict):
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must be a dictionary"
            )
        target_posix = str(target_os) == "OHOS"
        compiler = cls._require_absolute_tool(
            executables.get("c"), "c", target_posix=target_posix
        )
        compiler_name = (
            posixpath.basename(compiler) if target_posix else os.path.basename(compiler)
        )
        match = re.fullmatch(r"clang(?:-([0-9]+))?", compiler_name)
        if match is None:
            raise ConanInvalidConfiguration(
                "the configured C compiler must be clang or clang-<version>"
            )
        suffix = f"-{match.group(1)}" if match.group(1) else ""
        compiler_dir = (
            posixpath.dirname(compiler) if target_posix else os.path.dirname(compiler)
        )
        resolved = {}
        for name in ("ar", "ranlib", "nm", "objcopy", "strip"):
            configured = executables.get(name)
            if configured:
                resolved[name] = cls._require_absolute_tool(
                    configured, name, target_posix=target_posix
                )
                continue
            if target_posix:
                resolved[name] = posixpath.join(
                    compiler_dir, f"llvm-{name}{suffix}"
                )
                continue
            candidates = (
                os.path.join(compiler_dir, f"llvm-{name}{suffix}"),
                os.path.join(compiler_dir, f"llvm-{name}"),
            )
            for candidate in dict.fromkeys(candidates):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    resolved[name] = os.path.normpath(candidate)
                    break
            if name not in resolved:
                raise ConanInvalidConfiguration(
                    f"cannot resolve llvm-{name} beside the configured C compiler"
                )
        return resolved

    def _set_ohos_tmpdir(self):
        if str(self.settings.os) != "OHOS":
            return
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
