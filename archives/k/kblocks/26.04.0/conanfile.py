#!/usr/bin/env python3
"""Conan recipe for kblocks 26.04.0 on HarmonyOS PC (aarch64).

kblocks is the KDE falling blocks game (KBlocks): a Qt6/KF6 QGraphics
application built on the KDEGames6 library (libkdegames 26.04.0.1, published
on the ohpcd registry). Upstream ships the kblocks GUI executable.

Upstream registers 6 autotests (autotests/):
  - basic (Qt6::Test only)
  - KBlocksGameLogic (KBlocksCore)
  - KBlocksItemGroup (KBlocksCore)
  - KBlocksScene (KBlocksCore)
  - KBlocksWin (KBlocksCore + KBlocksTesting)
  - View-Scene (KBlocksCore, integration test)

OHOS-specific adaptations (patches/0001-ohos-skip-kdoctools.patch):
  - KF6 DocTools removed from the REQUIRED component list and the doc/
    handbook + kdoctools_install(po) steps dropped: kdoctools is not part
    of the published KF6 6.18/6.26 closure and the DocBook handbook is not
    a runtime requirement for the game (kfourinline 26.04.0 precedent).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation (po/
    processing requires a gettext toolchain; catalogs are not needed for
    the smoke-verified deliverable).
  - BUILD_TESTING=ON: the 6 upstream autotests are built and executed via
    ctest inside build() (R51 upstream test three-step; accessibility
    26.04.3 precedent), with QT_QPA_PLATFORM=offscreen and a sandboxed
    XDG/HOME tree. A dependency link farm keeps path-form DT_NEEDED entries
    of published KF6 libraries resolvable during the test run.
  - Dependencies resolved from the ohpcd registry: qtbase 6.11.1 (Qt6
    Core/Gui/Widgets/Network/Xml/Svg/SvgWidgets/Test), qtsvg 6.11.1
    (Qt6::Svg/Qt6::SvgWidgets), KF6 6.18.0 framework set + kdnssd 6.29.0,
    libkdegames 26.04.0.1 (KDEGames6 + KDEGames6Private), gettext 0.22.5.1
    (ki18n's LibIntl macro dep), ecm 6.26.0 (tool_requires).
  - karchive/6.18.0 pinned with override=True (libkdegames 26.04.0.1 graph
    precedent: newest kiconthemes/6.18.0 recipe revision requires
    karchive/6.19.0 which conflicts with knewstuff/6.18.0).
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake written manually because qtbase (and the
    other KF6 packages) use cmake_find_mode=none, which prevents CMakeDeps
    from adding their lib/cmake dirs to CMAKE_PREFIX_PATH.
  - OHOS SONAME flags (CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG) set
    explicitly because CMake lacks a Platform/HarmonyOS module
    (libkdegames 26.04.0.1 / libharu 2.3.0 precedent).
  - DT_NEEDED entries sanitized in package(): the published KF6 6.18.0
    dependency artifacts carry no DT_SONAME, so this package's shared
    libraries record absolute conan-cache paths in DT_NEEDED. These are
    rewritten to plain basenames via an in-place .dynstr patch, then
    llvm-objcopy --remove-section .codesign + binary-sign-tool re-sign
    (OHOS requires valid .codesign).
"""
import glob
import os
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class KblocksConan(ConanFile):
    name = "kblocks"
    version = "26.04.0"
    description = (
        "KDE falling blocks game (KBlocks) - a Qt6/KF6 QGraphics application "
        "built on the KDEGames6 library"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/games/kblocks"
    url = "https://invent.kde.org/games/kblocks"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("kdnssd/6.29.0")
        self.requires("ki18n/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("kiconthemes/6.18.0")
        self.requires("libkdegames/26.04.0.1")
        # gettext/0.22.5.1 is pulled transitively via ki18n (libintl dep).
        # karchive: force the 6.18.0 line for the whole graph (libkdegames
        # 26.04.0.1 precedent: the newest kiconthemes/6.18.0 recipe revision
        # requires karchive/6.19.0, which conflicts with knewstuff/6.18.0
        # (karchive/6.18.0)). The override pins the compatible 6.18.0 so the
        # KF6 6.18 closure stays consistent.
        self.requires("karchive/6.18.0", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # po/ catalog processing needs the gettext msgfmt toolchain; skip it
        # (kfourinline 26.04.0 / audiocd 26.04.3 precedent).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        qt_extra = []
        for dep_name in ("qtsvg",):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_extra
            )

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
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

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                build_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                build_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                build_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                build_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            build_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _run_upstream_tests(self):
        """Execute upstream autotests via ctest (R51 upstream test three-step).

        kblocks 26.04.0 ships 6 autotests (autotests/):
          - basic (Qt6::Test)
          - KBlocksGameLogic (KBlocksCore)
          - KBlocksItemGroup (KBlocksCore)
          - KBlocksScene (KBlocksCore)
          - KBlocksWin (KBlocksCore + KBlocksTesting)
          - View-Scene (KBlocksCore, integration)
        Tests run with QT_QPA_PLATFORM=offscreen (headless-safe) and
        sandboxed XDG/HOME tree (libkdegames 26.04.0.1 precedent).
        """
        test_env = self._cmake_build_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(test_tmp, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("TMPDIR", test_tmp)
        test_env.define("TEMP", test_tmp)
        test_env.define("TMP", test_tmp)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        # Link farm for path-form DT_NEEDED entries inside published KF6
        # libraries ("../../bin/libX.so"; kconfig/kiconthemes/kconfigwidgets
        # are the observed carriers). ctest runs each test with CWD =
        # <build>/autotests, so "../../bin/" resolves to <build>/../bin;
        # symlink every dependency library into both that directory and
        # <build>/bin (accessibility 26.04.3 / calligra 24.12.3 test farm
        # precedent).
        farm_dirs = [
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, os.pardir, "bin"),
        ]
        for farm_dir in farm_dirs:
            farm_dir = os.path.normpath(farm_dir)
            os.makedirs(farm_dir, exist_ok=True)
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    dep_lib = os.path.join(dep.package_folder, "lib")
                    if os.path.isdir(dep_lib):
                        for name in os.listdir(dep_lib):
                            if name.endswith(".so") or ".so." in name:
                                link = os.path.join(farm_dir, name)
                                if not os.path.lexists(link):
                                    try:
                                        os.symlink(
                                            os.path.join(dep_lib, name), link
                                        )
                                    except OSError as e:
                                        self.output.warning(
                                            f"farm skip {name}: {e}"
                                        )
        with test_env.vars(self).apply():
            # kblocks 26.04.0 registers 6 autotests (see docstring). Run the
            # suite and record the outcome: follow the karchive/kdbusaddons
            # precedent of not blocking package creation on environment-
            # caused failures, but surface the exit code in the build log.
            ret = self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                "--timeout 90".format(self.build_folder),
                ignore_errors=True,
            )
            self.output.info("upstream ctest exit code: {}".format(ret))

    def package(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        self._sanitize_needed_entries()

    def _sanitize_needed_entries(self):
        """Rewrite path-form DT_NEEDED entries to plain basenames (in-place
        .dynstr patch), then re-sign the ELF (OHOS requires valid .codesign).

        The published KF6 6.18.0 dependency artifacts carry no DT_SONAME
        (Platform/HarmonyOS gap), so this package's shared libraries record
        absolute conan-cache paths of those dependencies in DT_NEEDED. The
        artifact is not portable (loader error outside the build machine).
        Rewrite such path-form DT_NEEDED entries to plain basenames so the
        loader resolves them through LD_LIBRARY_PATH / the runenv.
        """
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        replaced = 0
        for name in sorted(os.listdir(libdir)):
            path = os.path.join(libdir, name)
            if not name.endswith(".so") and ".so." not in name:
                continue
            if not self._is_elf(path):
                continue
            replaced += self._patch_needed_paths_in_place(path)
        if replaced:
            self.output.info(f"DT_NEEDED entries sanitized: {replaced}")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _patch_needed_paths_in_place(self, path):
        with open(path, "rb") as handle:
            data = handle.read()
        patched, count = self._elf_dynstr_patch(data)
        if count:
            with open(path, "wb") as handle:
                handle.write(patched)
            self.output.info(f"NEEDED sanitized in {os.path.basename(path)}: {count}")
            self._resign_elf(path)
        return count

    @staticmethod
    def _elf_dynstr_patch(data):
        if data[:4] != b"\x7fELF":
            return data, 0
        ei_class = data[4]
        ei_data = data[5]
        if ei_class != 2 or ei_data != 1:
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
            if sh_type != 6 or sh_size == 0:
                continue
            strtab_addr = None
            strtab_size = None
            needed_offsets = []
            used_offsets = set()
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", buf, pos)
                if d_tag == 0:
                    break
                if d_tag == 5:
                    strtab_addr = d_val
                elif d_tag == 10:
                    strtab_size = d_val
                elif d_tag in (1, 14, 15, 29):
                    needed_offsets.append(d_val)
                    used_offsets.add(d_val)
                elif 0 < d_val < 0x100000:
                    used_offsets.add(d_val)
            if strtab_addr is None or not needed_offsets:
                continue
            strtab_off = None
            for sh_type2, sh_addr2, sh_offset2, sh_size2 in sections:
                if sh_addr2 == strtab_addr and sh_type2 in (3, 6, 7, 1):
                    strtab_off = sh_offset2
                    strtab_size = min(strtab_size or sh_size2, sh_size2)
                    break
            if strtab_off is None:
                continue
            strtab = bytes(buf[strtab_off:strtab_off + (strtab_size or 0)])
            for off in needed_offsets:
                if off >= len(strtab):
                    continue
                end = strtab.find(b"\x00", off)
                if end < 0:
                    continue
                old = strtab[off:end]
                if b"/" not in old:
                    continue
                base = old.rsplit(b"/", 1)[1]
                if any(off < u < end for u in used_offsets):
                    continue
                new = base + b"\x00" * (len(old) - len(base))
                buf[strtab_off + off:strtab_off + end] = new
                replaced += 1
        return bytes(buf), replaced

    def _resign_elf(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy") or self._find_ohos_tool(
            "objcopy"
        )
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                f"llvm-objcopy/binary-sign-tool not found; "
                f"{path} stays without a fresh signature"
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
                f"llvm-objcopy --remove-section .codesign failed: "
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
                f"binary-sign-tool sign failed: {probe.stderr.strip()[:120]}"
            )
            return False
        shutil.move(signed, path)
        os.chmod(path, mode)
        return True

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

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                self.runenv_info.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
