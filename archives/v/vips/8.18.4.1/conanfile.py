#!/usr/bin/env python3
"""Conan recipe for vips 8.18.4.1.

Same upstream source as 8.18.4, but with the JPEG and PNG image codecs enabled
(libjpeg-turbo / libpng / zlib), so consumers can actually load and save the
image formats every real application needs.

Why a new adaptation revision instead of 8.18.4: the 8.18.4 package was built
with every optional codec hard-disabled and the recipe exposes no codec options
(the disable list is not user-selectable), so its published binary cannot decode
a single JPEG or PNG — `vips_image_new_from_file()` returns
"… is not a known file format". Adding the capability changes the built artifact,
which the archive convention expresses as a new version directory
(cf. glib 2.84.0.1 / 2.84.0.2).

Only jpeg/png/zlib are turned on; the remaining optional stacks (tiff, webp,
magick, heif, …) stay disabled until each of their Conan packages is confirmed
in the product registry. `modules` stays disabled, so both loaders are linked
into libvips itself and need no runtime module-path lookup.
"""
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class VipsConan(ConanFile):
    name = "vips"
    version = "8.18.4.1"
    description = "A fast image processing library with low memory needs"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.libvips.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("expat/2.8.2.1", transitive_headers=True, transitive_libs=True)
        # Image codecs: libvips' meson asks for pkg-config `libjpeg` / `libpng`
        # / `zlib`; PkgConfigDeps exports exactly those names.
        self.requires("libjpeg-turbo/3.2.0", transitive_libs=True)
        # libpng/1.6.58 配方 requires zlib/1.3.1.1，而 glib2/2.88.0 声明的是
        # zlib/1.3.1 → 图中必然 "Version conflict"（CI #44364 实测）。统一到
        # **1.3.1.1**（PIC 变体，E005）而非 1.3.1：制品仓 libpng/1.6.58 二进制
        # 正是基于 zlib/1.3.1.1 构建，override 到 1.3.1 会让 libpng 回退到源码
        # 构建并撞上沙箱 configure 失败（同 abiword-plugin-pdf 3.0.8 /
        # gmime 3.0.6 / awf-gtk 4.2.0 的既有处理）。
        self.requires("libpng/1.6.58", transitive_libs=True)
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._create_glib_pkg_config_aliases()

        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["modules"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "false"
        tc.project_options["docs"] = "false"
        tc.project_options["cpp-docs"] = "false"
        tc.project_options["examples"] = "false"
        tc.project_options["cplusplus"] = "false"
        for feature in self._disabled_optional_features():
            tc.project_options[feature] = "disabled"
        # Enabled codecs (kept out of _disabled_optional_features on purpose).
        for feature in ("jpeg", "png", "zlib"):
            tc.project_options[feature] = "enabled"
        tc.generate()
        self._inject_archive_tools()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        self._patch_config_h_for_ohos()
        meson.build()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["vips"]
        # Only direct (non-override) requirements may be listed here: conan
        # validates both directions and rejects a reference to a package that
        # is present merely as an override. zlib is declared with override=True
        # (graph unification to the PIC variant), so it must NOT be listed —
        # consumers resolve it through libpng/glib2 (same handling as gmime 3.0.6).
        self.cpp_info.requires = [
            "glib2::glib2",
            "expat::expat",
            "libjpeg-turbo::libjpeg-turbo",
            "libpng::libpng",
        ]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "vips")
        self.cpp_info.set_property("cmake_target_name", "vips::vips")
        self.cpp_info.set_property("pkg_config_name", "vips")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    @staticmethod
    def _disabled_optional_features():
        # jpeg / png / zlib are deliberately absent: this revision enables them.
        return [
            "archive",
            "cfitsio",
            "cgif",
            "exif",
            "fftw",
            "fontconfig",
            "heif",
            "heif-module",
            "highway",
            "imagequant",
            "jpeg-xl",
            "jpeg-xl-module",
            "lcms",
            "magick",
            "magick-module",
            "matio",
            "nifti",
            "openexr",
            "openjpeg",
            "openslide",
            "openslide-module",
            "orc",
            "pangocairo",
            "pdfium",
            "poppler",
            "poppler-module",
            "quantizr",
            "raw",
            "rsvg",
            "spng",
            "tiff",
            "uhdr",
            "webp",
        ]

    def _create_glib_pkg_config_aliases(self):
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        aliases = {
            "gio-2.0.pc": "gio-2.0",
            "gobject-2.0.pc": "gobject-2.0",
        }
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        for variable, executable in {
            "glib_genmarshal": "glib-genmarshal",
            "glib_mkenums": "glib-mkenums",
        }.items():
            if not re.search(rf"^{variable}=", content, flags=re.M):
                tool = self._stage_glib_tool(content, executable)
                content = content.replace(
                    "\nName:",
                    f"\n{variable}={tool}\nName:",
                    1,
                )
        with open(glib_pc, "w", encoding="utf-8") as target:
            target.write(content)
        for filename, name in aliases.items():
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(os.path.join(self.generators_folder, filename), "w", encoding="utf-8") as target:
                target.write(alias)

    def _inject_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "")
        ranlib = executables.get("ranlib") or (os.path.join(bindir, "llvm-ranlib") if bindir else "")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        if not ar:
            ar = shutil.which("llvm-ar") or shutil.which("ar")
        if not ar:
            raise ConanInvalidConfiguration("Meson needs ar/llvm-ar for libvips")
        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        tools = f"[binaries]\nar = '{ar}'\n"
        if ranlib and os.path.isfile(ranlib):
            tools += f"ranlib = '{ranlib}'\n"
        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content.replace("[binaries]\n", tools, 1))

    def _stage_glib_tool(self, pc_content, executable):
        prefix_match = re.search(r"^prefix=(.+)$", pc_content, flags=re.M)
        if not prefix_match:
            return f"${{bindir}}/{executable}"
        source = os.path.join(prefix_match.group(1).strip(), "bin", executable)
        if not os.path.isfile(source):
            return f"${{bindir}}/{executable}"
        target = os.path.join(self.generators_folder, executable)
        shutil.copyfile(source, target)
        os.chmod(target, 0o755)
        python = (shutil.which("python3") or sys.executable).replace("\\", "/")
        target = target.replace("\\", "/")
        wrapper = self._build_python_tool_wrapper(executable, python, target)
        return wrapper.replace("\\", "/")

    def _build_python_tool_wrapper(self, executable, python, script):
        compiler = (
            self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ).get("c") or shutil.which("cc") or shutil.which("clang")
        if not compiler:
            return script
        wrapper = os.path.join(self.generators_folder, f"{executable}-wrapper")
        source = f"{wrapper}.c"
        with open(source, "w", encoding="utf-8") as wrapper_source:
            wrapper_source.write(
                '#include <stdio.h>\n'
                '#include <stdlib.h>\n'
                '#include <unistd.h>\n'
                'int main(int argc, char **argv) {\n'
                f'    const char *python = "{self._c_string(python)}";\n'
                f'    const char *script = "{self._c_string(script)}";\n'
                '    char **cmd = calloc((size_t)argc + 2, sizeof(char *));\n'
                '    if (!cmd) return 127;\n'
                '    cmd[0] = (char *)python;\n'
                '    cmd[1] = (char *)script;\n'
                '    for (int i = 1; i < argc; ++i) cmd[i + 1] = argv[i];\n'
                '    cmd[argc + 1] = NULL;\n'
                '    execv(python, cmd);\n'
                '    perror("execv");\n'
                '    return 127;\n'
                '}\n'
            )
        self.run(f'"{compiler}" "{source}" -o "{wrapper}"')
        os.chmod(wrapper, 0o755)
        return wrapper

    @staticmethod
    def _c_string(value):
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _patch_config_h_for_ohos(self):
        if self.settings.os != "OHOS":
            return
        config_h = os.path.join(os.path.dirname(self.generators_folder), "config.h")
        if not os.path.isfile(config_h):
            return
        fallback = (
            "\n#ifndef ENABLE_NLS\n"
            "#ifndef gettext\n"
            "#define gettext(String) (String)\n"
            "#endif\n"
            "#ifndef ngettext\n"
            "#define ngettext(Singular, Plural, Number) "
            "(((Number) == 1) ? (Singular) : (Plural))\n"
            "#endif\n"
            "#endif\n"
        )
        with open(config_h, encoding="utf-8") as config:
            content = config.read()
        if "#define gettext(String) (String)" in content:
            return
        with open(config_h, "a", encoding="utf-8") as config:
            config.write(fallback)
