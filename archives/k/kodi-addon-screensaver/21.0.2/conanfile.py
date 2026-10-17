#!/usr/bin/env python3
"""Conan recipe for kodi-addon-screensaver 21.0.2 — Kodi "Asteroids" screensaver.

Upstream: https://github.com/xbmc/screensaver.asteroids (tag 21.0.2-Omega,
commit 7345b182f9b689bcf4c95db50919bc2f8f874cf7). The package name follows the
repository's kodi-* family convention (add-on class "screensaver" + app
"asteroids"); the upstream project id is "screensaver.asteroids".

The upstream CMakeLists.txt resolves its build through modules shipped with
the kodi-addon-dev distribution (FindKodi.cmake + build_addon() from
AddonHelpers.cmake), which expects a Kodi SDK installation. The ohpcd
registry has no kodi package, so this recipe supplies its own CMake entry
point (recipe-cmake/, consumed via build_script_folder) that builds the same
unmodified upstream sources against the Kodi add-on SDK headers and
Conan-provided glm, and links the OHOS system GLESv3/EGL libraries — the
upstream APP_RENDER_SYSTEM=gles render path.

The Kodi add-on SDK headers (xbmc/addons/kodi-dev-kit/include) are taken from
the xbmc 21.3-Omega release tarball — the same source the kodi-tools/21.3
recipe consumes; only that include subtree is extracted (the full xbmc tree
extracts to several hundred MB).
"""
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, download, get


class KodiAddonScreensaverConan(ConanFile):
    name = "kodi-addon-screensaver"
    version = "21.0.2"
    description = "Kodi 'Asteroids' screensaver add-on (OpenGL ES render path)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/xbmc/screensaver.asteroids"
    url = "https://github.com/xbmc/screensaver.asteroids"

    settings = "os", "compiler", "build_type", "arch"

    # CMakeDeps so consumers (test_package here, a future Kodi port later)
    # can consume this package through find_package().
    generators = "CMakeDeps"
    exports_sources = "recipe-cmake/*"

    def requirements(self):
        # Upstream pins glm 0.9.9.4 (depends/common/glm/glm.txt); the registry
        # carries the same 0.9.9 series as 0.9.9.8 (W0 checked: recipe
        # downloadable from the ohpcd remote with --only-recipe). The add-on
        # only uses header-level math APIs (glm/glm.hpp, glm/gtc/type_ptr.hpp).
        self.requires("glm/0.9.9.8")

    def validate(self):
        # The GLES render path links the OHOS system GLESv3/EGL driver
        # libraries directly (see recipe-cmake/CMakeLists.txt); the recipe
        # makes no attempt to cover other platforms' GL stacks.
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "kodi-addon-screensaver/21.0.2 is packaged for OHOS only "
                "(system GLESv3/EGL render path)."
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
            filename="screensaver.asteroids-21.0.2-Omega.tar.gz")
        copy(self, "*", src=os.path.join(self.recipe_folder, "recipe-cmake"),
             dst=os.path.join(self.source_folder, "recipe-cmake"))

        # 2. Kodi add-on SDK headers: download the xbmc 21.3-Omega tarball
        #    (URL list tried in order) and extract only the kodi-dev-kit
        #    include subtree.
        sdk_data = data["sdk"]
        urls = sdk_data["url"] if isinstance(sdk_data["url"], list) else [sdk_data["url"]]
        sdk_archive = os.path.join(self.source_folder, "kodi-sdk.tar.gz")
        last_error = None
        for url in urls:
            try:
                download(self, url, sdk_archive, sha256=sdk_data["sha256"])
                last_error = None
                break
            except ConanException as exc:
                last_error = exc
        if last_error is not None:
            raise ConanException("could not download the Kodi add-on SDK "
                                 "source: %s" % last_error)

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

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["ADDON_SRC_DIR"] = self.source_folder
        toolchain.variables["KODI_SDK_INCLUDE_DIR"] = os.path.join(
            self.source_folder, "kodi-sdk-include")
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
        copy(self, "screensaver.asteroids.so", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # The product is a Kodi-side loaded module (screensaver.asteroids.so,
        # declared in the add-on's addon.xml). Nothing links against it —
        # consumers deploy the module into the Kodi add-on tree. The module
        # directory is exposed so tooling can locate it.
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "kodi-addon-screensaver")
        self.cpp_info.set_property("cmake_target_name",
                                   "kodi-addon-screensaver::kodi-addon-screensaver")
