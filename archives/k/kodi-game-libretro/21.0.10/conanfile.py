#!/usr/bin/env python3
"""Conan recipe for kodi-game-libretro 21.0.10 — Kodi Libretro compatibility.

Upstream: https://github.com/kodi-game/game.libretro (tag 21.0.10-Omega,
commit 3b3aa934198ccbf0c25138e10a579db1db8f4ffe). The package name follows
the repository's kodi-* family convention and matches the Debian source
package name (kodi-game-libretro); the upstream project id is "game.libretro".

The upstream CMakeLists.txt resolves its build through modules shipped with
the kodi-addon-dev distribution (FindKodi.cmake + build_addon() from
AddonHelpers.cmake), which expects a Kodi SDK installation. The ohpcd
registry has no kodi package, so this recipe supplies its own CMake entry
point (recipe-cmake/, consumed via build_script_folder) that builds the same
unmodified upstream sources against the Kodi add-on SDK headers.

Vendored inputs (no conan packages exist for them, pinned by upstream
depends/common/*.txt):
  - libretro-common @ 50c15a88 — header-only, extracted from the pinned
    tarball into libretro-common-include/libretro-common (the upstream
    sources include "libretro-common/libretro.h").
  - rcheevos @ v9.2.0 — static C library, extracted into rcheevos-src/ and
    built as a PIC static library by the recipe CMake entry with the
    upstream depends/common/rcheevos/CMakeLists.txt source list and
    -DRC_DISABLE_LUA; public headers are mirrored into
    rcheevos-include/rcheevos/ (the sources include "rcheevos/rcheevos.h").
tinyxml/2.6.2 comes from the conan registry (upstream pins the same 2.6.2
series and links it with TIXML_USE_STL, which the registry package's
with_stl default provides).

The Kodi add-on SDK headers (xbmc/addons/kodi-dev-kit/include) are taken from
the xbmc 21.3-Omega release tarball — the same source the
kodi-addon-screensaver/21.0.2 recipe consumes; only that include subtree is
extracted (the full xbmc tree extracts to several hundred MB).

No GLES/EGL involvement: rendering goes through the Kodi Game API callbacks;
the libretro core .so is dlopen()ed at host runtime (LibretroDLL.cpp).
"""
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, download, get


def _download_first(recipe, data, dest):
    """Download data["url"] (list, tried in order) into dest with sha256."""
    urls = data["url"] if isinstance(data["url"], list) else [data["url"]]
    last_error = None
    for url in urls:
        try:
            download(recipe, url, dest, sha256=data["sha256"])
            return
        except ConanException as exc:
            last_error = exc
    raise ConanException("could not download source archive: %s" % last_error)


class KodiGameLibretroConan(ConanFile):
    name = "kodi-game-libretro"
    version = "21.0.10"
    description = "Kodi 'Libretro Compatibility' game client add-on (libretro core wrapper)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/kodi-game/game.libretro"
    url = "https://github.com/kodi-game/game.libretro"

    settings = "os", "compiler", "build_type", "arch"

    # CMakeDeps so consumers (test_package here, a future Kodi port later)
    # can consume this package through find_package().
    generators = "CMakeDeps"
    exports_sources = "recipe-cmake/*"

    def requirements(self):
        # Upstream pins tinyxml 2.6.2 (depends/common/tinyxml/tinyxml.txt);
        # the registry carries tinyxml/2.6.2 with TIXML_USE_STL enabled by
        # default, matching the upstream depends build.
        self.requires("tinyxml/2.6.2")

    def validate(self):
        # The recipe targets the OHOS aarch64 build (OHOS system dlopen for
        # libretro cores, clang/libc++); no other platform is covered.
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "kodi-game-libretro/21.0.10 is packaged for OHOS only."
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        data = self.conan_data["sources"][self.version]

        # 1. Add-on sources. Conan merges exports_sources into the source
        #    folder BEFORE source() runs (config_source trap, see
        #    kodi-platform/20250416 notes), so recipe-cmake/ already exists
        #    here and the tarball (which has no recipe-cmake/ directory)
        #    cannot clobber it. Re-copy defensively like the kodi-platform
        #    precedent.
        get(self, **data["addon"], strip_root=True,
            filename="game.libretro-21.0.10-Omega.tar.gz")
        copy(self, "*", src=os.path.join(self.recipe_folder, "recipe-cmake"),
             dst=os.path.join(self.source_folder, "recipe-cmake"))

        # 2. Kodi add-on SDK headers: extract only the kodi-dev-kit include
        #    subtree of the xbmc 21.3-Omega tarball.
        sdk_archive = os.path.join(self.source_folder, "kodi-sdk.tar.gz")
        _download_first(self, data["sdk"], sdk_archive)
        sdk_root = os.path.join(self.source_folder, "kodi-sdk")
        prefix = "xbmc-21.3-Omega/xbmc/addons/kodi-dev-kit/include"
        with tarfile.open(sdk_archive, "r:gz") as archive:
            members = [member for member in archive.getmembers()
                       if member.name == prefix or member.name.startswith(prefix + "/")]
            archive.extractall(sdk_root, members=members, filter="data")
        os.rename(os.path.join(sdk_root, prefix),
                  os.path.join(self.source_folder, "kodi-sdk-include"))
        # Only the empty xbmc-21.3-Omega/ directory chain is left here.
        shutil.rmtree(sdk_root)
        os.remove(sdk_archive)

        # 3. libretro-common headers (header-only, upstream pin). The sources
        #    include "libretro-common/libretro.h", so the extracted include/
        #    subtree is renamed to libretro-common-include/libretro-common.
        lc_archive = os.path.join(self.source_folder, "libretro-common.tar.gz")
        _download_first(self, data["libretro-common"], lc_archive)
        lc_root = os.path.join(self.source_folder, "libretro-common-extract")
        lc_prefix = ("libretro-common-50c15a88eb741cbe675743a282d8cc4c89421e3f"
                     "/include")
        with tarfile.open(lc_archive, "r:gz") as archive:
            members = [member for member in archive.getmembers()
                       if member.name == lc_prefix or member.name.startswith(lc_prefix + "/")]
            archive.extractall(lc_root, members=members, filter="data")
        os.makedirs(os.path.join(self.source_folder, "libretro-common-include"))
        os.rename(os.path.join(lc_root, lc_prefix),
                  os.path.join(self.source_folder, "libretro-common-include",
                               "libretro-common"))
        shutil.rmtree(lc_root)
        os.remove(lc_archive)

        # 4. rcheevos (static C library, upstream pin). Extracted into its
        #    own rcheevos-src/ folder (the tarball's src/ must not merge with
        #    the add-on's src/); the four public headers are mirrored into
        #    rcheevos-include/rcheevos/ so the sources'
        #    "rcheevos/<header>.h" includes resolve, mirroring the upstream
        #    depends install layout (include/<project-name>/).
        rc_archive = os.path.join(self.source_folder, "rcheevos.tar.gz")
        _download_first(self, data["rcheevos"], rc_archive)
        rc_root = os.path.join(self.source_folder, "rcheevos-extract")
        rc_prefix = "rcheevos-9.2.0"
        with tarfile.open(rc_archive, "r:gz") as archive:
            members = [member for member in archive.getmembers()
                       if member.name == rc_prefix or member.name.startswith(rc_prefix + "/")]
            archive.extractall(rc_root, members=members, filter="data")
        os.rename(os.path.join(rc_root, rc_prefix),
                  os.path.join(self.source_folder, "rcheevos-src"))
        shutil.rmtree(rc_root)
        os.remove(rc_archive)
        rc_include = os.path.join(self.source_folder, "rcheevos-include",
                                  "rcheevos")
        os.makedirs(rc_include)
        for header in os.listdir(os.path.join(self.source_folder,
                                              "rcheevos-src", "include")):
            shutil.copy2(os.path.join(self.source_folder, "rcheevos-src",
                                      "include", header),
                         os.path.join(rc_include, header))

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["ADDON_SRC_DIR"] = self.source_folder
        toolchain.variables["KODI_SDK_INCLUDE_DIR"] = os.path.join(
            self.source_folder, "kodi-sdk-include")
        toolchain.variables["RCHEEVOS_SRC_DIR"] = os.path.join(
            self.source_folder, "rcheevos-src")
        # E092: CMake has no HarmonyOS platform module, use Linux
        # (kodi-platform/20250416 precedent).
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="recipe-cmake")
        cmake.build()

    def package(self):
        copy(self, "game.libretro.so", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # The product is a Kodi-side loaded module (game.libretro.so,
        # declared in the add-on's addon.xml). Nothing links against it —
        # consumers deploy the module into the Kodi add-on tree. The module
        # directory is exposed so tooling can locate it.
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "kodi-game-libretro")
        self.cpp_info.set_property("cmake_target_name",
                                   "kodi-game-libretro::kodi-game-libretro")
