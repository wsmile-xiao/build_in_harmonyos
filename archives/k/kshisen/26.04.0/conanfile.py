#!/usr/bin/env python3
"""Conan recipe for kshisen 26.04.0 on HarmonyOS PC (aarch64).

kshisen is a KDE release-service game (Shisen-Sho, a Mahjongg-like tile
solitaire): a KXmlGui/QApplication producing a single bin/kshisen
executable (no library artifacts). It is the KDEGames6 game built on the
KMahjongglib6 tileset/background library (libkmahjongg 26.04.0) and the
KDE Games framework (libkdegames 26.04.0.1, the SONAME-fixed re-release;
the official 26.04.0 is the defective SONAME-less release and must not
be consumed).

OHOS-specific adaptations:
  - kdoctools trimmed (patches/0001 + 0002, knavalbattle/kgoldrunner
    precedent): kdoctools has no package on the locked KF6 6.18.0 family
    (its newest published binary anchors karchive/6.19.0), so DocTools is
    removed from the KF6 umbrella find_package and kdoctools_install(po)
    plus the doc/ handbook generation are commented out.
    CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=TRUE as belt-and-suspenders.
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: the po/ catalog handling needs the gettext
    toolchain not required by the game (audiocd precedent)
  - libkmahjongg/26.04.0's recipe pins the KF6 6.14.0 line
    (kconfig/kconfigwidgets/kcoreaddons/kwidgetsaddons/ki18n); every pin
    is overridden UP to the uniform KF6 6.18.0 family that matches the
    libkdegames/26.04.0.1 binary closure (kjumpingcube kio/6.14.0
    override-UP precedent: installed KF6 configs request
    find_dependency(KF6* >= 6.14), which 6.18.0 satisfies, and KF6 keeps
    a stable ABI within the major version)
  - karchive pinned to 6.18.0 with override=True: the newest
    kiconthemes/6.18.0 recipe revision requires karchive/6.19.0 which
    conflicts with knewstuff/6.18.0 (same resolution as libkdegames/
    26.04.0.1 itself)
  - KF6DBusAddons (KDBusService in main.cpp) requires Qt6::DBus, which
    is only provided by the qtbase-sql-dbus/6.11.1 variant (knowledge
    E323 / E441). That variant is required directly and its lib/cmake
    dir is deterministically prepended first in
    conan_cmakedeps_paths.cmake so find_package(Qt6) can never resolve
    against the plain qtbase variant that arrives transitively
  - Upstream registers exactly one test (N=1): src/tests/movetest
    (Qt Test, links Qt6::Test + ../move.cpp, QTEST_APPLESS_MAIN), gated
    by BUILD_TESTING. BUILD_TESTING=ON and the test genuinely runs via
    ctest inside build() with an offscreen QPA and a sandboxed HOME/XDG
    tree (keditbookmarks kbookmarkmodeltest precedent; R39: self.run
    with /system/lib64 first for the OHOS libc++_shared.so)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project's
    CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake written manually because qtbase (and
    the other KF6 packages) use cmake_find_mode=none, which prevents
    CMakeDeps from adding their lib/cmake dirs to CMAKE_PREFIX_PATH
  - package() retargets path-form DT_NEEDED entries of the installed
    artifacts (absolute conan-cache paths inherited from SONAME-less
    dependency artifacts) to their basename suffix via an in-place
    8-byte dynamic-entry patch, then removes the stale .codesign
    section (llvm-objcopy) and re-signs the artifact
    (binary-sign-tool -selfSign 1) as required by OHOS; patchelf must
    not be used (knowledge E537)
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KshisenConan(ConanFile):
    name = "kshisen"
    version = "26.04.0"
    description = (
        "KShisen - Shisen-Sho solitaire game, a Mahjongg-like tile game "
        "(KDE Gear 26.04.0, Qt6/KF6/KMahjongglib6/KDEGames6)"
    )
    license = "GPL-2.0-or-later AND GFDL-1.2-or-later"
    homepage = "https://apps.kde.org/kshisen"
    url = "https://invent.kde.org/games/kshisen"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::DBus (needed by KF6DBusAddons/KDBusService) is only
        # available in the qtbase-sql-dbus variant on ohpcd (E323/E441).
        # Core/Gui/Test components resolve from the same variant (it is
        # deterministically first on the cmake search path).
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtsvg/6.11.1")
        # Uniform KF6 6.18.0 closure matching the libkdegames/26.04.0.1
        # binary closure. libkmahjongg/26.04.0 pins the 6.14.0 line; the
        # overrides force the five pinned frameworks UP to 6.18.0
        # (kjumpingcube override-UP precedent; KF6 ABI is stable within
        # the major version, installed configs request >= 6.14 which
        # 6.18.0 satisfies). karchive is pinned 6.18.0 for the whole
        # graph: the newest kiconthemes/6.18.0 recipe revision requires
        # karchive/6.19.0 which conflicts with knewstuff/6.18.0 (same
        # resolution as the libkdegames/26.04.0.1 recipe).
        self.requires("karchive/6.18.0", override=True)
        self.requires("kconfig/6.18.0", override=True)
        self.requires("kconfigwidgets/6.18.0", override=True)
        self.requires("kcoreaddons/6.18.0", override=True)
        self.requires("ki18n/6.18.0", override=True)
        self.requires("kwidgetsaddons/6.18.0", override=True)
        # Direct KF6 components of the game (all on the 6.18.0 family).
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("kxmlgui/6.18.0")
        # Runtime NEEDED closure of libKDEGames6.so (OpenAL audio
        # backend / sndfile). openal-soft defaults static so Conan would
        # skip it from consumer graphs unless required explicitly.
        self.requires("openal-soft/1.25.2")
        self.requires("libsndfile/1.2.2")
        # Mahjongg tileset/background library (KMahjongglib6) and the
        # KDE Games framework (KDEGames6) — the SONAME-fixed re-release.
        self.requires("libkmahjongg/26.04.0")
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
        # Upstream registers exactly one test (src/tests/movetest):
        # build it and run it via ctest in build() (keditbookmarks
        # precedent). KDECMakeSettings turns BUILD_TESTING into
        # include(CTest)/enable_testing().
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # kdoctools is trimmed by patch; never let find_package look for
        # it (kgoldrunner precedent).
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "TRUE"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        if str(self.settings.os) == "OHOS":
            # OHOS loader workaround (audiocd/kgoldrunner precedent):
            # default lld 0x10000 max-page-size can split .dynsym/.dynstr
            # into separate high-address RW LOAD segments which the OHOS
            # musl loader refuses to mmap; pin the 4K page layout.
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        # Qt6 split-package component discovery: qtdeclarative/
        # qtshadertools arrive transitively via libkdegames, qtsvg is a
        # direct requirement (kjumpingcube precedent).
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
        # Deterministic Qt6 resolution: prepend the DBus-enabled variant
        # last so it ends up FIRST on the search path and find_package(
        # Qt6 ... DBus) can never hit the plain qtbase variant dragged in
        # transitively (kjumpingcube precedent).
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
        # Build-time host tools shipped by dependency packages
        # (kconfig's kconfig_compiler_kf6 for kconfig_add_kcfg_files,
        # qtbase's uic for ki18n_wrap_ui, rcc/moc for the qrc/sources)
        # are executables linked against conan Qt/KF libraries, invoked
        # directly by make with no loader path of their own. The
        # published packages export no buildenv_info, so without an
        # explicit LD_LIBRARY_PATH the musl loader fails these tools
        # with "Error relocating ...: symbol not found"
        # (kjumpingcube/build-chain-pitfalls precedent). /system/lib64
        # provides the compatible libc++_shared.so (prepended first:
        # the SDK libc++.so is a linker script the loader cannot use).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Upstream registers exactly one ctest target: movetest
        # (src/tests, Qt Test, gated by BUILD_TESTING). Sandbox env
        # (keditbookmarks kbookmarkmodeltest precedent): offscreen QPA,
        # isolated HOME/XDG tree, dependency lib dirs on the loader path
        # with /system/lib64 first (OHOS libc++_shared.so shadow fix).
        # --no-tests=error turns a silently-skipped test suite into a
        # hard failure, so the N=1 upstream test genuinely runs (R39:
        # self.run, statistics go into the build log).
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        env.define("QT_QPA_PLATFORM", "offscreen")
        home = os.path.join(self.build_folder, "test-home")
        xdg = os.path.join(self.build_folder, "xdg-runtime")
        for d in (home, xdg):
            os.makedirs(d, exist_ok=True)
        os.chmod(xdg, 0o700)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "%s" --output-on-failure --no-tests=error'
                % self.build_folder
            )

    def package(self):
        cmake = CMake(self)
        with self._build_runtime_env().vars(self).apply():
            cmake.install()
        self._sanitize_needed_entries()

    def _sanitize_needed_entries(self):
        # The KF6 6.18.0 dependency artifacts carry no DT_SONAME (no
        # Platform/HarmonyOS CMake module), so the linked executable
        # records the absolute conan-cache paths of those dependencies
        # in DT_NEEDED and the artifact is not portable (loader error on
        # any other machine, L5/E537 failure mode). Retarget such
        # path-form DT_NEEDED entries to plain basenames so the loader
        # resolves them through the conan-provided LD_LIBRARY_PATH,
        # which this package's test_package (and any launcher) provides.
        # Only path-form entries are touched; plain soname-form entries
        # (libQt6Core.so.6, libc.so, ...) are left alone.
        #
        # The rewrite retargets the 8-byte d_val of each DT_NEEDED entry
        # to the byte offset of the basename substring that already
        # terminates the path string ("/abs/path/libX.so" -> offset of
        # "libX.so"). Zero bytes are moved, so every other ELF structure
        # (including suffix-shared .dynstr strings) stays untouched;
        # this also avoids the .dynstr overlap limitation of a naive
        # string-table overwrite. patchelf must not be used: it rewrites
        # the whole program header table and the result is rejected by
        # the OHOS musl loader (knowledge E537).
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
        path-form DT_NEEDED entry changes; every other byte of the file
        is preserved exactly.
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
            # OHOS enforces valid ELF code signatures (.codesign
            # section): a rewritten file is refused by the loader with
            # EACCES until it is re-signed.
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
        # Game sounds live under share/sounds/kshisen; surface the share
        # tree for consumers (kgoldrunner precedent).
        self.runenv_info.prepend_path(
            "XDG_DATA_DIRS", os.path.join(self.package_folder, "share")
        )
        # libKDEGames6.so NEEDs libopenal.so.1 (openal-soft is a
        # transitive requirement of libkdegames); surface its lib dir
        # (and libsndfile's) on the run environment so consumers can
        # resolve every ELF (kgoldrunner precedent).
        for dep_name in ("openal-soft", "libsndfile"):
            try:
                dep = self.dependencies.get(dep_name)
            except Exception:
                dep = None
            if dep and dep.package_folder:
                lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib):
                    self.runenv_info.prepend_path("LD_LIBRARY_PATH", lib)
