#!/usr/bin/env python3
"""Conan recipe for HarfBuzz 14.4.0.1 (Meson).

14.4.0.1 = 14.4.0 + ICU component enabled (libharfbuzz-icu / harfbuzz-icu.pc /
hb-icu.h). Source is the upstream 14.4.0 release; only the Meson option set
changes (icu=enabled, requires icu4c/78) so WebKitGTK's
`find_package(HarfBuzz REQUIRED COMPONENTS ICU)` can resolve HarfBuzz::ICU.
"""

import glob
import os
import re
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class HarfbuzzConan(ConanFile):
    name = "harfbuzz"
    version = "14.4.0.1"
    description = "OpenType text shaping engine"
    license = "MIT"
    homepage = "https://harfbuzz.github.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
            # icu4c/78 制品为静态库（shared=False），静态链入 libharfbuzz-icu.so
            # 时会把 ICU 全部符号（*_78）导出到动态符号表，导致上游 check-symbols
            # 期望的 def（仅 hb_ 前缀）与实际符号表不一致而失败。用
            # --exclude-libs=ALL 隐藏静态库（.a）符号；hb-icu.cc 目标文件符号
            # （hb_icu_script_to_script 等）不受影响，仍正常导出。
            if self.settings.os in ("Linux", "OHOS"):
                self.conf.append(
                    "tools.build:sharedlinkflags", ["-Wl,--exclude-libs,ALL"]
                )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # FreeType is published with --with-harfbuzz=no, so this edge is acyclic.
        self.requires("freetype/2.14.3")
        # ICU component (libharfbuzz-icu) — required by WebKitGTK's
        # `find_package(HarfBuzz REQUIRED COMPONENTS ICU)`; icu4c/78 provides
        # icu-uc.pc (Version 78.3 >= harfbuzz's icu_min_version 49.0).
        self.requires("icu4c/78")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"])
        local_archive = os.environ.get("HARFBUZZ_SOURCE_ARCHIVE")
        if local_archive:
            archive_path = Path(local_archive).resolve()
            if not archive_path.is_file():
                raise ConanInvalidConfiguration(
                    f"HARFBUZZ_SOURCE_ARCHIVE is not a regular file: {archive_path}"
                )
            source["url"] = archive_path.as_uri()
            source["filename"] = archive_path.name
        get(self, **source, strip_root=True)

    def _resolve_tool(self, tool, llvm=True):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c", "")
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        version_suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
        )

        candidates = [compiler_executables.get(tool)]
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(compiler_dir, f"llvm-{tool}{version_suffix}"),
                        os.path.join(compiler_dir, f"llvm-{tool}"),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        if llvm and version_suffix:
            candidates.append(f"llvm-{tool}{version_suffix}")
        if llvm:
            candidates.append(f"llvm-{tool}")
        candidates.append(tool)

        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate)
            if resolved:
                return resolved

        raise ConanInvalidConfiguration(f"required build tool was not found: {tool}")

    def generate(self):
        PkgConfigDeps(self).generate()
        # icu4c/78 的 PkgConfigDeps 产物名为 icu4c.pc；harfbuzz meson 通过
        # dependency('icu-uc') 查找，故转发 icu-uc.pc（与 tectonic 同款处理）。
        icu4c_pc = os.path.join(self.generators_folder, "icu4c.pc")
        icu_uc_pc = os.path.join(self.generators_folder, "icu-uc.pc")
        if os.path.isfile(icu4c_pc) and not os.path.isfile(icu_uc_pc):
            shutil.copy2(icu4c_pc, icu_uc_pc)
        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "libdir": "lib",
                "glib": "disabled",
                "gobject": "disabled",
                "cairo": "disabled",
                "chafa": "disabled",
                "png": "disabled",
                "zlib": "disabled",
                "icu": "enabled",
                "graphite": "disabled",
                "graphite2": "disabled",
                "freetype": "enabled",
                "fontations": "disabled",
                "gdi": "disabled",
                "directwrite": "disabled",
                "coretext": "disabled",
                "harfrust": "disabled",
                "kbts": "disabled",
                "wasm": "disabled",
                "raster": "enabled",
                "vector": "enabled",
                "gpu": "enabled",
                "gpu_demo": "disabled",
                "subset": "enabled",
                "tests": "enabled",
                "introspection": "disabled",
                "docs": "disabled",
                "doc_tests": False,
                "utilities": "enabled",
                "benchmark": "disabled",
                "with_libstdcxx": False,
                "experimental_api": False,
                "ragel_subproject": False,
            }
        )
        toolchain.generate()

        if self.settings.os in ("Linux", "OHOS"):
            ar = self._resolve_tool("ar")
            ranlib = self._resolve_tool("ranlib")
            native_file = os.path.join(
                self.generators_folder, "conan_meson_native.ini"
            )
            if os.path.isfile(native_file):
                with open(native_file, encoding="utf-8") as handle:
                    content = handle.read()
                if "\nar =" not in content and "[binaries]" in content:
                    archive_tools = (
                        "[binaries]\nar = '{}'\nranlib = '{}'\n".format(
                            ar, ranlib
                        )
                    )
                    content = content.replace("[binaries]\n", archive_tools, 1)
                    with open(native_file, "w", encoding="utf-8") as handle:
                        handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        self._bind_python_entrypoints()
        meson = Meson(self)
        meson.configure()
        meson.build()

        if self.settings.os in ("Linux", "OHOS"):
            if self.settings.os == "OHOS" and self.options.shared:
                self._sign_shared_libs(os.path.join(self.build_folder, "src"))
            test_tmp = os.path.join(self.build_folder, "test-tmp")
            os.makedirs(test_tmp, exist_ok=True)
            test_env = Environment()
            test_env.define("NM", self._resolve_tool("nm"))
            test_env.define("OBJDUMP", self._resolve_tool("objdump"))
            test_env.define("LDD", self._resolve_tool("readelf") + " -d")
            test_env.define("MESON_TESTTHREADS", "1")
            test_env.define("TMPDIR", test_tmp)
            with test_env.vars(self).apply():
                meson.test()
        else:
            meson.test()

        self._export_upstream_evidence()

    def _bind_python_entrypoints(self):
        if self.settings.os != "OHOS":
            return

        python = shutil.which("python3")
        if not python or not os.access(python, os.X_OK):
            raise ConanInvalidConfiguration("an executable python3 was not found")

        env_shebang = b"#!/usr/bin/env python3"
        bound_shebang = b"#!" + os.fsencode(python)
        rebound = []
        for script in Path(self.source_folder).rglob("*"):
            if not script.is_file():
                continue
            with script.open("rb") as handle:
                first_line = handle.readline(len(env_shebang) + 2)
                if first_line != env_shebang + b"\n":
                    continue
                payload = first_line + handle.read()
            script.write_bytes(bound_shebang + payload[len(env_shebang) :])
            rebound.append(script.relative_to(self.source_folder).as_posix())

        if "src/gen-hb-version.py" not in rebound:
            raise ConanInvalidConfiguration(
                "HarfBuzz Python entrypoint inventory changed: "
                "src/gen-hb-version.py was not rebound"
            )
        self.output.info(
            f"Rebound {len(rebound)} Python entrypoints to {python}"
        )

    def _export_upstream_evidence(self):
        evidence_value = os.environ.get("HARFBUZZ_UPSTREAM_EVIDENCE_DIR")
        if not evidence_value:
            return
        evidence_dir = os.path.abspath(evidence_value)
        os.makedirs(evidence_dir, exist_ok=True)
        evidence_files = {
            "intro-tests.json": os.path.join(
                self.build_folder, "meson-info", "intro-tests.json"
            ),
            "intro-targets.json": os.path.join(
                self.build_folder, "meson-info", "intro-targets.json"
            ),
            "testlog.json": os.path.join(
                self.build_folder, "meson-logs", "testlog.json"
            ),
            "testlog.txt": os.path.join(
                self.build_folder, "meson-logs", "testlog.txt"
            ),
        }
        for destination_name, source_path in evidence_files.items():
            if not os.path.isfile(source_path):
                raise ConanInvalidConfiguration(
                    f"upstream evidence file is missing: {source_path}"
                )
            shutil.copy2(source_path, os.path.join(evidence_dir, destination_name))

    def package(self):
        Meson(self).install()
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_shared_libs(os.path.join(self.package_folder, "lib"))

    def _sign_shared_libs(self, libdir):
        candidates = glob.glob(
            os.path.join(libdir, "**", "*.so"), recursive=True
        )
        candidates += glob.glob(
            os.path.join(libdir, "**", "*.so.*"), recursive=True
        )
        shared_libraries = [
            library
            for library in sorted(set(candidates))
            if not os.path.islink(library)
            and os.path.isfile(library)
            and re.search(r"\.so\.\d+(?:\.\d+)+$", library)
        ]
        if not any(
            os.path.basename(library).startswith("libharfbuzz.so.")
            for library in shared_libraries
        ):
            raise ConanInvalidConfiguration(
                f"versioned libharfbuzz shared library is missing under {libdir}"
            )

        objcopy = self._resolve_tool("objcopy")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        for library in shared_libraries:
            signed_library = f"{library}.ohos-signed"
            if os.path.lexists(signed_library):
                raise ConanInvalidConfiguration(
                    f"stale signed-library output exists: {signed_library}"
                )
            mode = os.stat(library).st_mode
            try:
                self.run(
                    shlex.join(
                        [objcopy, "--remove-section", ".codesign", library]
                    )
                )
                self.run(
                    shlex.join(
                        [
                            signer,
                            "sign",
                            "-inFile",
                            library,
                            "-outFile",
                            signed_library,
                            "-selfSign",
                            "1",
                        ]
                    )
                )
                if not os.path.isfile(signed_library):
                    raise ConanInvalidConfiguration(
                        f"signer did not create output: {signed_library}"
                    )
                os.chmod(signed_library, mode)
                os.replace(signed_library, library)
            finally:
                if os.path.lexists(signed_library):
                    os.remove(signed_library)

        self._materialize_shared_aliases(shared_libraries)

    def _materialize_shared_aliases(self, shared_libraries):
        for library in shared_libraries:
            stem, version = library.rsplit(".so.", 1)
            aliases = [f"{stem}.so.{version.split('.', 1)[0]}", f"{stem}.so"]
            for alias in aliases:
                if os.path.lexists(alias):
                    os.remove(alias)
                shutil.copy2(library, alias)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "harfbuzz")
        # utilities=enabled 安装 hb-shape / hb-subset / hb-info 等 CLI 工具
        # （R38 / L0k：CLI 包必须声明 commands.json；与顶层 tool 类型对齐）
        if os.path.isdir(os.path.join(self.package_folder, "bin")):
            self.cpp_info.bindirs = ["bin"]

        core = self.cpp_info.components["harfbuzz"]
        core.libs = ["harfbuzz"]
        core.includedirs = ["include/harfbuzz"]
        core.requires = ["freetype::freetype"]
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            core.system_libs = ["pthread", "m"]
        core.set_property("cmake_target_name", "harfbuzz::harfbuzz")
        core.set_property("pkg_config_name", "harfbuzz")

        for component_name in ("subset", "raster", "vector", "gpu"):
            library_name = f"harfbuzz-{component_name}"
            component = self.cpp_info.components[component_name]
            component.libs = [library_name]
            component.includedirs = ["include/harfbuzz"]
            component.requires = ["harfbuzz"]
            component.set_property(
                "cmake_target_name", f"harfbuzz::harfbuzz-{component_name}"
            )
            component.set_property("pkg_config_name", library_name)

        # ICU integration component (libharfbuzz-icu): WebKitGTK's
        # FindHarfBuzz.cmake resolves HarfBuzz::ICU via pkg-config
        # `harfbuzz-icu` + hb-icu.h + libharfbuzz-icu.
        icu = self.cpp_info.components["harfbuzz-icu"]
        icu.libs = ["harfbuzz-icu"]
        icu.includedirs = ["include/harfbuzz"]
        icu.requires = ["harfbuzz", "icu4c::icu4c"]
        icu.set_property("cmake_target_name", "harfbuzz::harfbuzz-icu")
        icu.set_property("pkg_config_name", "harfbuzz-icu")
