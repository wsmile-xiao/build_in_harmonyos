#!/usr/bin/env python3
"""Conan recipe for Enzyme — LLVM automatic differentiation plugin.

Build strategy on OHOS SDK LLVM 15 (see knowledge E216-draft):
  - OHOS SDK LLVM ships only monolithic libLLVM-15.so, no .a stubs
    (LLVMExports.cmake references LLVMDemangle.a etc. → FATAL_ERROR).
  - No llvm-tblgen binary → TableGen .inc files cannot be generated.
  - No lit/llvm-lit/FileCheck → upstream 1523 lit tests cannot run.
  - cmake-overlay/ provides:
      * LLVMConfig.cmake  — wraps SDK LLVM, creates IMPORTED targets
                            pointing to monolithic libLLVM-15.so,
                            skips the problematic LLVMExports.cmake.
      * AddLLVM.cmake      — stub implementations of tablegen(),
                            add_llvm_library(), add_public_tablegen_target(),
                            configure_lit_site_cfg(), get_llvm_lit_path().
      * stub-tblgen.sh     — generates minimal .inc stub files
                            (handleBLAS / attributeTablegen return false).
    stub-tblgen.sh MUST be executable (chmod +x); otherwise
    execute_process() hits "permission denied" and produces empty files,
    causing compile errors at CallDerivatives.cpp:2254 (handleBLAS
    undeclared) and Utils.cpp:410 (attributeTablegen undeclared).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
import os


class EnzymeConan(ConanFile):
    name = "enzyme"
    version = "0.0.284"
    description = "Enzyme High-Performance Automatic Differentiator of LLVM and MLIR"
    license = "MIT"
    homepage = "https://enzyme.mit.edu"
    url = "https://github.com/EnzymeAD/Enzyme"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # External toolchain dependency — NOT a Conan requirement.
    _OHOS_SDK_LLVM = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm"
    _OVERLAY_FILES = ("LLVMConfig.cmake", "AddLLVM.cmake", "stub-tblgen.sh")

    def validate(self):
        """OHOS SDK LLVM 15 only provides Release libraries.
        Non-Release build_type may cause link errors against the SDK's
        Release-only libLLVM-15.so; warn so the user can choose.
        """
        if str(self.settings.build_type) != "Release":
            self.output.warning(
                f"OHOS SDK LLVM 15 only provides Release libraries. "
                f"build_type={self.settings.build_type} may cause link errors."
            )

    def export_sources(self):
        export_conandata_patches(self)
        overlay_src = os.path.join(self.recipe_folder, "cmake-overlay")
        if os.path.isdir(overlay_src):
            for fname in self._OVERLAY_FILES:
                fpath = os.path.join(overlay_src, fname)
                if os.path.isfile(fpath):
                    copy(self, fname, src=overlay_src, dst=self.export_sources_folder)
            self.output.info("Exported cmake-overlay for OHOS SDK LLVM missing components")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        overlay_dst = os.path.join(self.source_folder, "cmake-overlay")
        os.makedirs(overlay_dst, exist_ok=True)
        for src_base in (self.export_sources_folder, self.recipe_folder):
            if not src_base or not os.path.isdir(src_base):
                continue
            copied_any = False
            for fname in self._OVERLAY_FILES:
                for cand in (os.path.join(src_base, fname),
                             os.path.join(src_base, "cmake-overlay", fname)):
                    cand_abs = os.path.abspath(cand)
                    if cand_abs == os.path.abspath(overlay_dst):
                        continue
                    if os.path.isfile(cand):
                        src_dir = os.path.dirname(cand)
                        if os.path.abspath(src_dir) == os.path.abspath(overlay_dst):
                            continue
                        dst_file = os.path.join(overlay_dst, fname)
                        with open(cand, "rb") as rfh:
                            data = rfh.read()
                        with open(dst_file, "wb") as wfh:
                            wfh.write(data)
                        if fname == "stub-tblgen.sh":
                            try:
                                os.chmod(dst_file, 0o755)
                            except OSError as e:
                                self.output.warning(f"chmod +x stub-tblgen.sh failed: {e}")
                        self.output.info(f"Copied {fname} to source folder cmake-overlay")
                        copied_any = True
                        break
            if copied_any:
                break

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENZYME_ENABLE_PLUGINS"] = "ON"
        tc.variables["ENZYME_CLANG"] = "OFF"
        tc.variables["ENZYME_MLIR"] = "OFF"
        tc.variables["ENZYME_FORTRAN"] = "OFF"
        tc.variables["ENZYME_BC_LOADER"] = "OFF"
        if self.options.shared:
            tc.variables["ENZYME_STATIC_LIB"] = "OFF"
            tc.variables["ENZYME_EXTERNAL_SHARED_LIB"] = "ON"
        else:
            tc.variables["ENZYME_STATIC_LIB"] = "ON"
            tc.variables["ENZYME_EXTERNAL_SHARED_LIB"] = "OFF"
        overlay_dir = os.path.join(self.source_folder, "cmake-overlay")
        if os.path.isdir(overlay_dir) and os.path.isfile(os.path.join(overlay_dir, "LLVMConfig.cmake")):
            tc.variables["LLVM_DIR"] = overlay_dir
        else:
            llvm_dir = os.environ.get("LLVM_DIR") or os.environ.get("OHOS_LLVM_DIR")
            if not llvm_dir:
                candidate_dirs = [
                    os.path.join(self._OHOS_SDK_LLVM, "lib/cmake/llvm"),
                    "/usr/lib/llvm-15/lib/cmake/llvm",
                    "/usr/lib/cmake/llvm",
                    "/usr/local/opt/llvm@15/lib/cmake/llvm",
                ]
                for d in candidate_dirs:
                    if os.path.isfile(os.path.join(d, "LLVMConfig.cmake")):
                        llvm_dir = d
                        break
            if llvm_dir and os.path.isfile(os.path.join(llvm_dir, "LLVMConfig.cmake")):
                tc.variables["LLVM_DIR"] = llvm_dir
            else:
                self.output.warning("LLVM_DIR not found — building without LLVM cmake config")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake_file = os.path.join(self.source_folder, "enzyme", "CMakeLists.txt")
        if os.path.isfile(cmake_file):
            with open(cmake_file, "r") as f:
                content = f.read()
            content = content.replace(
                'if (ENZYME_ENABLE_PLUGINS)\n    add_subdirectory(test)\nendif()',
                '# SKIP: test subdirectory requires LLVM lit/cmake modules not in OHOS SDK (E216-draft)\n#if (ENZYME_ENABLE_PLUGINS)\n#    add_subdirectory(test)\n#endif()'
            )
            with open(cmake_file, "w") as f:
                f.write(content)
            self.output.info("Skipped test subdirectory in CMakeLists.txt")
        cmake = CMake(self)
        src_dir = os.path.join(self.source_folder, "enzyme")
        cmake.configure(build_script_folder=src_dir)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["LLVMEnzyme-15", "LLDEnzyme-15"]
        self.cpp_info.includedirs = []