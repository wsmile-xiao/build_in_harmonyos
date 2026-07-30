#!/usr/bin/env python3
"""Conan recipe — osm-pbf 1.6.1 (CMake / OSM-binary).

对齐 Homebrew formula osm-pbf：
  https://github.com/Homebrew/homebrew-core/blob/master/Formula/o/osm-pbf.rb

上游 OSM-binary v1.6.1：静态/共享 libosmpbf + osmpbf-outline。
依赖与 codegen：
  - 目标库：cmd-pkgs 预编译 protobuf/abseil/zlib（R18）
  - OHOS-native CI：直接用 cmd-pkgs 中的 aarch64 protoc
  - Linux x86_64 交叉主机：下载官方 linux-x86_64 protoc zip（避免跑 OHOS protoc）
"""
from __future__ import annotations

import glob
import os
import shutil
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import cmake_layout
from conan.tools.files import check_sha256, copy, get


class OsmPbfConan(ConanFile):
    name = "osm-pbf"
    version = "1.6.1"
    description = "Tools related to OSM PBF (Protocolbuffer Binary Format)"
    license = "LGPL-3.0-or-later"
    homepage = "https://wiki.openstreetmap.org/wiki/PBF_Format"
    url = ""
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

    def validate(self):
        # 本配方为 OHOS 交叉编译（需 OHOS SDK + cmd-pkgs），不支持原生 Linux 构建
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported; this recipe only builds for OHOS "
                "(requires OHOS SDK / ohos.toolchain.cmake). Use an OHOS host profile "
                "(e.g. -pr:h=ohos-aarch64-6.1)."
            )
        self._ohos_arch()  # reject unmapped / unsupported arch early

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        # R39: 官方 URL only；GitHub 镜像 fallback 由 CI 自动注入
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_arch(self) -> str:
        """Map Conan settings.arch → OHOS CMake OHOS_ARCH (ABI)."""
        arch = str(self.settings.arch)
        # Conan arch → NDK/OHOS ABI name used by ohos.toolchain.cmake
        mapping = {
            "armv8": "arm64-v8a",
            "armv8.3": "arm64-v8a",
            "aarch64": "arm64-v8a",
            "armv7": "armeabi-v7a",
            "armv7hf": "armeabi-v7a",
            "x86_64": "x86_64",
            "x86": "x86",
        }
        ohos_arch = mapping.get(arch)
        if not ohos_arch:
            raise ConanInvalidConfiguration(
                f"arch={arch} has no OHOS_ARCH mapping; supported: {', '.join(sorted(mapping))}"
            )
        # cmd-pkgs deps in conandata are currently aarch64-only
        if ohos_arch != "arm64-v8a":
            raise ConanInvalidConfiguration(
                f"arch={arch} (OHOS_ARCH={ohos_arch}) not supported yet: "
                "ohos_deps tarballs are aarch64-only; use arch=armv8"
            )
        return ohos_arch

    def _sdk_home(self) -> str:
        for key in ("OHOS_SDK_HOME", "OHOS_NDK_HOME"):
            val = os.environ.get(key, "")
            if val and os.path.isdir(val):
                return val
        for cand in (
            "/opt/ohos-sdk-6.1",
            "/data/service/hnp/ohos-sdk.org",
        ):
            if os.path.isdir(cand):
                if cand.endswith("ohos-sdk.org"):
                    globbed = sorted(glob.glob(os.path.join(cand, "*", "ohos", "native")))
                    if globbed:
                        # .../ohos/native → SDK root is parent of native? actually path is */ohos/native
                        return os.path.dirname(os.path.dirname(globbed[-1]))
                return cand
        raise ConanInvalidConfiguration(
            "OHOS SDK not found: set OHOS_SDK_HOME=/opt/ohos-sdk-6.1"
        )

    def _ohos_toolchain(self) -> str:
        sdk = self._sdk_home()
        candidates = [
            os.path.join(sdk, "native", "build", "cmake", "ohos.toolchain.cmake"),
            os.path.join(sdk, "build", "cmake", "ohos.toolchain.cmake"),
        ]
        candidates += sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake")
        )
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        raise ConanInvalidConfiguration("ohos.toolchain.cmake not found")

    def _cmake_bin(self) -> str:
        conf = self.conf.get("tools.cmake:cmake_program", default=None)
        if conf and os.path.isfile(conf):
            return conf
        sdk = self._sdk_home()
        cand = os.path.join(sdk, "native", "build-tools", "cmake", "bin", "cmake")
        if os.path.isfile(cand):
            return cand
        return shutil.which("cmake") or "cmake"

    def _llvm_bin_dir(self, sdk: str) -> str:
        """Locate the SDK's llvm/bin directory (host cross tools: clang, llvm-ar, ...)."""
        for cand in (
            os.path.join(sdk, "native", "llvm", "bin"),
            os.path.join(sdk, "llvm", "bin"),
        ):
            if os.path.isdir(cand):
                return cand
        # last resort: glob the multi-version install root
        globs = sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")
        )
        return globs[-1] if globs else ""

    def _find_tool(self, llvm_bin: str, name: str) -> str:
        if llvm_bin:
            cand = os.path.join(llvm_bin, name)
            if os.path.isfile(cand):
                return cand
        return ""

    def _curl(self, url, dest: str) -> None:
        """Download url (str or CI mirror list) to dest; try each URL until one succeeds.

        Use self.run() (not bare subprocess): OHOS CI puts curl under
        /data/service/hnp/bin which is only on PATH via Conan buildenv.
        """
        # CI mirror fallback may rewrite conandata url: str → list[str]
        urls = list(url) if isinstance(url, (list, tuple)) else [url]
        last_err = None
        for u in urls:
            try:
                if os.path.isfile(dest):
                    os.remove(dest)
                self.run(f'curl -fL --retry 3 -o "{dest}" "{u}"')
                if os.path.isfile(dest) and os.path.getsize(dest) > 0:
                    return
                last_err = RuntimeError(f"empty download: {dest}")
            except Exception as exc:
                last_err = exc
                self.output.warning(f"download failed ({u}): {exc}")
        raise ConanInvalidConfiguration(
            f"failed to download from any URL ({len(urls)} tried); last={last_err}"
        )

    def _shell_run(self, cmd: str) -> None:
        """Run via bash when available — OHOS /system/bin/sh (mksh) cannot exec ELF."""
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        if os.path.isfile(bash):
            escaped = cmd.replace("'", "'\"'\"'")
            self.run(f"{bash} -c '{escaped}'")
        else:
            self.run(cmd)

    def _deps_lib_path(self, deps_prefix: str) -> str:
        """Library search path for cmd-pkgs protoc (needs libc++_shared from SDK)."""
        libs = [os.path.join(deps_prefix, "lib")]
        try:
            sdk = self._sdk_home()
        except Exception:
            sdk = ""
        for cand in (
            os.path.join(sdk, "native", "llvm", "lib") if sdk else "",
            os.path.join(sdk, "llvm", "lib") if sdk else "",
            "/data/service/hnp/lib",
        ):
            if cand and os.path.isdir(cand):
                libs.append(cand)
        libs += sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
        )
        # de-dupe, preserve order
        seen = set()
        out = []
        for p in libs:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return ":".join(out)

    def _can_run(self, exe: str, lib_path: str | None = None) -> bool:
        if not exe or not os.path.isfile(exe):
            return False
        try:
            prefix = ""
            if lib_path:
                prefix = (
                    f'export LD_LIBRARY_PATH="{lib_path}'
                    f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; '
                )
            self._shell_run(f'{prefix}"{exe}" --version')
            return True
        except Exception:
            return False

    def _resolve_deps_protoc(self, deps_prefix: str) -> str | None:
        """Locate cmd-pkgs protoc; create bin/protoc if only versioned binary exists.

        protobuf-*-ohos-aarch64.tar.gz ships bin/protoc-34.1.0 without a `protoc` symlink.
        """
        bindir = os.path.join(deps_prefix, "bin")
        if not os.path.isdir(bindir):
            return None
        canonical = os.path.join(bindir, "protoc")
        if os.path.isfile(canonical):
            return canonical
        candidates = sorted(
            p
            for p in glob.glob(os.path.join(bindir, "protoc-*"))
            if os.path.isfile(p) and not os.path.basename(p).startswith("protoc-gen-")
        )
        if not candidates:
            return None
        chosen = candidates[-1]
        try:
            os.symlink(os.path.basename(chosen), canonical)
        except OSError:
            shutil.copy2(chosen, canonical)
            os.chmod(canonical, 0o755)
        self.output.info(f"created {canonical} -> {os.path.basename(chosen)}")
        return canonical

    def _ensure_host_protoc(self) -> str:
        """Download linux-x86_64 protoc for cross hosts that cannot run OHOS protoc."""
        tools_dir = os.path.join(self.build_folder, "host-tools")
        protoc = os.path.join(tools_dir, "bin", "protoc")
        if self._can_run(protoc):
            return protoc
        os.makedirs(tools_dir, exist_ok=True)
        meta = self.conan_data["host_protoc"]
        expected = meta.get("sha256") or ""
        if not expected:
            raise ConanInvalidConfiguration(
                "host_protoc.sha256 missing in conandata.yml — refuse to run unverified protoc"
            )
        zpath = os.path.join(tools_dir, "protoc-host.zip")
        if os.path.isfile(zpath):
            os.remove(zpath)
        self._curl(meta["url"], zpath)
        check_sha256(self, zpath, expected)
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(tools_dir)
        os.chmod(protoc, 0o755)
        if not self._can_run(protoc):
            raise ConanInvalidConfiguration(
                f"host protoc not runnable on this machine: {protoc} "
                "(linux-x86_64 zip is for Linux cross hosts; on OHOS-native use cmd-pkgs protoc)"
            )
        self.output.info(f"host protoc ready (sha256 verified): {protoc}")
        return protoc

    def _ensure_ohos_deps(self) -> str:
        """Fetch cmd-pkgs aarch64 deps into a local prefix (R18); verify sha256."""
        env_prefix = os.environ.get("OHOS_DEPS_PREFIX", "")
        if env_prefix and os.path.isfile(os.path.join(env_prefix, "lib", "cmake", "protobuf", "protobuf-config.cmake")):
            return env_prefix

        prefix = os.path.join(self.build_folder, "ohos-deps")
        marker = os.path.join(prefix, "lib", "cmake", "protobuf", "protobuf-config.cmake")
        if os.path.isfile(marker):
            return prefix

        os.makedirs(prefix, exist_ok=True)
        dl = os.path.join(self.build_folder, "deps-dl")
        os.makedirs(dl, exist_ok=True)

        for dep in self.conan_data["ohos_deps"]:
            name, ver = dep["name"], dep["version"]
            expected = dep.get("sha256") or ""
            if not expected:
                raise ConanInvalidConfiguration(
                    f"ohos_deps[{name}/{ver}].sha256 missing — refuse unverified cmd-pkgs tarball"
                )
            tarball = f"{name}-{ver}-ohos-aarch64.tar.gz"
            url = dep.get("url") or (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
                f"releases/download/pkgs/{tarball}"
            )
            dest = os.path.join(dl, tarball)
            self.output.info(f"fetch {name}/{ver}: {url}")
            if os.path.isfile(dest):
                os.remove(dest)
            self._curl(url, dest)
            check_sha256(self, dest, expected)
            extract_dir = os.path.join(dl, f"{name}-{ver}")
            os.makedirs(extract_dir, exist_ok=True)
            self.run(f'tar xzf "{dest}" -C "{extract_dir}"')
            # merge lib/include/bin/share into prefix
            roots = [extract_dir]
            roots += [
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

        if not os.path.isfile(marker):
            raise ConanInvalidConfiguration(
                f"protobuf cmake config missing after deps install: {marker}"
            )
        return prefix

    def _patch_protoc_for_host(self, deps_prefix: str, host_protoc: str) -> None:
        """Replace aarch64 protoc in deps prefix with host binary (codegen only)."""
        bindir = os.path.join(deps_prefix, "bin")
        if not os.path.isdir(bindir):
            return
        for name in os.listdir(bindir):
            if name == "protoc" or name.startswith("protoc-"):
                # keep plugins; only replace main protoc binaries that are ELF aarch64
                path = os.path.join(bindir, name)
                if not os.path.isfile(path) or os.path.islink(path):
                    continue
                if "protoc-gen-" in name:
                    continue
                shutil.copy2(host_protoc, path)
                os.chmod(path, 0o755)
        # ensure canonical name
        shutil.copy2(host_protoc, os.path.join(bindir, "protoc"))
        os.chmod(os.path.join(bindir, "protoc"), 0o755)

    def build(self):
        # OHOS-native (host==build): cmd-pkgs aarch64 protoc.
        # Linux x86_64 cross host: download host zip (OHOS protoc cannot run under qemu).
        deps_prefix = self._ensure_ohos_deps()
        lib_path = self._deps_lib_path(deps_prefix)
        deps_protoc = self._resolve_deps_protoc(deps_prefix)
        if not cross_building(self):
            if not deps_protoc:
                raise ConanInvalidConfiguration(
                    f"OHOS-native build: no protoc in {deps_prefix}/bin "
                    "(expected protoc or protoc-<ver> from cmd-pkgs protobuf)"
                )
            if not self._can_run(deps_protoc, lib_path=lib_path):
                raise ConanInvalidConfiguration(
                    f"OHOS-native build requires runnable cmd-pkgs protoc: {deps_protoc} "
                    f"(tried LD_LIBRARY_PATH={lib_path})"
                )
            host_protoc = deps_protoc
            self.output.info(f"using native/deps protoc: {host_protoc}")
        elif deps_protoc and self._can_run(deps_protoc, lib_path=lib_path):
            host_protoc = deps_protoc
            self.output.info(f"using native/deps protoc: {host_protoc}")
        else:
            host_protoc = self._ensure_host_protoc()
            self._patch_protoc_for_host(deps_prefix, host_protoc)
            self.output.info(f"using host protoc for codegen: {host_protoc}")

        # Ensure codegen (and any RUNPATHed deps tools) find libc++_shared / protobuf libs
        prev_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = (
            f"{lib_path}:{prev_ld}" if prev_ld else lib_path
        )

        toolchain = self._ohos_toolchain()
        cmake = self._cmake_bin()
        sdk = self._sdk_home()
        sysroot = os.path.join(sdk, "native", "sysroot")
        bdir = os.path.join(self.build_folder, "build-ohos")

        # OHOS toolchain leaves CMAKE_AR/RANLIB unresolved on some SDK layouts
        # (llvm-ar not on PATH), so static archiving fails with "no such file or
        # directory". Resolve them explicitly from the SDK's llvm/bin.
        llvm_bin = self._llvm_bin_dir(sdk)
        ar_tool = self._find_tool(llvm_bin, "llvm-ar") or shutil.which("llvm-ar") or shutil.which("ar")
        ranlib_tool = self._find_tool(llvm_bin, "llvm-ranlib") or shutil.which("llvm-ranlib") or shutil.which("ranlib")
        strip_tool = self._find_tool(llvm_bin, "llvm-strip") or shutil.which("llvm-strip")

        defs = [
            f'-DCMAKE_TOOLCHAIN_FILE="{toolchain}"',
            f"-DOHOS_ARCH={self._ohos_arch()}",
            f"-DCMAKE_BUILD_TYPE={self.settings.build_type}",
            f'-DCMAKE_PREFIX_PATH="{deps_prefix}"',
            "-DCMAKE_CXX_STANDARD=17",
            "-Dprotobuf_MODULE_COMPATIBLE=ON",
            f'-DProtobuf_PROTOC_EXECUTABLE="{host_protoc}"',
            f'-DCMAKE_FIND_ROOT_PATH="{deps_prefix};{sysroot}"',
            "-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER",
            "-DCMAKE_INSTALL_LIBDIR=lib",
        ]
        if ar_tool:
            defs.append(f'-DCMAKE_AR="{ar_tool}"')
        if ranlib_tool:
            defs.append(f'-DCMAKE_RANLIB="{ranlib_tool}"')
        if strip_tool:
            defs.append(f'-DCMAKE_STRIP="{strip_tool}"')
        self.run(f'{cmake} -S "{self.source_folder}" -B "{bdir}" {" ".join(defs)}')
        self.run(f'{cmake} --build "{bdir}" -j1')

    def package(self):
        cmake = self._cmake_bin()
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run(f'{cmake} --install "{bdir}" --prefix "{self.package_folder}"')
        # Homebrew installs sample.pbf into share
        sample = os.path.join(self.source_folder, "resources", "sample.pbf")
        if os.path.isfile(sample):
            share = os.path.join(self.package_folder, "share", "osm-pbf")
            os.makedirs(share, exist_ok=True)
            shutil.copy2(sample, os.path.join(share, "sample.pbf"))
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        for signer_dir in ("/data/service/hnp/bin", os.path.join(self._sdk_home(), "native", "llvm", "bin")):
            objcopy = os.path.join(signer_dir, "llvm-objcopy")
            signer = os.path.join(signer_dir, "binary-sign-tool")
            if os.path.isfile(signer):
                break
        else:
            self.output.warning("binary-sign-tool not found; skip ELF signing")
            return
        for so in sos:
            if os.path.islink(so):
                continue
            if os.path.isfile(objcopy):
                self.run(f'{objcopy} --remove-section .codesign "{so}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["osmpbf"]
        self.cpp_info.includedirs = ["include"]
        # R38: osmpbf-outline CLI — bindirs required so L0k treats package as tool
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "osmpbf")
        self.cpp_info.set_property("cmake_target_name", "osmpbf::osmpbf")
        self.cpp_info.set_property("pkg_config_name", "osmpbf")
        # R32: Linux-like platforms; validate() already restricts to OHOS
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
