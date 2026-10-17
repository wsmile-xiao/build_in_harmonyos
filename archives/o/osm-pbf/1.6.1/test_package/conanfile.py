#!/usr/bin/env python3
"""Conan test_package — osm-pbf 1.6.1（R34 实质依赖）。

1. 编译并链接消费者程序：#include <osmpbf/osmpbf.h>，调用 BlobHeader API
2. 可运行时执行测试二进制；并跑 osmpbf-outline sample.pbf（对齐 Homebrew）
3. 交叉构建：必须完成 compile/link（检测坏头文件/缺符号）；跳过 qemu 运行
"""
from __future__ import annotations

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import check_sha256


class OsmPbfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _protobuf_prefix(self) -> str:
        """Locate OHOS protobuf/abseil prefix for consumer link (headers + libs)."""
        env = os.environ.get("OHOS_DEPS_PREFIX", "")
        candidates = [env] if env else []
        candidates += [
            "/root/ohos-deps",
            os.path.expanduser("~/ohos-deps"),
            os.path.join(self.build_folder, "ohos-deps"),
        ]
        for prefix in candidates:
            if not prefix:
                continue
            cfg = os.path.join(prefix, "lib", "cmake", "protobuf", "protobuf-config.cmake")
            if os.path.isfile(cfg):
                return prefix
        # Fetch cmd-pkgs protobuf+abseil into build folder (same source as recipe)
        prefix = os.path.join(self.build_folder, "ohos-deps")
        self._fetch_cmd_pkgs(prefix)
        cfg = os.path.join(prefix, "lib", "cmake", "protobuf", "protobuf-config.cmake")
        if not os.path.isfile(cfg):
            raise ConanInvalidConfiguration(
                "protobuf cmake config not found; set OHOS_DEPS_PREFIX or allow network for cmd-pkgs"
            )
        return prefix

    def _parent_ohos_deps(self):
        """Load ohos_deps (with sha256) from sibling conandata.yml."""
        path = os.path.join(os.path.dirname(self.recipe_folder), "conandata.yml")
        try:
            import yaml  # Conan env provides PyYAML

            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            deps = data.get("ohos_deps") or []
        except Exception as exc:
            raise ConanInvalidConfiguration(
                f"failed to load parent conandata.yml ohos_deps: {exc}"
            ) from exc
        # test_package only needs abseil + protobuf for linking
        return [d for d in deps if d["name"] in ("abseil-cpp", "protobuf")]

    def _fetch_cmd_pkgs(self, prefix: str) -> None:
        os.makedirs(prefix, exist_ok=True)
        dl = os.path.join(self.build_folder, "deps-dl")
        os.makedirs(dl, exist_ok=True)
        for dep in self._parent_ohos_deps():
            name, ver = dep["name"], dep["version"]
            expected = dep.get("sha256") or ""
            if not expected:
                raise ConanInvalidConfiguration(
                    f"ohos_deps[{name}/{ver}].sha256 missing in parent conandata.yml"
                )
            marker = os.path.join(prefix, "lib", "cmake", "protobuf", "protobuf-config.cmake")
            if name == "protobuf" and os.path.isfile(marker):
                continue
            if name == "abseil-cpp" and os.path.isdir(os.path.join(prefix, "lib", "cmake", "absl")):
                continue
            tarball = f"{name}-{ver}-ohos-aarch64.tar.gz"
            dest = os.path.join(dl, tarball)
            url = dep.get("url") or (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
                f"releases/download/pkgs/{tarball}"
            )
            urls = list(url) if isinstance(url, (list, tuple)) else [url]
            self.output.info(f"test_package fetch {name}/{ver}")
            if os.path.isfile(dest):
                os.remove(dest)
            # self.run: OHOS CI curl lives under Conan buildenv PATH
            last_err = None
            for u in urls:
                try:
                    self.run(f'curl -fL --retry 3 -o "{dest}" "{u}"')
                    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
                        break
                except Exception as exc:
                    last_err = exc
                    self.output.warning(f"download failed ({u}): {exc}")
            else:
                raise ConanInvalidConfiguration(
                    f"failed to download {name}/{ver}; last={last_err}"
                )
            check_sha256(self, dest, expected)
            extract_dir = os.path.join(dl, f"{name}-{ver}")
            os.makedirs(extract_dir, exist_ok=True)
            self.run(f'tar xzf "{dest}" -C "{extract_dir}"')
            roots = [extract_dir] + [
                os.path.join(extract_dir, d)
                for d in os.listdir(extract_dir)
                if os.path.isdir(os.path.join(extract_dir, d))
            ]
            for root in roots:
                for sub in ("bin", "lib", "include", "share"):
                    src = os.path.join(root, sub)
                    if os.path.isdir(src):
                        dst = os.path.join(prefix, sub)
                        os.makedirs(dst, exist_ok=True)
                        shutil.copytree(src, dst, dirs_exist_ok=True)

    def generate(self):
        prefix = self._protobuf_prefix()
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Pass deps prefix via dedicated var — never overwrite CMAKE_PREFIX_PATH
        # (that would hide Conan-generated osmpbf-config.cmake in generators/).
        tc.variables["OHOS_DEPS_PREFIX"] = prefix
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "BOTH"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "BOTH"
        tc.generate()

    def build(self):
        # R34: must compile + link against libosmpbf (catches bad headers / missing symbols)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Prove the consumer binary was produced
        candidates = []
        bindir = getattr(self.cpp.build, "bindir", None) or getattr(
            self.cpp.build, "bindirs", [""]
        )
        if isinstance(bindir, list):
            for b in bindir:
                candidates.append(os.path.join(self.build_folder, b, "test_osmpbf"))
        else:
            candidates.append(os.path.join(self.build_folder, bindir, "test_osmpbf"))
        candidates += glob.glob(
            os.path.join(self.build_folder, "**", "test_osmpbf"), recursive=True
        )
        if not any(os.path.isfile(p) for p in candidates):
            raise ConanInvalidConfiguration(
                "test_osmpbf binary missing after build — link against libosmpbf failed"
            )

    def test(self):
        # L0d: must call self.run() (cmake.test() / subprocess alone are rejected as stubs)
        if cross_building(self) or not can_run(self):
            self.output.info(
                "cross-building / cannot run: compile+link API test done in build(); "
                "skip qemu execution of test_osmpbf / osmpbf-outline"
            )
            return

        # OHOS /system/bin/sh (mksh) cannot exec ELF — wrap with bash
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Conan 2.x exposes bindirs (list); bindir may be absent — mirror build()
        bindir = getattr(self.cpp.build, "bindir", None) or getattr(
            self.cpp.build, "bindirs", None
        )
        if isinstance(bindir, list):
            bindir = bindir[0] if bindir else None
        if not bindir:
            bindir = self.build_folder
        test_bin = os.path.join(bindir, "test_osmpbf")
        self.run(f'{bash} -c \'"{test_bin}"\'', env="conanrun")

        pkg = self.dependencies[self.tested_reference_str].package_folder
        outline = os.path.join(pkg, "bin", "osmpbf-outline")
        sample = os.path.join(pkg, "share", "osm-pbf", "sample.pbf")
        if not os.path.isfile(outline) or not os.path.isfile(sample):
            raise ConanInvalidConfiguration("missing osmpbf-outline or sample.pbf in package")
        # Homebrew-aligned smoke: osmpbf-outline must print OSMHeader
        self.run(
            f'{bash} -c \'out=$("{outline}" "{sample}" 2>&1); echo "$out"; '
            f'echo "$out" | grep -q OSMHeader\'',
            env="conanrun",
        )
        self.output.info("osmpbf-outline sample.pbf OK (OSMHeader found)")
