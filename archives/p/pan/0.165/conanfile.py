#!/usr/bin/env python3
"""Conan recipe — pan 0.165 (CMake, GNOME Usenet newsreader application).

Pan is a Usenet newsreader (GTK3 GUI + nzb CLI mode), C++17.
Upstream: https://gitlab.gnome.org/GNOME/pan (v0.165 tag).

Build notes (OHOS aarch64 / musl / clang 15):
- pan 0.165 switched to CMake (min 3.25). The hnp cmake 4.1.2 satisfies it
  (tool_requires is NOT used: the ohpcd registry has no cmake recipe and CI
  disables conancenter, so L0i would hard-fail on a missing tool_requires).
- Dependencies are discovered via pkg_check_modules (gtk+-3.0, gmime-3.0,
  glib-2.0) + find_package(ZLIB). PkgConfigDeps generates the .pc files;
  zlib/1.3.1.1 (conan) sets cmake_file_name=ZLIB which also satisfies the
  CMake FindZLIB module through CMakeDeps.
- glib unification: gmime/3.0.5 requires glib2/2.88.0 (static) while
  gtk/3.24.43 requires glib/2.84.0.1 (shared). Both packages export
  pkg_config_name=glib-2.0; in a combined graph Conan 2.29 keeps a single
  glib-2.0.pc pointing at the gtk tree's shared glib, and gmime's static
  libgmime-3.0.a links against that same shared libglib at runtime (symbol
  level compatible: 2.84 vs 2.88 both satisfy pan's GLIB_VERSION_MAX_ALLOWED
  = 2.36 policy). Verified with conan install gmime+gtk --build=missing.
- Optional features are disabled to keep the first graph minimal:
  WANT_GSPELL=OFF (gspell not published on ohpcd),
  WANT_GNUTLS=OFF (upstream ships a well-formed no-TLS CertStore fallback;
  gnutls/3.8.10 IS published and can be enabled in a later iteration),
  WANT_DBUS=OFF, WANT_NOTIFY=OFF, WANT_GKR=OFF, WANT_WEBKIT=OFF,
  WANT_GMIME_CRYPTO=OFF, ENABLE_MANUAL=OFF (needs itstool).
- The po/ subdir needs msgfmt (find_package(Gettext)); the hnp toolchain
  provides msgfmt/xgettext, PATH is set by the ohos-aarch64 profile.
- try_run(strftime test) in CMakeLists needs 3.25+: runs OK on hnp cmake.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class PanConan(ConanFile):
    name = "pan"
    version = "0.165"
    description = "Pan is a Usenet newsreader supporting NNTP/(S)NNTP, GTK3 GUI and nzb batch mode"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.gnome.org/GNOME/pan"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gtk pulls glib/2.84.0.1 (shared), cairo, pango, atk, gdk-pixbuf ...
        # transitive_headers/transitive_libs: pan includes gtk/gdk headers
        # directly and pkg_check_modules must resolve the full tree.
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        # gmime 3.0.5 is REQUIRED by pkg_check_modules(GMIME REQUIRED gmime-3.0)
        # (message parsing/encoding; pan calls g_mime_init() in main()).
        # BLOCKER: gmime/3.0.5 PR #7971 in CI — NOT yet on ohpcd registry.
        # Local pre-validation used the locally built gmime/3.0.5 cache.
        self.requires("gmime/3.0.5")
        # find_package(ZLIB 1.2.0 REQUIRED) — zlib/1.3.1.1 publishes
        # cmake_file_name=ZLIB; 1.3.1 base is non-PIC, .1.1 is the PIC fix.
        # override=True: glib2/2.88.0 (via gmime) pins zlib/1.3.1 while the
        # PIC variant 1.3.1.1 is the one published with binaries — graph
        # unification to 1.3.1.1 (same fix as the gmime/3.0.5 recipe).
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        # pkg_check_modules needs pkg-config; the hnp toolchain ships it
        # (profile PATH). No conan-side tool_requires: cmake/pkg-config are
        # hnp-provided and the ohpcd registry has no cmake recipe (CI
        # disables conancenter; a tool_requires("cmake/...") would fail L0i).
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # .pc files for every host dependency (gtk/gmime/glib trees).
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = CMakeToolchain(self)
        # CMake has no OHOS platform module; pan builds natively on OHOS
        # with clang and uses no Linux-specific build-system behaviour
        # (same approach as abcmidi/20260609).
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # try_run(HAVE_LKSTRFTIME ...) cannot run in the conan cross-build
        # context (CMAKE_CROSSCOMPILING is set by the OHOS toolchain). The
        # upstream fallback is safe (e-util.cc replaces %l→%I / %k→%H in
        # the format string before calling strftime), so preset the cache
        # var to 0 = "use the portable fallback" (same value musl gives).
        tc.cache_variables["HAVE_LKSTRFTIME"] = "0"
        tc.cache_variables["HAVE_LKSTRFTIME__TRYRUN_OUTPUT"] = ""
        # Feature switches (all default-off options stay off; the two
        # default-ON options are forced off, see class docstring).
        tc.variables["WANT_DBUS"] = False
        tc.variables["WANT_GMIME_CRYPTO"] = False
        tc.variables["WANT_GSPELL"] = False          # gspell not on ohpcd
        tc.variables["WANT_WEBKIT"] = False
        tc.variables["WANT_GNUTLS"] = False          # minimal graph first
        tc.variables["WANT_NOTIFY"] = False
        tc.variables["WANT_GKR"] = False
        tc.variables["ENABLE_MANUAL"] = False        # needs itstool
        tc.variables["BUILD_TESTING"] = False        # upstream tests disabled
        # Reproducible build: skip embedding git rev (tarball has no .git
        # anyway) and uname platform info. Both CMakeLists branches check
        # "if NOT DEFINED ENV{SOURCE_DATE_EPOCH}"; export it in the build
        # environment instead of the toolchain (CMakeToolchain has no
        # .environment() method).
        env = Environment()
        env.define("SOURCE_DATE_EPOCH", "1")
        if self.settings.os == "OHOS":
            # msgfmt/xgettext (po/ processing) live in the hnp tool dir;
            # make them visible to CMake's FindGettext. msgmerge is only
            # symlinked under hnp/gettext.org/gettext_0.26/bin (not on the
            # default hnp PATH) and FindGettext REQUIRES it — prepend the
            # full gettext bin dir so msgfmt/xgettext/msgmerge all resolve.
            import glob
            for gdir in sorted(glob.glob("/data/service/hnp/gettext.org/*/bin"),
                               reverse=True):
                if os.path.isdir(gdir):
                    env.prepend_path("PATH", gdir)
                    break
            for tool in ("msgfmt", "xgettext", "msgmerge"):
                path = shutil.which(tool)
                if path:
                    env.define_path(tool.upper(), path)
            # hnp cmake needs libc++_shared.so from /system/lib64 — the
            # conan build environment may not include it; prepend so cmake
            # resolves its runtime deps (same fix as gmime test_package).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.vars(self).save_script("pan_ohos_buildenv")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # hnp cmake needs libc++_shared.so from /system/lib64; the conan
        # build sandbox may strip LD_LIBRARY_PATH — inject it directly into
        # the process environment before cmake runs (E077-adjacent fix).
        if self.settings.os == "OHOS":
            cur = os.environ.get("LD_LIBRARY_PATH", "")
            if "/system/lib64" not in cur:
                os.environ["LD_LIBRARY_PATH"] = ("/system/lib64:" + cur) if cur else "/system/lib64"
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # License files (CI gate checks common license names).
        for lic in ("COPYING", "COPYING-DOCS"):
            src = os.path.join(self.source_folder, lic)
            if os.path.isfile(src):
                copy(self, lic, src, os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "pan"))

    @staticmethod
    def _sign_ohos_elf(path):
        # E077: OHOS kernels refuse to exec unsigned ELFs ("Operation not
        # permitted"). Sign the packaged pan binary so test_package (and
        # end users) can run it. Same pattern as abx/0.1.
        import subprocess
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(f"Missing packaged executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanInvalidConfiguration("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True, timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True, capture_output=True, text=True, timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanInvalidConfiguration("Signed pan binary has invalid .codesign count")
        os.replace(output, path)
        os.chmod(path, 0o755)

    def package_info(self):
        # Application package: only the pan executable is consumed.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # System libs pan links against (pthread is added by Threads module).
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        self.cpp_info.set_property("pkg_config_name", "pan")
        self.cpp_info.set_property("cmake_file_name", "pan")
        self.cpp_info.set_property("cmake_target_name", "pan::pan")
