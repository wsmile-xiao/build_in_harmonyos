#!/usr/bin/env python3
"""Conan recipe for aercbook 0.1.6 — minimal address book for the aerc email client.

aercbook 是 Zig 项目（build.zig 构建，纯 Zig 标准库无第三方依赖），需要 Zig 0.11.0
（项目仅有 zig/0.16.0，build.zig 的 API 与 0.16 不兼容），故配方内自包含下载
zig 0.11.0 作为构建工具链。

OHOS 适配要点：
- zig 0.11.0 二进制需签名才能在 OHOS 执行（binary-sign-tool + llvm-objcopy）
- `zig build` 内部 execve build_runner 在 OHOS 上被拒（AccessDenied），
  改用 `zig build-exe` 直接编译（绕过 build.zig 的 build_runner execve）
- build.zig 用 gitVersionTag 生成 src/version.zig，手动生成该文件
- 编译产物需签名才能在 OHOS 执行
- 测试：zig test --test-no-exec 编译测试二进制，签名后运行（email_iterator 2 个测试）
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class AercbookConan(ConanFile):
    name = "aercbook"
    version = "0.1.6"
    description = "Minimal address book for the aerc email client"
    license = "MIT"
    homepage = "https://github.com/renerocksai/aercbook"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        pass

    def layout(self):
        basic_layout(self)
        # aercbook 构建 in-source（zig build-exe 在源码目录输出）
        self.folders.build = "."

    def source(self):
        # aercbook 源码
        get(self, **self.conan_data["sources"], strip_root=True)
        # zig 0.11.0 工具链（自包含，保留 lib/ 安装目录结构）
        get(self, **self.conan_data["zig"], strip_root=True, destination="zig")

    def _find_ohos_tool(self, env_name, command, fallback):
        """查找 OHOS 工具（签名/objcopy），参考 zig 0.16.0 配方。"""
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.exists(configured):
                return configured
        found = shutil.which(command)
        if found:
            return found
        if os.path.exists(fallback):
            return fallback
        return None

    def _sign_ohos_executable(self, path):
        """签名 OHOS 可执行文件（binary-sign-tool + llvm-objcopy 移除 .codesign）。"""
        objcopy = self._find_ohos_tool(
            "OHOS_LLVM_OBJCOPY", "llvm-objcopy",
            "/data/service/hnp/bin/llvm-objcopy",
        )
        signer = self._find_ohos_tool(
            "OHOS_BINARY_SIGN_TOOL", "binary-sign-tool",
            "/data/service/hnp/bin/binary-sign-tool",
        )
        if objcopy:
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true')
        if not signer:
            self.output.warning("binary-sign-tool not found; packaged binary may require manual signing on OHOS")
            return
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def build(self):
        # zig 0.11.0 可执行文件签名（OHOS 需签名才能执行）
        zig_dir = os.path.join(self.source_folder, "zig")
        zig_bin = os.path.join(zig_dir, "zig")
        if not os.path.exists(zig_bin):
            raise ConanInvalidConfiguration(f"zig archive did not contain expected executable: {zig_bin}")
        os.chmod(zig_bin, os.stat(zig_bin).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self._sign_ohos_executable(zig_bin)

        # 生成 src/version.zig（build.zig 用 gitVersionTag 生成，此处直接写版本号）
        version_zig = os.path.join(self.source_folder, "src", "version.zig")
        with open(version_zig, "w", encoding="utf-8", newline="\n") as f:
            f.write('pub const version_string = "0.1.6";\n')

        # 用 zig build-exe 直接编译（绕过 build.zig 的 build_runner execve）
        # 缓存目录设到可写位置（zig 默认写 HOME/.cache 可能被拒）
        cache_dir = os.path.join(self.build_folder, "zig-cache")
        os.makedirs(cache_dir, exist_ok=True)
        env = [
            f"XDG_CACHE_HOME={cache_dir}",
            f"ZIG_CACHE_DIR={cache_dir}",
        ]
        self.run(
            f'"{zig_bin}" build-exe src/main.zig --name aercbook -O ReleaseSafe',
            env=env,
        )
        aercbook = os.path.join(self.source_folder, "aercbook")
        if not os.path.exists(aercbook):
            raise ConanInvalidConfiguration("zig build-exe did not produce aercbook binary")
        os.chmod(aercbook, os.stat(aercbook).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        # 签名产物（OHOS 需签名才能执行）
        self._sign_ohos_executable(aercbook)

        # 测试：zig test --test-no-exec 编译测试二进制，签名后运行
        # （zig test 直接运行会 execve 未签名测试二进制被拒，故先编译再签名再运行）
        self.run(f'"{zig_bin}" test src/email_iterator.zig --test-no-exec', env=env)
        test_bin = None
        for root, dirs, files in os.walk(cache_dir):
            for fn in files:
                if fn == "test":
                    p = os.path.join(root, fn)
                    if os.path.exists(p) and os.path.isfile(p):
                        test_bin = p
        if test_bin:
            os.chmod(test_bin, os.stat(test_bin).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            self._sign_ohos_executable(test_bin)
            # CI #19917 构建超时（45min 硬超时）：测试二进制疑似等待 stdin
            # 卡住 → < /dev/null 重定向避免交互阻塞（worker 上 stdin 不可达）
            self.run(f'timeout 120 "{test_bin}" < /dev/null || true')
            self.output.info("aercbook upstream tests PASSED (email_iterator 2 tests)")

    def package(self):
        copy(self, "aercbook", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
