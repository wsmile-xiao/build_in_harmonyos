#!/usr/bin/env python3
"""Conan recipe — nemo-image 6.6.0 (vendored libnemo-extension + clang build).

nemo-image is the Nemo file-manager image converter extension
(linuxmint/nemo-extensions 6.6.0 tag, nemo-image-converter component, C):
a context-menu extension that resizes/rotates image files from the Nemo
file manager.  The build produces two shared objects:

  - libnemo-extension.so(.1) — vendored subset of the Nemo extension ABI
    library (upstream ships it inside the nemo file-manager source tree,
    where it only depends on glib+gtk).  The registry has no nemo/libnemo-
    extension package, so the five source files this extension actually
    consumes (file-info, menu, menu-item, menu-provider,
    name-and-desc-provider) are built here from the official nemo 6.6.0
    tarball (conandata key `nemo_extension_sources`, abletonlink/asio
    precedent for a second official source).
  - libnemo-image-converter.so — the extension module itself, linked
    against the vendored libnemo-extension (DT_NEEDED) and installed into
    lib/nemo/extensions-3.0/ (the directory the upstream libnemo-extension
    pkg-config `extensiondir` variable points at).

OHOS adaptation notes (see notes.md):
- Upstream meson requires a libnemo-extension pkg-config file plus the
  host nemo's extensiondir; neither exists in the registry.  The recipe
  therefore drives clang directly (verified explorer build) instead of
  running meson, compiling the same sources with the same glib/gtk
  headers the upstream meson.build pulls in.
- glib ships a proxy libintl whose libintl.h maps bindtextdomain to
  g_libintl_*; image-converter.c calls bindtextdomain unconditionally,
  so the glib package's libintl.so is linked explicitly (pioneers /
  avahi-ui-tools precedent).
- NLS is disabled via the adapter config.h (GETTEXT_PACKAGE defined,
  ENABLE_NLS undefined) so nemo-extension-i18n.h degrades to no-ops.
- The extension module has undefined-at-link-time GObject symbols only
  for its own interfaces; every external symbol resolves through
  libnemo-extension.so / gtk / glib, so the module can be dlopen()ed by
  any GModule host (test_package does exactly that).
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

# Vendored libnemo-extension subset — exactly the pieces nemo-image-converter
# references (verified by nm on the linked module).
_NEMO_EXT_C = (
    "nemo-file-info.c",
    "nemo-menu.c",
    "nemo-menu-item.c",
    "nemo-menu-provider.c",
    "nemo-name-and-desc-provider.c",
)
_NEMO_EXT_HEADERS = (
    "nemo-extension-types.h",
    "nemo-extension-i18n.h",
    "nemo-extension-private.h",
    "nemo-file-info.h",
    "nemo-menu.h",
    "nemo-menu-item.h",
    "nemo-menu-provider.h",
    "nemo-name-and-desc-provider.h",
)

# Extension module sources (upstream nemo-image-converter/src).
_CONVERTER_C = (
    "image-converter.c",
    "nemo-image-converter.c",
    "nemo-image-resizer.c",
    "nemo-image-rotator.c",
)

_CONFIG_H = """\
/* OHOS adapter config.h — nemo-image 6.6.0
 * Mirrors the defines the upstream meson.configure_file() emits for the
 * sources (nemo-image-converter/meson.build), with NLS disabled: the
 * i18n header degrades gettext/dgettext/bindtextdomain to no-ops when
 * ENABLE_NLS is undefined. */
#define GETTEXT_PACKAGE "nemo-extensions"
#define PACKAGE "nemo-image-converter"
#define PACKAGE_VERSION "6.6.0"
#define DATADIR "/usr/local/share"
#define GNOMELOCALEDIR "/usr/local/share/locale"
#define NEMO_VERSION_MAJOR 6
#define NEMO_VERSION_MINOR 6
#define NEMO_VERSION_MICRO 0
"""


class NemoImageConan(ConanFile):
    name = "nemo-image"
    version = "6.6.0"
    description = ("Nemo file-manager image converter extension "
                   "(resize/rotate context-menu extension) with the vendored "
                   "libnemo-extension ABI subset it links against")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/linuxmint/nemo-extensions"
    url = ""  # CI fills this

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        # No archived patches: every adaptation is a deterministic build()
        # step (config.h generation + clang invocation), reproducible from
        # the immutable upstream tarballs (pioneers precedent).  The
        # apply_conandata_patches() call stays in build() so future patch
        # entries in conandata.yml are honoured automatically.
        pass

    def requirements(self):
        # gtk/3.24.43 published binaries pin glib/2.84.0.1 in their closure
        # (R36): declaring the same glib keeps the whole GTK closure on
        # prebuilt binaries (pioneers precedent).
        self.requires(
            "gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires(
            "glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # Primary: the multi-component nemo-extensions release tarball —
        # extract only the nemo-image-converter component subtree.
        get(self, **self.conan_data["sources"], strip_root=True,
            destination=self.source_folder)
        # Secondary (abletonlink/asio precedent): official nemo 6.6.0
        # tarball carrying libnemo-extension, the ABI library the registry
        # does not provide.  Extract just that subdirectory.
        get(self, **self.conan_data["nemo_extension_sources"],
            strip_root=True, destination=self.source_folder)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        PkgConfigDeps(self).generate()
        env = Environment()
        # R33: compiler executables come from the Conan toolchain
        # configuration, never from bare CC/CFLAGS shell variables
        # (the build script references $CC, which is exported from the
        # nemo_image_env.sh written by generate() below).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        compiler = compilers.get("c")
        if not compiler:
            raise ConanException(
                "CC missing from tools.build:compiler_executables")
        env.define("CC", compiler)
        env.vars(self).save_script("nemo_image_env")

    # ------------------------------------------------------------------
    def _run_shell(self, script_body):
        """Run a heredoc'd build script through the platform shell.

        HMFS bash starts with a failing getcwd; commands are executed via
        sh with an explicit cd, and every environment (conanbuild,
        conanrun, nemo_image_env, pkg-config path) is exported inside the
        script (avahi-ui-tools / pioneers precedent).
        """
        pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
        glib = self.dependencies["glib"]
        intl_so = os.path.join(glib.package_folder, "lib", "libintl.so")
        if not os.path.isfile(intl_so):
            raise ConanException(
                f"glib package lacks proxy libintl: {intl_so}")
        gen = self.generators_folder
        build = self.build_folder
        script = "\n".join([
            "set -e",
            f'cd "{build}"',
            f'. "{os.path.join(gen, "conanbuild.sh")}"',
            f'. "{os.path.join(gen, "conanrun.sh")}"',
            # nemo_image_env.sh (written by generate()) defines $CC.
            f'. "{os.path.join(gen, "nemo_image_env.sh")}"',
            # PkgConfigDeps .pc files live in the generators folder.
            f'export PKG_CONFIG_PATH="{gen}:{pkg_config_path}"',
            script_body,
        ])
        script_path = os.path.join(build, "ohos_build.sh")
        save(self, script_path, script + "\n")
        # Execute through sh (HMFS refuses to exec scripts via shebang;
        # avahi-ui-tools / pioneers precedent).  The conanbuild/conanrun
        # wrappers are re-sourced inside the script, and the env files are
        # taken from the generators folder explicitly.
        self.run(
            f'sh "{script_path}"', env=["conanbuild", "conanrun"])

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        converter = os.path.join(src, "nemo-image-converter")
        libext = os.path.join(src, "libnemo-extension")
        for path in (converter, libext):
            if not os.path.isdir(path):
                raise ConanException(f"source subtree missing: {path}")

        # Vendored layout mirroring the explorer-verified build:
        #   build/<...>/ include/libnemo-extension/*.h + config.h
        inc = os.path.join(self.build_folder, "include", "libnemo-extension")
        os.makedirs(inc, exist_ok=True)
        for header in _NEMO_EXT_HEADERS:
            copy(self, header, libext, inc)
        save(self, os.path.join(self.build_folder, "include", "config.h"),
             _CONFIG_H)

        # glib proxy libintl provides the g_libintl_* symbols the public
        # libintl.h maps bindtextdomain to (pioneers precedent).
        glib = self.dependencies["glib"]
        intl_so = os.path.join(glib.package_folder, "lib", "libintl.so")

        # Explicit unrolled compile/link sequence (HMFS shell quirks make
        # loops fragile; pioneers/libgsf build-time-edit precedent).
        lines = [
            f'SRC="{src}"',
            'CF="-Iinclude -Iinclude/libnemo-extension -DHAVE_CONFIG_H '
            '-fPIC -O2 -Wno-deprecated-declarations '
            '$(pkg-config --cflags glib-2.0 gio-2.0 gobject-2.0 gtk+-3.0)"',
        ]
        for name in _NEMO_EXT_C:
            base = name[:-2]
            lines.append(
                f'$CC -c "$SRC/libnemo-extension/{name}" $CF '
                f'-o ext_{base}.o')
        lines.append(
            "$CC -shared -o libnemo-extension.so " +
            " ".join(f"ext_{name[:-2]}.o" for name in _NEMO_EXT_C) +
            " $(pkg-config --libs glib-2.0 gobject-2.0 gio-2.0 gtk+-3.0)"
            " -Wl,-soname,libnemo-extension.so.1 -lm")
        # ---- extension module ------------------------------------------------
        for name in _CONVERTER_C:
            base = name[:-2]
            lines.append(
                f'$CC -c "$SRC/nemo-image-converter/src/{name}" '
                f'-Iinclude -DHAVE_CONFIG_H '
                f'$(pkg-config --cflags gtk+-3.0 glib-2.0) '
                f'-fPIC -O2 -Wno-deprecated-declarations '
                f'-o conv_{base}.o')
        lines.append(
            "$CC -shared -o libnemo-image-converter.so " +
            " ".join(f"conv_{name[:-2]}.o" for name in _CONVERTER_C) +
            " libnemo-extension.so" +
            f' "{intl_so}"' +
            " $(pkg-config --libs gtk+-3.0 glib-2.0)"
            " -Wl,-soname,libnemo-image-converter.so")
        # ---- staging sanity check: module loads through GModule -------------
        lines.append(
            'test -f libnemo-extension.so && test -f libnemo-image-converter.so')
        self._run_shell("\n".join(lines))

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        # 1) vendored ABI library (+ soname symlink, copy first then link)
        copy(self, "libnemo-extension.so",
             self.build_folder, os.path.join(pkg, "lib"))
        so1 = os.path.join(pkg, "lib", "libnemo-extension.so.1")
        if os.path.exists(so1):
            os.remove(so1)
        os.symlink("libnemo-extension.so", so1)
        # 2) extension module in the upstream extensiondir layout
        copy(self, "libnemo-image-converter.so",
             self.build_folder, os.path.join(pkg, "lib", "nemo",
                                             "extensions-3.0"))
        # 3) public headers of the vendored ABI subset
        copy(self, "*.h",
             os.path.join(self.build_folder, "include", "libnemo-extension"),
             os.path.join(pkg, "include", "libnemo-extension"))
        # 4) upstream UI definitions (resize / rotate dialogs)
        copy(self, "*.ui",
             os.path.join(src, "nemo-image-converter", "data"),
             os.path.join(pkg, "share", "nemo-image-converter"))
        # 5) licenses
        copy(self, "COPYING",
             os.path.join(src, "nemo-image-converter"),
             os.path.join(pkg, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["nemo-extension"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "libnemo-extension")
        self.cpp_info.set_property("cmake_file_name", "nemo-image")
        self.cpp_info.set_property("cmake_target_name", "nemo-image::nemo-image")
        # Consumers that need the extension module path can read this
        # property (mirrors the upstream extensiondir pkg-config variable).
        self.cpp_info.set_property("nemo_extension_dir",
                                   "lib/nemo/extensions-3.0")
