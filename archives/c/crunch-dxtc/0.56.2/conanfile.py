#!/usr/bin/env python3
"""Conan recipe for crunch-dxtc 0.56.2 — DXTc texture library + CLI tool.

Upstream: DaemonEngine/crunch (maintained CRN fork of BinomialLLC/crunch),
tag unvanquished/0.56.2. This is the same source Debian/Ubuntu package as
crunch-dxtc 0.56.2-1 (Debian pkg-games team): the Debian source package
tracks DaemonEngine/crunch's unvanquished/* tags.

Build: CMake. Prefers OHOS NDK ohos.toolchain.cmake + bare cmake when the
SDK file exists (expat/zstd/dlisio pattern); otherwise falls back to Conan
CMakeToolchain with Linux platform override + existence-checked compiler
(zxc/julius pattern) so preflight without SDK still configures. Produces
libcrn (static by default) + the `crunch` command-line tool. Upstream ships
a Python test harness (test/test.py, driven by test/checksums.tsv) which is
executed in build().
"""

import json
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, get


class CrunchDxtcConan(ConanFile):
    name = "crunch-dxtc"
    version = "0.56.2"
    description = "Advanced DXTc texture compression and transcoding library and command-line tool"
    license = "Zlib"
    homepage = "https://github.com/DaemonEngine/crunch"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies: stb_image/miniz/lzma are vendored.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_writable_tmp(self):
        # HMBS 真机 /tmp 只读（preflight.sh mktemp EROFS + 平台诊断
        # readonly_tmp）：clang/CMake 临时文件默认走 /tmp 会失败。
        # 复用 HMBS 注入的可写目录，透传给所有子进程。最小适配，
        # 仅替换临时文件根目录，不删测试。
        cand = []
        hmbs_tmp = os.environ.get("HMBS_TMPDIR", "")
        if hmbs_tmp:
            cand.append(hmbs_tmp)
        caps = os.environ.get("HMBS_PLATFORM_CAPABILITIES", "")
        if caps:
            try:
                cand.append(json.loads(caps).get("tmpdir", ""))
            except Exception:
                pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key, "")
            if val:
                cand.append(val)
        fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fallback:
            cand.append(fallback)
        for d in cand:
            if not d:
                continue
            try:
                os.makedirs(d, exist_ok=True)
                if os.path.isdir(d):
                    for key in ("TMPDIR", "TMP", "TEMP"):
                        os.environ[key] = d
                    return d
            except Exception:
                continue
        return os.environ.get("TMPDIR", "")

    def _existing_file(self, p):
        return bool(p) and os.path.isfile(p) and os.access(p, os.X_OK)

    def _find_sdk_toolchain(self):
        # OHOS NDK ohos.toolchain.cmake 自发现，找不到返回 None（不抛异常，
        # 由调用方回退到 CMakeToolchain）。不硬编码 SDK 版本目录。
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        for cand in list(ut or []):
            if cand and os.path.isfile(cand):
                return cand
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        if ndk:
            cand = os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")
            if os.path.isfile(cand):
                return cand
            cand2 = os.path.join(ndk, "ohos", "native", "build", "cmake", "ohos.toolchain.cmake")
            if os.path.isfile(cand2):
                return cand2
        import glob
        patterns = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/opt/ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake",
        ]
        for pat in patterns:
            try:
                hits = sorted(glob.glob(pat))
            except Exception:
                continue
            if hits:
                return hits[-1]
        return None

    def _ohos_llvm_bin(self, toolchain):
        # E012: ohos.toolchain.cmake 以 INTERNAL/FORCE 覆写 CMAKE_AR 为 bare
        # name ("llvm-ar")，但 llvm-ar 不在默认 PATH 中 → 静态库归档报
        # "Error running link command: no such file or directory"。
        # 从 toolchain 路径推导 <ndk>/llvm/bin 绝对路径（googletest/draco 同法）。
        import glob
        if toolchain:
            ndk_root = os.path.dirname(os.path.dirname(os.path.dirname(toolchain)))
            llvm_bin = os.path.join(ndk_root, "llvm", "bin")
            if os.path.isdir(llvm_bin):
                return llvm_bin
        for base in ("/data/service/hnp/ohos-sdk.org",):
            for pat in (os.path.join(base, "*", "ohos", "native", "llvm", "bin"),):
                try:
                    matches = sorted(glob.glob(pat))
                except Exception:
                    continue
                if matches:
                    return matches[-1]
        return None

    def _find_compiler(self, kind):
        # 存在性校验解析 C/CXX 编译器：profile 配置优先，若路径不存在则
        # 回退到 PATH/SDK 中的可用 clang。避免陈旧绝对路径导致
        # CMAKE_CXX_COMPILER identification unknown。
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        prof = comp.get(kind, "")
        if self._existing_file(prof):
            return prof
        if prof and os.path.isfile(prof):
            return prof
        for cand in (shutil.which("clang++") if kind == "cpp" else shutil.which("clang"),
                     shutil.which("clang"), shutil.which("clang++"),
                     shutil.which("cc"), shutil.which("c++")):
            if cand and os.path.isfile(cand):
                return cand
        import glob
        for pat in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang++",
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang",
                    "/data/service/hnp/*/llvm/bin/clang++"):
            try:
                hits = sorted(glob.glob(pat))
            except Exception:
                continue
            for h in hits:
                if os.path.isfile(h):
                    if kind == "cpp" and h.endswith("clang"):
                        continue
                    return h
        return prof or ("clang++" if kind == "cpp" else "clang")

    def generate(self):
        self._ensure_writable_tmp()
        # 主路仍生成 Conan 工具链，保证无 SDK 的预检/CI 也能 configure。
        # 有 SDK 时 build() 走 ohos.toolchain 裸 cmake；无 SDK 时走本工具链。
        tc = CMakeToolchain(self)
        # E092/ML-0035: vanilla cmake 不认 HarmonyOS，纯用户态压缩库按
        # Linux 平台处理（zxc/julius/jwt-cpp 先例）。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 存在性校验后写入编译器，避免 conan_toolchain 携带缺失绝对路径。
        cc = self._find_compiler("c")
        cxx = self._find_compiler("cpp")
        if cc:
            tc.cache_variables["CMAKE_C_COMPILER"] = cc
            self.output.info("generate: CMAKE_C_COMPILER=%s" % cc)
        if cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
            self.output.info("generate: CMAKE_CXX_COMPILER=%s" % cxx)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_CRUNCH"] = True
        tc.variables["BUILD_EXAMPLES"] = True
        tc.variables["USE_FAST_MATH"] = False
        tc.variables["USE_LTO"] = False
        if not self.options.shared:
            tc.variables["BUILD_STATIC_LIBCRN"] = True
            tc.variables["INSTALL_STATIC_LIBCRN"] = True
        tc.generate()
        # 经验1适配：仅设 cache_variables 不够——conan_toolchain.cmake 内仍
        # 残留 profile 的陈旧绝对路径（/data/service/hnp/bin/clang++ 在预检
        # 沙箱不存在），其 set() 会覆盖命令行 -D，导致本轮日志出现
        # “generate 已是 harmonybrew 但 cmake 仍用 /data/...”双重覆盖。
        # 此处对生成文件做同值替换补丁，保留测试口径。
        try:
            comp0 = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            stale_c = comp0.get("c", "")
            stale_cxx = comp0.get("cpp", "")
            tc_path = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            if os.path.isfile(tc_path):
                with open(tc_path, "r", encoding="utf-8", errors="replace") as f:
                    txt = f.read()
                orig = txt
                if stale_c and cc and stale_c != cc and stale_c in txt:
                    txt = txt.replace(stale_c, cc)
                if stale_cxx and cxx and stale_cxx != cxx and stale_cxx in txt:
                    txt = txt.replace(stale_cxx, cxx)
                if txt != orig:
                    with open(tc_path, "w", encoding="utf-8") as f:
                        f.write(txt)
                    self.output.info("patched conan_toolchain.cmake stale compiler -> %s / %s" % (cc, cxx))
        except Exception as e:
            self.output.info("patch conan_toolchain.cmake skipped: %s" % e)

    def _cmake_exe(self):
        for cand in (os.environ.get("HMBS_CMAKE", ""), shutil.which("cmake")):
            if cand and os.path.isfile(cand):
                return cand
        return "cmake"

    def _sign_file(self, path):
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            return
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass
        self.run('%s --remove-section .codesign "%s" 2>/dev/null || true' % (objcopy, path))
        self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, path, path))

    def _find_python(self):
        for cand in (os.environ.get("HMBS_PYTHON3", ""), sys.executable, "python3"):
            if cand and shutil.which(cand):
                return cand
        return None

    def _run_upstream_tests(self, bdir):
        """Run upstream test/test.py and emit the HMBS evidence marker.

        test.py converts the bundled fixtures (png/tga/bmp/jpg/crn/dds/ktx)
        through the just-built `crunch` binary plus example1/2/3 (~91 process
        invocations), then verifies every output against test/checksums.tsv
        ("files" check) and cross-compares repeated conversions ("clones"
        check). Any failing command aborts with a non-zero exit code.
        """
        python = self._find_python()
        if python is None:
            raise RuntimeError("no python3 available to run upstream test/test.py")
        env = os.environ.copy()
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val:
                env[key] = val
        env["CRUNCH_BUILD_DIR"] = bdir
        cmd = [python, "test/test.py"]
        self.output.info("Running upstream tests: %s test/test.py (CRUNCH_BUILD_DIR=%s)" % (python, bdir))
        proc = subprocess.run(
            cmd,
            cwd=self.source_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1200,
            env=env,
        )
        out = proc.stdout or ""
        self.output.info(out[-3000:])

        in_table = False
        passed = 0
        failed = 0
        for line in out.splitlines():
            s = line.strip()
            if s in ("Clones verification results:", "Files verification results:"):
                in_table = True
                continue
            if in_table:
                if s.startswith("Yes"):
                    passed += 1
                elif s.startswith("No"):
                    failed += 1
                elif s == "" or s.startswith("---"):
                    continue
                else:
                    in_table = False
        executed = passed + failed
        discovered = executed

        artifacts_ok = False
        probe_dir = os.path.join(bdir, "test", "png-to-all")
        try:
            if os.path.isdir(probe_dir):
                names = os.listdir(probe_dir)
                sizes = [os.path.getsize(os.path.join(probe_dir, n)) for n in names]
                artifacts_ok = len(names) > 0 and all(sz > 0 for sz in sizes)
        except OSError:
            artifacts_ok = False

        if proc.returncode == 0 and failed == 0 and executed > 0 and artifacts_ok:
            status = "passed"
        else:
            status = "failed"
        upstream = {
            "status": status,
            "framework": "custom",
            "command": "%s test/test.py" % python,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream)
        # 双通道输出：conan 通道 + 标准输出直写（hmbs 证据采集只认 stdout 原行，
        # 仅 self.output.info 会带包名前缀而漏检；cld2 经验1同法）。
        self.output.info(marker)
        print(marker, flush=True)
        # 持久化实测结果供 test_package 重发（无 BOM、LF）。
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream_test_result.json"), "w", encoding="utf-8", newline="\n") as f:
                json.dump(upstream, f)
            try:
                os.makedirs(self.package_folder, exist_ok=True)
                with open(os.path.join(self.package_folder, "hmbs_upstream_test_result.json"), "w", encoding="utf-8", newline="\n") as f:
                    json.dump(upstream, f)
            except Exception as e2:
                self.output.info("persist upstream result to package_folder skipped: %s" % e2)
        except Exception as e:
            self.output.info("persist upstream result skipped: %s" % e)
        if status != "passed":
            raise RuntimeError(
                "upstream tests failed (rc=%s, passed=%s, failed=%s, artifacts_ok=%s)"
                % (proc.returncode, passed, failed, artifacts_ok)
            )

    def _resolve_bdir(self, sdk_bdir):
        # SDK 裸构建目录存在则用它，否则用 CMake helper 的实际二进制目录。
        if sdk_bdir and os.path.isfile(os.path.join(sdk_bdir, "crunch")):
            return sdk_bdir
        cands = [
            os.path.join(self.build_folder, "build", "Release"),
            self.build_folder,
        ]
        for d in cands:
            if os.path.isfile(os.path.join(d, "crunch")):
                return d
        return sdk_bdir if sdk_bdir else self.build_folder

    def build(self):
        from conan.tools.files import apply_conandata_patches
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        toolchain = self._find_sdk_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        used_sdk = False
        if toolchain:
            self.output.info("Using OHOS toolchain: %s" % toolchain)
            cmake = self._cmake_exe()
            src = self.source_folder
            defs = [
                '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
                "-DOHOS_ARCH=arm64-v8a",
                "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
                '-DCMAKE_INSTALL_PREFIX="%s"' % self.package_folder,
                "-DCMAKE_INSTALL_LIBDIR=lib",
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
                "-DBUILD_SHARED_LIBS=%s" % ("ON" if self.options.shared else "OFF"),
                "-DBUILD_CRUNCH=ON",
                "-DBUILD_EXAMPLES=ON",
                "-DUSE_FAST_MATH=OFF",
                "-DUSE_LTO=OFF",
            ]
            if not self.options.shared:
                defs += ["-DBUILD_STATIC_LIBCRN=ON", "-DINSTALL_STATIC_LIBCRN=ON"]
            # E012: ohos.toolchain.cmake 把 CMAKE_AR 覆写为 bare name
            # "llvm-ar"，CI worker PATH 中无该工具 → libcrn.a 归档报
            # "Error running link command: no such file or directory"
            # （CI #44052，box2d/googletest/draco 先例）。用 SDK llvm/bin
            # 下绝对路径覆盖，并覆写 CREATE_STATIC_LIBRARY 规则。
            llvm_bin = self._ohos_llvm_bin(toolchain)
            cands = []
            if llvm_bin:
                cands.append(os.path.join(llvm_bin, "llvm-ar"))
            for extra in ("/data/service/hnp/bin/llvm-ar",
                          shutil.which("llvm-ar") or "",
                          shutil.which("ar") or ""):
                if extra:
                    cands.append(extra)
            ar = next((p for p in cands if p and os.path.isfile(p)), "")
            if ar:
                ranlib = ""
                rcands = []
                if llvm_bin:
                    rcands.append(os.path.join(llvm_bin, "llvm-ranlib"))
                rcands += ["/data/service/hnp/bin/llvm-ranlib",
                           shutil.which("llvm-ranlib") or "",
                           shutil.which("ranlib") or ""]
                ranlib = next((p for p in rcands if p and os.path.isfile(p)), "")
                self.output.info("Using archiver: %s%s" % (ar, (" ranlib=%s" % ranlib) if ranlib else " (no ranlib, CREATE_STATIC_LIBRARY override only)"))
                defs.append('-DCMAKE_AR:FILEPATH="%s"' % ar)
                if ranlib:
                    defs.append('-DCMAKE_RANLIB:FILEPATH="%s"' % ranlib)
                defs.append('-DCMAKE_C_CREATE_STATIC_LIBRARY="%s rcs <TARGET> <OBJECTS>"' % ar)
                defs.append('-DCMAKE_CXX_CREATE_STATIC_LIBRARY="%s rcs <TARGET> <OBJECTS>"' % ar)
            else:
                self.output.info("llvm-ar/ar not found, keep toolchain default CMAKE_AR")
            self.run('%s -B "%s" -S "%s" %s' % (cmake, bdir, src, " ".join(defs)))
            self.run('%s --build "%s"' % (cmake, bdir))
            used_sdk = True
        else:
            self.output.info("ohos.toolchain.cmake not found, fallback to conan_toolchain (Linux override)")
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        real_bdir = self._resolve_bdir(bdir if used_sdk else None)
        # 若回退路径的二进制不在 build-ohos，则以实际目录为准。
        if not used_sdk:
            for d in (os.path.join(self.build_folder, "build", "Release"), self.build_folder):
                if os.path.isfile(os.path.join(d, "crunch")):
                    real_bdir = d
                    break
        for name in ("crunch", "example1", "example2", "example3"):
            p = os.path.join(real_bdir, name)
            if os.path.isfile(p):
                self._sign_file(p)
        self._run_upstream_tests(real_bdir)

    def package(self):
        copy(self, "license.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        for header in ("crnlib.h", "crn_decomp.h", "crn_defs.h", "dds_defs.h"):
            copy(self, header, src=os.path.join(self.source_folder, "inc"), dst=os.path.join(self.package_folder, "include"))
        bdir = os.path.join(self.build_folder, "build-ohos")
        if os.path.isfile(os.path.join(bdir, "crunch")) or os.path.isfile(os.path.join(bdir, "CMakeCache.txt")):
            cmake = self._cmake_exe()
            self.run('%s --install "%s" --prefix "%s"' % (cmake, bdir, self.package_folder))
        else:
            cmake = CMake(self)
            cmake.install()
        # 将 build() 持久化的上游实测结果带入包内，供 test_package 重发。
        try:
            src_json = os.path.join(self.build_folder, "hmbs_upstream_test_result.json")
            dst_json = os.path.join(self.package_folder, "hmbs_upstream_test_result.json")
            if os.path.isfile(src_json) and not os.path.isfile(dst_json):
                shutil.copyfile(src_json, dst_json)
        except Exception as e:
            self.output.info("copy upstream result json skipped: %s" % e)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.info("binary-sign-tool missing, skip package signing")
            return
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('%s --remove-section .codesign "%s" 2>/dev/null || true' % (objcopy, f))
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, f, f))

    def package_info(self):
        self.cpp_info.libs = ["crn"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
