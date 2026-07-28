#!/usr/bin/env python3
"""Conan recipe — libxslt 1.1.45 with xsltproc enabled."""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, get


class LibxsltConan(ConanFile):
    name = "libxslt"
    version = "1.1.45.1"
    description = "libxslt with xsltproc enabled for build-time XSLT transforms"
    license = "MIT"
    homepage = "https://gitlab.gnome.org/GNOME/libxslt"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
        user_toolchains = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain",
            default=[],
            check_type=list,
        )
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(user_toolchains)
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake"))
        candidates.extend(
            sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake; set OHOS_NDK_HOME or "
            "tools.cmake.cmaketoolchain:user_toolchain in the Conan profile."
        )

    def _ohos_llvm_bin(self):
        toolchain = self._ohos_toolchain()
        native_dir = os.path.abspath(os.path.join(os.path.dirname(toolchain), "..", ".."))
        llvm_bin = os.path.join(native_dir, "llvm", "bin")
        return llvm_bin if os.path.isdir(llvm_bin) else ""

    def _cmake_defs(self):
        xml2 = self.dependencies["libxml2"].package_folder
        defs = [
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DBUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            "-DLIBXSLT_WITH_CRYPTO=OFF",
            "-DLIBXSLT_WITH_PYTHON=OFF",
            "-DLIBXSLT_WITH_PROGRAMS=ON",
            "-DLIBXSLT_WITH_TESTS=OFF",
            '-DLibXml2_DIR="{}"'.format(os.path.join(xml2, "lib", "cmake", "libxml2")),
            '-DCMAKE_PREFIX_PATH="{}"'.format(xml2),
        ]
        if self.settings.os == "OHOS":
            defs.insert(0, '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(self._ohos_toolchain()))
            defs.insert(1, "-DOHOS_ARCH=arm64-v8a")
            ar = self._resolve_tool("ar")
            ranlib = self._resolve_tool("ranlib")
            nm = self._resolve_tool("nm")
            defs.extend(
                [
                    '-DCMAKE_AR:FILEPATH="{}"'.format(ar),
                    '-DCMAKE_RANLIB:FILEPATH="{}"'.format(ranlib),
                    '-DCMAKE_NM:FILEPATH="{}"'.format(nm),
                    '-DCMAKE_C_COMPILER_AR:FILEPATH="{}"'.format(ar),
                    '-DCMAKE_C_COMPILER_RANLIB:FILEPATH="{}"'.format(ranlib),
                ]
            )
        return defs

    def build(self):
        apply_conandata_patches(self)
        build_dir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake -B "{}" -S "{}" {}'.format(build_dir, self.source_folder, " ".join(self._cmake_defs())))
        self.run('cmake --build "{}"'.format(build_dir))

    def package(self):
        build_dir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(build_dir, self.package_folder))
        if self.settings.os == "OHOS":
            self._sign_ohos_elfs()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resolve_tool(self, tool, llvm=True):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        compiler = compiler_executables.get("c", "")
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        version_suffix = (
            compiler_name[len("clang"):] if compiler_name.startswith("clang") else ""
        )

        env_tool = {
            "objcopy": "LLVM_OBJCOPY",
            "binary-sign-tool": "BINARY_SIGN_TOOL",
        }.get(tool)
        candidates = [
            os.environ.get(env_tool) if env_tool else None,
            compiler_executables.get(tool),
        ]
        ohos_llvm_bin = ""
        if llvm and self.settings.os == "OHOS":
            ohos_llvm_bin = self._ohos_llvm_bin()

        if ohos_llvm_bin:
            candidates.extend(
                [
                    os.path.join(ohos_llvm_bin, "llvm-{}{}".format(tool, version_suffix)),
                    os.path.join(ohos_llvm_bin, "llvm-{}".format(tool)),
                    os.path.join(ohos_llvm_bin, tool),
                ]
            )
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(
                            compiler_dir, "llvm-{}{}".format(tool, version_suffix)
                        ),
                        os.path.join(compiler_dir, "llvm-{}".format(tool)),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        if llvm and version_suffix:
            candidates.append("llvm-{}{}".format(tool, version_suffix))
        if llvm:
            candidates.append("llvm-{}".format(tool))
        candidates.append(tool)

        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate)
            if resolved:
                return resolved

        raise ConanInvalidConfiguration(
            "required OHOS tool was not found: {}".format(tool)
        )

    def _sign_ohos_elfs(self):
        targets = {}
        lib_dir = os.path.join(self.package_folder, "lib")
        shared_libs = glob.glob(os.path.join(lib_dir, "**", "*.so"), recursive=True)
        shared_libs += glob.glob(os.path.join(lib_dir, "**", "*.so.*"), recursive=True)
        for shared_lib in shared_libs:
            if (
                os.path.isfile(shared_lib)
                and not os.path.islink(shared_lib)
                and self._is_elf(shared_lib)
            ):
                targets[shared_lib] = False

        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for name in os.listdir(bin_dir):
                binary = os.path.join(bin_dir, name)
                if (
                    os.path.isfile(binary)
                    and not os.path.islink(binary)
                    and self._is_elf(binary)
                ):
                    targets[binary] = True

        if not targets:
            return

        objcopy = self._resolve_tool("objcopy")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        for target, executable in sorted(targets.items()):
            signed = target + ".signed"
            mode = os.stat(target).st_mode
            self.run(
                "{} 2>/dev/null || true".format(
                    shlex.join([objcopy, "--remove-section", ".codesign", target])
                )
            )
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        target,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ]
                )
            )
            os.replace(signed, target)
            if executable:
                os.chmod(target, mode | 0o755)
            else:
                os.chmod(target, mode)

    def package_info(self):
        self.cpp_info.libs = ["exslt", "xslt"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "LibXslt")
        self.cpp_info.set_property("cmake_target_name", "LibXslt::LibXslt")
        self.cpp_info.set_property("pkg_config_name", "libxslt")
        bin_dir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
