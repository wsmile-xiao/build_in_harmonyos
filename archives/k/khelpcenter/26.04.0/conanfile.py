#!/usr/bin/env python3
"""Conan recipe for khelpcenter 26.04.0 on HarmonyOS PC.

khelpcenter is the KDE Help Center (KDE Gear 26.04, KF6/Qt6). Upstream it
builds a Qt WebEngineWidgets-based help viewer executable plus a headless
Xapian documentation search stack.

OHOS-specific adaptations (see patches/0001-ohos-adaptation.patch):
  - The WebEngine viewer executable is trimmed from the build: qtwebengine
    is not published to the ohpcd conan registry and the qtbase/6.11.1
    package does not provide Qt6::WebEngineWidgets nor Qt6::PrintSupport
    (algobox 1.1.1 recipe precedent for the same gap). The GUI viewer
    (view.cpp/mainwindow.cpp/printdoc.cpp/pagesearchbar.cpp and friends)
    is deeply tied to QWebEnginePage/QWebEngineView and cannot be built.
  - The delivered artifacts on this platform are the headless search stack:
      * khcdocmetainfo shared library: DocEntry / DocMetaInfo /
        DocEntryTraverser plus the kcfg-generated Prefs settings - the
        metadata model that embedding applications and the upstream test
        suite consume
      * khc_xapianindexer: walks the KDocTools documentation dirs and
        builds/updates a Xapian full-text index out of the *.cache.bz2
        document caches (CacheReader/KCompressionDevice + libxml2
        htmlTextDump)
      * khc_xapiansearch: queries a Xapian index and prints the results
        as an HTML fragment (the searchhandler protocol khelpcenter uses)
    plus the data files (plugins/*.desktop, templates, glossary/toc xslt).
  - The upstream tests/ suite (testmetainfo) is kept: it now links the
    khcdocmetainfo library instead of recompiling the sources.
  - The DocMetaInfo/DocEntry classes are internal to the upstream
    executable and carry no export macros, so the library target sets
    CXX_VISIBILITY_PRESET "default" to keep the symbols visible.
  - DocTools/KDocTools::documentationDirs() is used by the indexer
    (kdoctools 6.19.0 from the registry provides KF6::DocTools);
    kdoctools_create_handbook doc/ building is trimmed (docbook
    customization data for OHOS help bundles is not shipped).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    not in the KDE platform list, audiocd 26.04.3 precedent).
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalog generation (CI
    worker msgfmt cannot load its libintl, alkimia 8.2.1 precedent).
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable (audiocd precedent).
  - conan_cmakedeps_paths.cmake created manually because qtbase and the
    KF6 packages use cmake_find_mode=none (audiocd/libkcddb precedent).
  - Linker flags pin -Wl,-z,max-page-size=0x1000: the default lld 0x10000
    page size can place .dynsym/.dynstr into separate high-address RW LOAD
    segments which the OHOS musl loader refuses to mmap (audiocd
    precedent).
  - FindXapian/FindLibXml2 are satisfied through the xapian-core package's
    own lib/cmake/xapian/xapian-config.cmake (XAPIAN_LIBRARIES /
    XAPIAN_INCLUDE_DIR) and CMakeDeps' LibXml2 target respectively; the
    xapian-config.cmake prefix is rewritten at generate() time so the
    paths point into the conan package folder.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file


class KHelpCenterConan(ConanFile):
    name = "khelpcenter"
    version = "26.04.0"
    description = "KDE Help Center - headless Xapian documentation search stack (khcdocmetainfo library, khc_xapianindexer/khc_xapiansearch tools) with the WebEngine viewer trimmed on OHOS"
    license = "GPL-2.0-or-later AND GFDL-1.2-or-later"
    homepage = "https://invent.kde.org/kde/khelpcenter"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/khelpcenter-26.04.0.tar.xz"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # karchive/zlib/libxml2 are aligned with the pins of kdoctools
        # 6.19.0 (karchive/6.19.0, zlib/1.3.1.1, libxml2/2.15.3) so the
        # dependency graph stays conflict-free.
        self.requires("karchive/6.19.0")
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("kdoctools/6.19.0")
        self.requires("ki18n/6.26.0")
        self.requires("xapian-core/1.4.26")
        self.requires("libxml2/2.15.3")
        # Explicitly require the transitive deps whose cmake configs the
        # KF6Archive/KF6DocTools configs chain-load (find_package(OpenSSL)
        # inside KF6ArchiveConfig.cmake etc.); Conan 2 only exposes direct
        # requires in self.dependencies, so these must be direct for the
        # conan_cmakedeps_paths.cmake injection. Versions are the ones
        # already pinned by kdoctools/6.19.0 - no graph change.
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
        self.requires("libxslt/1.1.45.1")
        # force the kdoctools/xapian pin for the whole graph (kf6 6.26-line
        # packages accept it; libkdegames 26.04.0 override precedent)
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Skip translation catalog generation: the CI worker's msgfmt
        # fails to load its own libintl.so.8 (alkimia 8.2.1 precedent).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # OHOS loader workaround: keep the regular 4-LOAD layout that the
        # OHOS musl loader accepts (audiocd 26.04.3 precedent).
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_MODULE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so the
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ...) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )
        tc.generate()

        # qtbase and the KF6 packages use cmake_find_mode=none, so
        # CMakeDeps doesn't generate conan_cmakedeps_paths.cmake. Create it
        # manually to add their lib/cmake dirs to CMAKE_PREFIX_PATH
        # (audiocd 26.04.3 recipe precedent).
        lines = []
        dep_names = [
            "qtbase",
            "karchive",
            "kconfig",
            "kcoreaddons",
            "kdoctools",
            "ki18n",
            "xapian-core",
            "libxml2",
            # transitive deps of the KF6 cmake configs: karchive's
            # KF6ArchiveConfig.cmake find_package(ZLIB) / find_package(
            # OpenSSL) need the conan packages' cmake dirs on the prefix
            # path; zstd/libxslt likewise for the kdoctools chain.
            "zlib",
            "zstd",
            "libxslt",
            "openssl",
        ]
        xapian_pkg = None
        for dep_name in dep_names:
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                pkg = dep.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
                for libdir in ("lib", "lib64"):
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/{libdir}")'
                    )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")'
                )
                bindir = os.path.join(pkg, "bin")
                if os.path.isdir(bindir):
                    lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{bindir}")')
                if dep_name == "xapian-core":
                    xapian_pkg = pkg
        if ecm:
            ecm_pkg = ecm.package_folder
            ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{ecm_pkg}/bin")')
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
        # The xapian-core package ships lib/cmake/xapian/xapian-config.cmake
        # whose prefix was baked at xapian-core packaging time; rewrite it so
        # XAPIAN_LIBRARIES/XAPIAN_INCLUDE_DIR point into this dependency's
        # package folder (the find_package(Xapian) module-mode lookup in
        # khelpcenter's CMakeLists resolves through those variables).
        if xapian_pkg:
            xapian_cfg = os.path.join(
                xapian_pkg, "lib", "cmake", "xapian", "xapian-config.cmake"
            )
            if os.path.isfile(xapian_cfg):
                # Rewrite the baked-in prefix so XAPIAN_LIBRARIES /
                # XAPIAN_INCLUDE_DIR point into this dependency's package
                # folder; drop the CACHE declarations so the reloaded
                # values stick. Idempotent: a cached package already
                # rewritten by a previous run is left untouched.
                with open(xapian_cfg) as f:
                    cfg_src = f.read()
                if 'SET(prefix "/")' in cfg_src:
                    replace_in_file(
                        self, xapian_cfg, 'SET(prefix "/")',
                        f'SET(prefix "{xapian_pkg}")',
                    )
                    replace_in_file(
                        self, xapian_cfg,
                        'SET(XAPIAN_SHARED_LIBRARY "${prefix}/lib/libxapian.so" CACHE FILEPATH "Shared Xapian library")',
                        'SET(XAPIAN_SHARED_LIBRARY "${prefix}/lib/libxapian.so")',
                    )
                    replace_in_file(
                        self, xapian_cfg,
                        'SET(XAPIAN_INCLUDE_DIR "${prefix}/include" CACHE PATH "Include path for Xapian")',
                        'SET(XAPIAN_INCLUDE_DIR "${prefix}/include")',
                    )
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{xapian_pkg}/lib/cmake/xapian")'
                )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        # Host tools shipped by the conan packages (kconfig_compiler from
        # kconfig, meinproc6 from kdoctools, moc/uic/rcc from qtbase) are
        # OHOS binaries: they need the compatible libc++_shared from
        # /system/lib64 plus the dependency lib dirs on LD_LIBRARY_PATH
        # (audiocd 26.04.3 recipe precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The library is the consumable deliverable together with the
        # search tools; no upstream cmake config exists for the trimmed
        # khcdocmetainfo target, so consumers locate it via plain
        # find_library against the package layout.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["khcdocmetainfo"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        # Ship the search/indexer tools on PATH for consumers that use
        # this package as a tool provider.
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
