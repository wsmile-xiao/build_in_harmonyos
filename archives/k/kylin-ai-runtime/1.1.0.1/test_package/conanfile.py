#!/usr/bin/env python3
"""Conan test_package — kylin-ai-runtime 1.1.0.1 L1 运行探针（R51）。

kylin-ai-runtime 是 application 包（无对外头/库），L1 测试即“能起来”：
在包安装目录下以真实运行期环境拉起 `bin/kylin-ai-runtime` 守护进程 5s，
存活或干净退出（rc 0/1）判 PASS，动态链接失败（rc 127/信号）判 FAIL。

运行期环境要点（OHOS）：
  - 主二进制 DT_NEEDED 覆盖 9 个已发布依赖 + 2 个 vendor 客户端库，
    且 application 包不向消费方传播 requires → 测试包内显式声明运行期
    依赖，使 conanrun 的 LD_LIBRARY_PATH 覆盖完整闭包。
  - libc++_shared.so / libxml2.so.16 不在任何包的 cpp_info.libdirs 内，
    额外把 OHOS SDK 运行库目录并入 LD_LIBRARY_PATH（同配方 generate()
    的 E266 处理）。
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.env import Environment


class KylinAiRuntimeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 运行期依赖闭包（版本与配方 requires 一致；application 包不传播）
        for ref in (
            "zlib/1.3.2",
            "openssl/3.5.8.1",
            "spdlog/1.17.0",
            "fmt/12.2.0",
            "jsoncpp/1.9.8.1",
            "curl/8.22.0",
            "icu/76.1",
            "glib/2.88.0",
            "pulseaudio/17.0.1",
            "libsodium/1.0.20",
            "grpc/1.84.0",
            "protobuf/33.6",
            "abseil-cpp/20260107.1",
            "c-ares/1.34.6",
            "re2/2024-04-01",
            "pcre2/10.45",
            "libsndfile/1.2.2",
            "nlohmann-json/3.11.2",
            "libkylin-ai-system-private/1.2.0.0",
            "kysdk-ai-common/1.1.0.1",
        ):
            self.requires(ref, transitive_libs=True)

    def test(self):
        pkg = self.dependencies["kylin-ai-runtime"].package_folder

        lib_dirs = []
        for dep in self.dependencies.values():
            folder = dep.package_folder
            if not folder:
                continue
            # cpp_info.libdirs 可能是相对路径（相对 package_folder），
            # 直接 isdir 会按 CWD 过滤而静默丢弃
            for d in dep.cpp_info.libdirs:
                lib_dirs.append(d if os.path.isabs(d)
                                else os.path.join(folder, d))
            for root, _d, files in os.walk(folder):
                if any(f.endswith(".so") or ".so." in f for f in files):
                    lib_dirs.append(root)
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot/usr/lib/aarch64-linux-ohos",
        ):
            lib_dirs.extend(glob.glob(pattern))

        seen, ordered = set(), []
        for d in lib_dirs:
            d = os.path.normpath(d)
            if d not in seen and os.path.isdir(d):
                seen.add(d)
                ordered.append(d)

        # OHOS 强制加载已签名 ELF：部分已发布依赖（如 pulseaudio/17.0.1）
        # 的 .so 缺少 .codesign 段，直接加载会 rc=127。此处把缺失签名的
        # 依赖库复制到临时目录自签名，并前置到 LD_LIBRARY_PATH。
        signed_dir = self._sign_unsigned_libs(ordered)
        if signed_dir:
            ordered.insert(0, signed_dir)

        env = Environment()
        env.define("LD_LIBRARY_PATH", ":".join(ordered))
        env.vars(self).save_script("runtime_env")

        self.run(
            f'python3 "{os.path.join(os.path.dirname(__file__), "test_kylin_ai_runtime.py")}"'
            f' "{pkg}"',
            env=["conanrun", "runtime_env"],
        )

    def _sign_unsigned_libs(self, lib_dirs):
        """签名所有缺 `.codesign` 段的依赖 `.so*`（含符号链接指向的真实文件），
        返回含已签名副本的临时目录；无缺失或工具不可用时返回 None。"""
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            return None
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        # 写到包源树之外（HOME 缓存），避免污染配方目录
        out = os.path.join(os.path.expanduser("~"), ".cache",
                           "kylin-ai-runtime-test", "signed_libs")
        # 每轮清空缓存：按文件名复用会残留旧版本依赖库的签名副本（依赖升级后
        # os.path.exists 命中即跳过重签，而该目录又被前置到 LD_LIBRARY_PATH，
        # 导致测试跑在过期库闭包上，产生假 PASS/FAIL）
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out, exist_ok=True)
        signed_any = False
        for d in lib_dirs:
            for path in glob.glob(os.path.join(d, "*.so*")):
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, "rb") as h:
                        if h.read(4) != b"\x7fELF":
                            continue
                        if b".codesign" in h.read():
                            continue
                except OSError:
                    continue
                dst = os.path.join(out, os.path.basename(path))
                shutil.copy2(path, dst)
                if objcopy and os.path.isfile(objcopy):
                    self.run(f"{shlex.quote(objcopy)} --remove-section .codesign "
                             f"{shlex.quote(dst)} 2>/dev/null || true")
                self.run(shlex.join([signer, "sign", "-inFile", dst,
                                     "-outFile", dst, "-selfSign", "1"]))
                os.chmod(dst, 0o755)
                signed_any = True
        return out if signed_any else None
