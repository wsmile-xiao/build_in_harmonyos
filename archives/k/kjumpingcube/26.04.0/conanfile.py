#!/usr/bin/env python3
"""Conan recipe for kjumpingcube 26.04.0 on HarmonyOS PC (aarch64).

kjumpingcube is a KDE release-service game: a KXmlGui GUI application
producing a single bin/kjumpingcube executable (no library artifacts).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog processing (po/
    handling requires a full gettext toolchain not needed for the game)
  - KF6DocTools has no 6.18.0 package on the ohpcd registry (the locked
    KF6 6.18.0 family), so the doc handbook processing (add_subdirectory(doc)
    and kdoctools_install(po)) is patched out; ki18n_install(po) is kept and
    skipped at build time by KF_SKIP_PO_PROCESSING=ON
  - KIO is genuinely used by the game (src/game.cpp: KIO::stat /
    KIO::file_copy for game-state save/load through URLs), but ohpcd has
    no kio/6.18.0 (only 6.14.0/6.26.0; 6.26.0 would demand a 6.26 KF
    closure that does not exist for kconfigwidgets/kiconthemes). kio is
    therefore consumed at 6.14.0 with every one of its KF6 6.14 requirement
    pins overridden UP to the uniform 6.18.0 family: kio's installed
    configs request find_dependency(KF6* >= 6.14), which 6.18.0 satisfies,
    and KF6 keeps a stable ABI within the major version (same consumption
    pattern as kxmlgui/6.18.0 consuming karchive/6.19.0 artifacts)
  - KF6DBusAddons (KDBusService in main.cpp) requires Qt6::DBus, which is
    only provided by the qtbase-sql-dbus/6.11.1 variant (knowledge E323 /
    E441, and the published kdbusaddons/6.18.0 recipe consumes exactly that
    variant). That variant is required directly, and its lib/cmake dir is
    deterministically prepended first in conan_cmakedeps_paths.cmake so
    find_package(Qt6 ... DBus) can never resolve against the plain qtbase
    variant that arrives transitively (qtsvg, KF6 packages, libkdegames)
  - Dependencies resolved from the ohpcd registry: qtbase-sql-dbus 6.11.1,
    qtsvg 6.11.1, KF6 6.18.0 framework set, libkdegames/26.04.0.1 (the
    SONAME-fixed re-release; the official 26.04.0 is the defective
    SONAME-less release and must not be consumed), ecm/6.26.0
    (tool_requires)
  - karchive is pinned to 6.18.0 with override=True for the whole graph:
    the newest kiconthemes/6.18.0 recipe revision requires karchive/6.19.0
    while knewstuff/6.18.0 requires karchive/6.18.0 (same resolution as the
    libkdegames/26.04.0.1 recipe)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake written manually because qtbase (and the
    other KF6 packages) use cmake_find_mode=none, which prevents CMakeDeps
    from adding their lib/cmake dirs to CMAKE_PREFIX_PATH
  - package() retargets path-form DT_NEEDED entries of the installed
    artifacts (absolute conan-cache paths inherited from SONAME-less
    dependency artifacts) to their basename suffix via an in-place 8-byte
    dynamic-entry patch, then removes the stale .codesign section
    (llvm-objcopy) and re-signs the artifact (binary-sign-tool -selfSign 1)
    as required by OHOS; patchelf must not be used (knowledge E537)
  - Upstream ships no test suite (no autotests/, no tests/, no add_test/
    enable_testing anywhere in the source tree), so BUILD_TESTING=OFF and
    correctness is verified by the test_package consumer: a headless
    --version smoke run plus OHOS DT_NEEDED portability assertions
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KJumpingCubeConan(ConanFile):
    name = "kjumpingcube"
    version = "26.04.0"
    description = (
        "KJumpingCube - tactical one or two player KDE game "
        "(KXmlGui GUI application)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://apps.kde.org/kjumpingcube"
    url = "https://invent.kde.org/games/kjumpingcube"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::DBus (needed by KF6DBusAddons/KDBusService) is only available
        # in the qtbase-sql-dbus variant on ohpcd (knowledge E323/E441).
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtsvg/6.11.1")
        # kio is genuinely used (KIO::stat / KIO::file_copy for game-state
        # save/load). ohpcd has no kio/6.18.0; consume 6.14.0 with its KF6
        # requirement pins overridden UP to the uniform 6.18.0 family below
        # (see the module docstring for the version-choice rationale).
        self.requires("kio/6.14.0")
        # Uniform KF6 6.18.0 closure, pinned with override=True for the
        # whole graph: kio/6.14.0 pins 6.14.0 for its requirement set, and
        # the newest kiconthemes/6.18.0 recipe revision requires
        # karchive/6.19.0 while knewstuff/6.18.0 requires karchive/6.18.0 —
        # the overrides resolve everything to 6.18.0 (libkdegames/26.04.0.1
        # pins karchive/6.18.0 the same way).
        self.requires("karchive/6.18.0", override=True)
        self.requires("kauth/6.18.0", override=True)
        self.requires("kbookmarks/6.18.0", override=True)
        self.requires("kcolorscheme/6.18.0", override=True)
        self.requires("kcompletion/6.18.0", override=True)
        self.requires("kconfig/6.18.0", override=True)
        self.requires("kconfigwidgets/6.18.0", override=True)
        self.requires("kcoreaddons/6.18.0", override=True)
        self.requires("kcrash/6.18.0", override=True)
        self.requires("kguiaddons/6.18.0", override=True)
        self.requires("ki18n/6.18.0", override=True)
        self.requires("kiconthemes/6.18.0", override=True)
        self.requires("kitemviews/6.18.0", override=True)
        self.requires("kjobwidgets/6.18.0", override=True)
        self.requires("kservice/6.18.0", override=True)
        self.requires("kwidgetsaddons/6.18.0", override=True)
        self.requires("kwindowsystem/6.18.0", override=True)
        self.requires("solid/6.18.0", override=True)
        self.requires("kdbusaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        # Runtime closure of the KDEGames audio backend (libKDEGames6.so
        # DT_NEEDED libopenal.so.1 / libsndfile.so.1). Conan 2.29's
        # skip-binaries logic refuses to install second-level runtime-only
        # dependencies for a pure consumer, which would leave the game
        # unable to load at test time; declaring them here makes the closure
        # explicit and installed (both published on ohpcd, consumed by
        # libkdegames/26.04.0.1).
        self.requires("openal-soft/1.25.2")
        self.requires("libsndfile/1.2.2")
        # 26.04.0.1 is the SONAME-fixed re-release of libkdegames 26.04.0
        # (merged upstream and published on ohpcd); the original 26.04.0
        # artifact is the known SONAME-defective release.
        self.requires("libkdegames/26.04.0.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Upstream ships no test suite (NO_UPSTREAM_TESTS): keep ctest off.
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # po/ catalog processing is not needed for the game itself.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        qt_extra = []
        for dep_name in ("qtdeclarative", "qtshadertools", "qtsvg"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        # Deterministic Qt6 resolution: prepend the DBus-enabled variant last
        # so it ends up FIRST on the search path and find_package(Qt6 ... DBus)
        # can never hit the plain qtbase variant dragged in transitively.
        qt_variant = self.dependencies.get("qtbase-sql-dbus")
        if qt_variant and qt_variant.package_folder:
            self._append_dependency_paths(lines, qt_variant.package_folder)
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _build_runtime_env(self):
        # Build-time host tools shipped by dependency packages (kconfig's
        # kconfig_compiler_kf6 for kconfig_add_kcfg_files, qtbase's uic for
        # ki18n_wrap_ui) are executables linked against conan Qt libraries,
        # invoked directly by make with no loader path of their own. The
        # published kconfig package exports no buildenv_info, so without an
        # explicit LD_LIBRARY_PATH the musl loader fails these tools with
        # "Error relocating ...: symbol not found". Provide the closure
        # explicitly (build-chain-pitfalls: no default-search-path luck).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        return build_env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sanitize_needed_entries()

    def _sanitize_needed_entries(self):
        # The KF6 6.18.0 dependency artifacts carry no DT_SONAME (no
        # Platform/HarmonyOS CMake module), so the linked executable records
        # the absolute conan-cache paths of those dependencies in DT_NEEDED
        # and the artifact is not portable (loader error on any other
        # machine, L5/E537 failure mode). Retarget such path-form DT_NEEDED
        # entries to plain basenames so the loader resolves them through the
        # conan-provided LD_LIBRARY_PATH, which this package's test_package
        # (and any launcher) provides. Only path-form entries are touched;
        # plain soname-form entries (libQt6Core.so.6, libc.so, ...) are left
        # alone.
        #
        # The rewrite retargets the 8-byte d_val of each DT_NEEDED entry to
        # the byte offset of the basename substring that already terminates
        # the path string ("/abs/path/libX.so" -> offset of "libX.so").
        # Zero bytes are moved, so every other ELF structure (including
        # suffix-shared .dynstr strings) stays untouched; this also avoids
        # the .dynstr overlap limitation of a naive string-table overwrite.
        # patchelf must not be used: it rewrites the whole program header
        # table and the result is rejected by the OHOS musl loader
        # (knowledge E537).
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        replaced = 0
        for rel in ("bin", "lib"):
            package_dir = os.path.join(self.package_folder, rel)
            if not os.path.isdir(package_dir):
                continue
            for name in sorted(os.listdir(package_dir)):
                path = os.path.join(package_dir, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                if not self._is_elf(path):
                    continue
                replaced += self._retarget_needed_in_place(path)
        if replaced:
            self.output.info(f"DT_NEEDED entries sanitized: {replaced}")

    @staticmethod
    def _elf_needed_basename_retarget(data):
        """In-place d_val retarget of path-form DT_NEEDED entries.

        Returns (data, retargeted_count). Only the 8-byte d_val of each
        path-form DT_NEEDED entry changes; every other byte of the file is
        preserved exactly.
        """
        import struct

        if data[:4] != b"\x7fELF":
            return data, 0
        ei_class = data[4]
        ei_data = data[5]
        if ei_class != 2 or ei_data != 1:  # ELFCLASS64, little-endian only
            return data, 0
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        if e_shoff == 0 or e_shentsize == 0:
            return data, 0

        sections = []
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            sh_type = struct.unpack_from("<I", data, off + 4)[0]
            sh_addr = struct.unpack_from("<Q", data, off + 16)[0]
            sh_offset = struct.unpack_from("<Q", data, off + 24)[0]
            sh_size = struct.unpack_from("<Q", data, off + 32)[0]
            sections.append((sh_type, sh_addr, sh_offset, sh_size))

        buf = bytearray(data)
        replaced = 0
        for sh_type, sh_addr, sh_offset, sh_size in sections:
            if sh_type != 6 or sh_size == 0:  # SHT_DYNAMIC
                continue
            strtab_addr = None
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", buf, pos)
                if d_tag == 0:  # DT_NULL
                    break
                if d_tag == 5:  # DT_STRTAB
                    strtab_addr = d_val
                    break
            if strtab_addr is None:
                continue
            strtab_off = None
            strtab_size = 0
            for sh_type2, sh_addr2, sh_offset2, sh_size2 in sections:
                if sh_addr2 == strtab_addr and sh_type2 in (3, 6, 7, 1):
                    strtab_off = sh_offset2
                    strtab_size = sh_size2
                    break
            if strtab_off is None:
                continue
            strtab = bytes(buf[strtab_off:strtab_off + strtab_size])
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", buf, pos)
                if d_tag == 0:  # DT_NULL
                    break
                if d_tag != 1:  # DT_NEEDED only
                    continue
                if d_val >= len(strtab):
                    continue
                end = strtab.find(b"\x00", d_val)
                if end < 0:
                    continue
                old = strtab[d_val:end]
                slash = old.rfind(b"/")
                if slash < 0:
                    continue  # already a plain basename
                base_off = d_val + slash + 1
                struct.pack_into("<Q", buf, pos + 8, base_off)
                replaced += 1
        return bytes(buf), replaced

    def _retarget_needed_in_place(self, path):
        with open(path, "rb") as handle:
            data = handle.read()
        patched, count = self._elf_needed_basename_retarget(data)
        if count:
            with open(path, "wb") as handle:
                handle.write(patched)
            self.output.info(
                f"NEEDED sanitized in {os.path.basename(path)}: {count}"
            )
            # OHOS enforces valid ELF code signatures (.codesign section):
            # a rewritten file is refused by the loader with EACCES until it
            # is re-signed.
            self._resign_elf(path)
        return count

    def _resign_elf(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy") or self._find_ohos_tool(
            "objcopy"
        )
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "llvm-objcopy/binary-sign-tool not found; "
                f"{path} stays without a fresh signature and may not load"
            )
            return False
        mode = os.stat(path).st_mode & 0o777
        signed = path + ".signed"
        probe = subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            self.output.warning(
                f"llvm-objcopy --remove-section .codesign failed for {path}: "
                f"{probe.stderr.strip()[:120]}"
            )
            return False
        probe = subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            self.output.warning(
                f"binary-sign-tool sign failed for {path}: "
                f"{probe.stderr.strip()[:120]}"
            )
            return False
        shutil.move(signed, path)
        os.chmod(path, mode)
        return True

    def package_info(self):
        # Leaf GUI application: ship bin/, no cmake package of its own.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
