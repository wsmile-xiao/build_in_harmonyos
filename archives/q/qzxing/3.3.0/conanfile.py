#!/usr/bin/env python3
"""Conan recipe for QZXing 3.3.0 (C++/Qt barcode scanner) on OpenHarmony PC."""
import glob
import os
import re
import shlex
import shutil
import subprocess
import textwrap

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs, can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class QzxingConan(ConanFile):
    name = "qzxing"
    version = "3.3.0"
    description = "QZXing barcode/QR scanner library (C++/Qt port of ZXing)"
    license = "Apache-2.0"
    homepage = "https://github.com/ftylitak/qzxing"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qzxing only supports Linux and OHOS, got {}".format(self.settings.os))

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream QZXing.pro default feature set: all decoders + generic QR
        # encoder; the QML/multimedia blocks are commented out there too.
        tc.cache_variables["QZXING_USE_ENCODER"] = "ON"
        # Decoder registration in MultiFormatReader.cpp is guarded by
        # ENABLE_DECODER_* defines, and upstream src/CMakeLists.txt applies
        # them only when the QZXING_USE_DECODER_* options are set (they
        # default to unset). QZXing.pri defines them all unconditionally, so
        # the .pro build ships every decoder; the CMake build without these
        # options produces a MultiFormatReader with ZERO registered readers
        # and every consumer decode fails (device-verified: the packaged
        # library failed to decode while the same sources compiled with the
        # .pri-aligned defines passed the upstream 1110-image corpus).
        tc.cache_variables["QZXING_USE_DECODER_QR_CODE"] = "ON"
        tc.cache_variables["QZXING_USE_DECODER_1D_BARCODES"] = "ON"
        tc.cache_variables["QZXING_USE_DECODER_DATA_MATRIX"] = "ON"
        tc.cache_variables["QZXING_USE_DECODER_AZTEC"] = "ON"
        tc.cache_variables["QZXING_USE_DECODER_PDF17"] = "ON"
        tc.cache_variables["QZXING_MULTIMEDIA"] = "OFF"
        tc.cache_variables["QZXING_USE_QML"] = "OFF"
        # Qt5 consumption goes through the qt5-qtbase CMakeDeps root config
        # (find_package(qt5-qtbase)); it declares the Qt5::Core/Qt5::Gui/
        # Qt5::Concurrent component targets. The patched src/CMakeLists.txt
        # never touches the native Qt5Config.cmake umbrella, which is not
        # relocatable.
        tc.cache_variables["CMAKE_LIBRARY_OUTPUT_DIRECTORY"] = os.path.join(
            self.build_folder, "lib").replace("\\", "/")
        tc.cache_variables["CMAKE_RUNTIME_OUTPUT_DIRECTORY"] = os.path.join(
            self.build_folder, "lib").replace("\\", "/")
        # The patch runs moc explicitly (CMake AUTOMOC cannot detect Qt5
        # without QT_VERSION_MAJOR); point it at the qt5-qtbase bin/moc.
        qt = self.dependencies["qt5-qtbase"]
        moc = os.path.join(qt.package_folder, "bin", "moc") if qt.package_folder else ""
        tc.cache_variables["QZXING_MOC_PATH"] = moc
        tc.generate()
        # qt5-qtbase root config consumed by the patched find_package call
        # (see the patch comment).
        deps = CMakeDeps(self)
        deps.generate()
        if self.settings.os == "OHOS":
            # HMDFS rejects symlinks (E046/E492 family); prepend a PATH shim
            # so any `ln -s` during the build falls back to a plain copy.
            # moc runs during the build and links against the qt5-qtbase
            # libraries, so expose the package lib dir as well.
            env = Environment()
            env.prepend_path("PATH", self._create_symlink_shim())
            if qt.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(qt.package_folder, "lib"))
            env.vars(self).save_script("conanbuild_qzxing_shim")

    def build(self):
        cmake = CMake(self)
        # Upstream keeps its CMakeLists.txt in src/, not at the repo root.
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "src"))
        cmake.build()
        if can_run(self):
            self._run_upstream_tests()
        else:
            self.output.info(
                "can_run() is False: skipping upstream test build/run in this environment.")

    def _run_upstream_tests(self):
        """Compile the unmodified upstream QZXingTests sources with a
        generated CMake harness (the upstream .pro is qmake-only; test
        sources and logic are unchanged, feature defines mirror upstream
        QZXing.pri) and execute them, then verify the printed decode totals
        and the encoder exception marker."""
        src = self.source_folder
        test_dir = os.path.join(src, "tests", "src", "QZXingTests")
        if not os.path.isfile(os.path.join(test_dir, "main.cpp")):
            raise ConanException(
                "Upstream QZXingTests sources not found in {}".format(test_dir))
        build_dir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(build_dir, exist_ok=True)
        qt_dep = self.dependencies["qt5-qtbase"]
        moc = os.path.join(qt_dep.package_folder, "bin", "moc") if qt_dep.package_folder else ""
        cmakelists = textwrap.dedent("""\
            cmake_minimum_required(VERSION 3.10)
            project(QZXingTests CXX)
            # CMakeDeps root config: declares Qt5::Core/Qt5::Gui/Qt5::Concurrent
            # (no per-module Qt5Core-config.cmake files are generated).
            find_package(qt5-qtbase REQUIRED)

            set(QZXING_SRC {src})
            set(TEST_SRC {test_dir})

            # Mirror the upstream src/zxing/zxing/CMakeLists.txt source set:
            # all *.cpp recursively except UnsupportedEncodingException.cpp
            # (upstream lists its header but not the translation unit).
            file(GLOB_RECURSE ZXING_CORE "${{QZXING_SRC}}/src/zxing/zxing/*.cpp")
            list(REMOVE_ITEM ZXING_CORE
                "${{QZXING_SRC}}/src/zxing/zxing/UnsupportedEncodingException.cpp")
            file(GLOB BIGINT "${{QZXING_SRC}}/src/zxing/bigint/*.cc")

            # moc explicitly: CMake AUTOMOC cannot detect Qt5 without
            # QT_VERSION_MAJOR. Same -D flags as the target so the Q_ENUMS
            # string tables match the compiled enum.
            set(QZXING_MOC {moc})
            if(NOT QZXING_MOC)
                find_program(QZXING_MOC moc)
            endif()
            add_custom_command(OUTPUT ${{CMAKE_CURRENT_BINARY_DIR}}/moc_QZXing.cpp
                COMMAND ${{QZXING_MOC}}
                        -DENABLE_ENCODER_GENERIC -DENABLE_ENCODER_QR_CODE
                        ${{QZXING_SRC}}/src/QZXing.h
                        -o ${{CMAKE_CURRENT_BINARY_DIR}}/moc_QZXing.cpp
                DEPENDS ${{QZXING_SRC}}/src/QZXing.h)
            add_custom_command(OUTPUT ${{CMAKE_CURRENT_BINARY_DIR}}/moc_ImageHandler.cpp
                COMMAND ${{QZXING_MOC}}
                        ${{QZXING_SRC}}/src/ImageHandler.h
                        -o ${{CMAKE_CURRENT_BINARY_DIR}}/moc_ImageHandler.cpp
                DEPENDS ${{QZXING_SRC}}/src/ImageHandler.h)

            add_executable(QZXingTests
                ${{TEST_SRC}}/main.cpp
                ${{TEST_SRC}}/DecodeValidator.cpp
                ${{TEST_SRC}}/ValidationStats.cpp
                ${{TEST_SRC}}/EncodeValidator.cpp
                ${{TEST_SRC}}/TestCase.cpp
                ${{TEST_SRC}}/EncoderStressTest.cpp
                ${{TEST_SRC}}/zxing/qrcode/encoder/MatrixUtilTests.cpp
                ${{TEST_SRC}}/zxing/qrcode/encoder/MaskUtilTests.cpp
                ${{TEST_SRC}}/zxing/qrcode/encoder/QRCodeTests.cpp
                ${{TEST_SRC}}/zxing/qrcode/encoder/EncoderTests.cpp
                ${{TEST_SRC}}/zxing/common/reedsolomon/ReedSolomonEncoderTests.cpp
                ${{TEST_SRC}}/zxing/common/BitArrayTests.cpp
                ${{TEST_SRC}}/zxing/qrcode/encoder/BitVectorTests.cpp
                ${{QZXING_SRC}}/src/QZXing.cpp
                ${{QZXING_SRC}}/src/ImageHandler.cpp
                ${{QZXING_SRC}}/src/CameraImageWrapper.cpp
                ${{QZXING_SRC}}/src/QZXing.h
                ${{CMAKE_CURRENT_BINARY_DIR}}/moc_QZXing.cpp
                ${{CMAKE_CURRENT_BINARY_DIR}}/moc_ImageHandler.cpp
                ${{TEST_SRC}}/backward.hpp
                ${{ZXING_CORE}}
                ${{BIGINT}}
            )
            target_include_directories(QZXingTests PRIVATE
                ${{TEST_SRC}}
                ${{TEST_SRC}}/zxing
                ${{QZXING_SRC}}/src
                ${{QZXING_SRC}}/src/zxing
                ${{QZXING_SRC}}/src/zxing/zxing
                ${{QZXING_SRC}}/src/zxing/bigint
            )
            target_compile_definitions(QZXingTests PRIVATE
                QZXING_LIBRARY
                DISABLE_LIBRARY_FEATURES
                ZXING_ICONV_CONST
                NO_ICONV
                NOFMAXL
                ENABLE_ENCODER_GENERIC
                ENABLE_ENCODER_QR_CODE
                ENABLE_DECODER_1D_BARCODES
                ENABLE_DECODER_QR_CODE
                ENABLE_DECODER_DATA_MATRIX
                ENABLE_DECODER_AZTEC
                ENABLE_DECODER_PDF17
            )
            target_link_libraries(QZXingTests PRIVATE Qt5::Core Qt5::Gui Qt5::Concurrent)
            # Upstream Encoder keeps its static helpers protected (the
            # tests call them directly; upstream itself marks the pattern
            # "temp solution for tests" in Encoder.h). Relax access
            # checking for the test binary only; test sources are
            # unmodified.
            target_compile_options(QZXingTests PRIVATE -fno-access-control)
        """).format(src=src.replace("\\", "/"), test_dir=test_dir.replace("\\", "/"),
                    moc=moc.replace("\\", "/"))
        with open(os.path.join(build_dir, "CMakeLists.txt"), "w", encoding="utf-8") as handle:
            handle.write(cmakelists)
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        self.run(
            "cmake -S {src} -B {build} -DCMAKE_TOOLCHAIN_FILE={tc} -DCMAKE_BUILD_TYPE={bt} -DCMAKE_PREFIX_PATH={prefix}".format(
                src=shlex.quote(build_dir), build=shlex.quote(build_dir),
                tc=shlex.quote(toolchain),
                bt=shlex.quote(str(self.settings.build_type)),
                prefix=shlex.quote(self.generators_folder)),
            cwd=build_dir)
        self.run("cmake --build {} -j{}".format(
            shlex.quote(build_dir), build_jobs(self)), cwd=build_dir)
        # main.cpp resolves "../../resources/resources/" relative to the
        # cwd, i.e. <build_folder>/resources/resources. The qzxing-test-
        # resources submodule is absent from the source tarball (see
        # notes.md); when it was placed at <source_folder>/tests/resources
        # for the device run, link/copy it into position so the decode
        # suite runs against the full 1192-image corpus.
        # QZXING_RESOURCES_DIR: escape hatch for environments that have the
        # submodule checked out elsewhere (e.g. the real-device run).
        # Unset -> upstream prints Total: [0] and the decode-corpus checks
        # are skipped gracefully; the 46-method unit/encoder suite still
        # runs and is still verified.
        resources_src = os.environ.get("QZXING_RESOURCES_DIR")
        if resources_src:
            if not os.path.isdir(resources_src):
                raise ConanException(
                    "QZXING_RESOURCES_DIR={} is not a directory".format(resources_src))
        else:
            resources_src = os.path.join(src, "tests", "resources")
        resources_link = os.path.join(self.build_folder, "resources")
        if not os.path.lexists(resources_link) and os.path.isdir(resources_src):
            try:
                os.symlink(resources_src, resources_link)
            except OSError:
                shutil.copytree(resources_src, resources_link)
        run_dir = os.path.join(build_dir, "bin")
        os.makedirs(run_dir, exist_ok=True)
        log = os.path.join(build_dir, "QZXingTests.log")
        self.run(
            "QT_QPA_PLATFORM=offscreen LD_LIBRARY_PATH={paths}:$LD_LIBRARY_PATH {exe} > {log} 2>&1".format(
                paths=shlex.quote(os.pathsep.join(self._host_lib_dirs())),
                exe=shlex.quote(os.path.join(build_dir, "QZXingTests")),
                log=shlex.quote(log)),
            cwd=run_dir)
        with open(log, encoding="utf-8", errors="replace") as handle:
            output = handle.read()
        # The decode corpus is the resources/ subdir inside the checkout
        # (upstream main.cpp resolves ../../resources/resources/). The
        # Debian tarball ships an EMPTY tests/resources placeholder
        # (submodule not populated), so isdir() on the parent alone is
        # not enough to decide the corpus is present.
        resources_present = os.path.isdir(os.path.join(resources_src, "resources"))
        self._verify_upstream_output(output, resources_present=resources_present)

    def _verify_upstream_output(self, output, resources_present):
        totals = re.findall(
            r"Total:\s*\[\s*(\d+)\s*\]\s*,\s*successful:\s*\[\s*(\d+)\s*\]\s*,\s*failed:\s*\[\s*(\d+)\s*\]\s*,\s*inconsistencies:\s*\[\s*(\d+)\s*\]",
            output)
        if not totals:
            raise ConanException(
                "QZXingTests printed no Total: result lines; output tail:\n{}".format(output[-2000:]))
        decode = None
        if resources_present:
            if len(totals) != 1:
                raise ConanException(
                    "Expected exactly one decode Total: line with resources present, got {}:\n{}".format(
                        len(totals), output[-2000:]))
            decode = [int(x) for x in totals[0]]
            total, successful, failed, inconsistent = decode
            # Healthy-run signature, established on the OHOS device run and
            # corroborated against upstream's own committed reference log
            # (tests/src/QZXingTests/qzxing_decode_3_0_alpha_0_3_test_results.log):
            # 12 of the 17 per-format rows are byte-identical to that log;
            # the remaining deltas are upstream code evolution from 3.0-alpha
            # to 3.3.0 (RSS_EXPANDED decoder rewritten: 0/245 -> 235/10,
            # QR_CODE inconsistencies 13 -> 2, UPC_A 101/66/3 -> 104/63/7,
            # RSS_14 one image flips success -> failed). See notes.md.
            expected_totals = (1110, 851, 237, 22)
            if (total, successful, failed, inconsistent) != expected_totals:
                raise ConanException(
                    "Decode totals {} != expected {} (qzxing-test-resources corpus; "
                    "if the corpus was updated, refresh the expected per-format "
                    "signature in this function and notes.md)".format(
                        (total, successful, failed, inconsistent), expected_totals))
            expected_fmt = {
                "AZTEC": (13, 21, 2),
                "CODABAR": (11, 0, 0),
                "CODE_39": (23, 0, 2),
                "CODE_93": (3, 0, 0),
                "CODE_128": (47, 1, 1),
                "DATA_MATRIX": (26, 11, 0),
                "EAN_8": (8, 0, 0),
                "EAN_13": (120, 37, 2),
                "ITF": (21, 6, 0),
                "PDF_417": (39, 21, 1),
                "QR_CODE": (149, 29, 2),
                "RSS_14": (0, 30, 0),
                "RSS_EXPANDED": (235, 10, 0),
                "UPC_A": (104, 63, 7),
                "UPC_E": (47, 8, 2),
                "UPC_EAN_EXTENSION": (2, 0, 0),
                "CODE_128_GS1": (3, 0, 3),
            }
            decoder_lines = re.findall(
                r"Decoder:\s*\[\s*\"([^\"]+)\"\s*\]\s*,\s*successful:\s*\[\s*(\d+)\s*\]\s*,\s*failed:\s*\[\s*(\d+)\s*\]\s*,\s*inconsistencies:\s*\[\s*(\d+)\s*\]",
                output)
            if len(decoder_lines) != len(expected_fmt):
                raise ConanException(
                    "Expected {} per-format Decoder: lines, got {}:\n{}".format(
                        len(expected_fmt), len(decoder_lines), output[-2000:]))
            for name, succ, fl, inc in decoder_lines:
                want = expected_fmt.get(name)
                if want is None:
                    raise ConanException("Unexpected decoder format {!r} in output".format(name))
                got = (int(succ), int(fl), int(inc))
                if got != want:
                    raise ConanException(
                        "Per-format {} mismatch: got {} expected {}".format(name, got, want))
        # Encoder suites: upstream assertions throw zxing::Exception, which
        # EncodeValidator catches and prints as "Exception: ...". A clean
        # run of all 46 methods prints none.
        if "Exception:" in output:
            marker = output.index("Exception:")
            raise ConanException(
                "Upstream encoder suite reported an exception:\n{}".format(
                    output[max(0, marker - 500):marker + 1500]))
        self.output.info(
            "Upstream tests verified: decode total={} successful={} failed={} inconsistencies={}; encoder suites clean (no Exception: marker)".format(
                *(decode if decode else [0, 0, 0, 0])))

    def _host_lib_dirs(self):
        lib_paths = []
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                lib_paths.append(os.path.join(dep.package_folder, libdir))
        return lib_paths

    def _create_symlink_shim(self):
        """Copy Qt ABI aliases when the OHOS workspace rejects symlinks."""
        shim_dir = os.path.join(self.build_folder, "conan_tools")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "ln")
        real_ln = shutil.which("ln") or "/system/bin/ln"
        with open(shim, "w", encoding="utf-8") as shim_file:
            shim_file.write(
                "#!/bin/sh\n"
                f"if {shlex.quote(real_ln)} \"$@\"; then\n"
                "  exit 0\n"
                "fi\n"
                "symbolic=0\n"
                "while [ $# -gt 0 ]; do\n"
                "  case \"$1\" in\n"
                "    --symbolic) symbolic=1; shift ;;\n"
                "    --) shift; break ;;\n"
                "    -*) flags=${1#-}; case \"$flags\" in *s*) symbolic=1 ;; esac; shift ;;\n"
                "    *) break ;;\n"
                "  esac\n"
                "done\n"
                "if [ \"$symbolic\" = 1 ] && [ $# -eq 2 ]; then\n"
                "  rm -f \"$2\"\n"
                "  cp -f \"$1\" \"$2\"\n"
                "  exit $?\n"
                "fi\n"
                "exit 1\n"
            )
        os.chmod(shim, 0o755)
        return shim_dir

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "QZXing.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include", "qzxing"))
        copy(self, "QZXing_global.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include", "qzxing"))
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        built = glob.glob(os.path.join(self.build_folder, "lib", "libqzxing.so*"))
        real = None
        for candidate in built:
            if os.path.basename(candidate) == "libqzxing.so.3.3.0":
                real = candidate
                break
        if real is None and built:
            real = built[0]
        if real is None:
            raise ConanException(
                "No libqzxing.so* produced in {}".format(
                    os.path.join(self.build_folder, "lib")))
        # The device rejects symlinks (os.symlink raises EPERM) so it used
        # to fall back to copies there, but some CI workers DO allow them.
        # Linking the first name to its own basename produced a self-
        # referential link chain on those workers, and the CMakeDeps
        # conan_package_library_targets() find_library() call then saw
        # dangling links -> "Library 'qzxing' not found in package"
        # (CI #65168). Copy the real binary under all three names instead:
        # deterministic on every filesystem and keeps the Debian-style
        # SONAME libqzxing.so.3 layout.
        for name in ("libqzxing.so.3.3.0", "libqzxing.so.3", "libqzxing.so"):
            shutil.copy2(real, os.path.join(lib_dir, name))
        if str(self.settings.os) == "OHOS":
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = os.environ.get("HNP_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException("Required OHOS signing tool not found: {}".format(tool))
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            self._remove_codesign_section(objcopy, shared_object)
            self.run("{} sign -inFile {} -outFile {} -selfSign 1".format(
                shlex.quote(signer),
                shlex.quote(shared_object),
                shlex.quote(shared_object)))

    def _remove_codesign_section(self, objcopy, shared_object):
        try:
            probe = subprocess.run(
                [objcopy, "--dump-section", ".codesign=/dev/null", shared_object],
                text=True,
                capture_output=True,
                check=False)
        except OSError as exc:
            raise ConanException("Required OHOS objcopy tool failed: {}".format(objcopy)) from exc
        if probe.returncode != 0:
            return
        self.run("{} --remove-section .codesign {}".format(
            shlex.quote(objcopy),
            shlex.quote(shared_object)))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "qzxing")
        self.cpp_info.set_property("cmake_target_name", "qzxing::qzxing")
        self.cpp_info.libs = ["qzxing"]
        self.cpp_info.includedirs = ["include", "include/qzxing"]
        # Upstream gates the encoder API with these macros; they are part of
        # the library configuration, so consumers need them too.
        self.cpp_info.defines = ["ENABLE_ENCODER_GENERIC", "ENABLE_ENCODER_QR_CODE"]
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui"]
