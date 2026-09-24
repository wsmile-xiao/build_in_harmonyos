#!/usr/bin/env python3
"""Conan test_package — cryptsetup 2.8.8（消费者视角验证）

两层：
  层 A（C API）：test_cryptsetup.c 链接 libcryptsetup，真实创建并回读
                 LUKS2 头（覆盖 libjson-c 元数据路径 + openssl backend）。
  层 B（OHOS CLI 消费者用例，本轮新增）：直接运行包内 cryptsetup CLI，
                 在普通文件上完成 LUKS2 容器生命周期
                 （luksFormat -> isLuks -> luksDump -> luksUUID ->
                  luksHeaderBackup），全程不需要 root / dm-crypt 内核支持，
                 是 OHOS 平台上可真实执行的端到端消费者用例。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class CryptsetupTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _runtime_view(self):
        """OHOS 实体化运行时视图（E505/E316 同族）。

        libcryptsetup.so.12 的 DT_NEEDED（libjson-c.so.5、libdevmapper.so.1.02）
        指向依赖包内「SONAME 名是软链」的文件——OHOS musl/SELinux 域下加载
        失败（探针实测 rc=127）。把所有依赖（含被测包）lib/ 下 .so 跟随软链
        复制成实体文件汇总到视图目录，LD_LIBRARY_PATH 只指视图即可运行。
        本轮实测首错：CTest 直接 spawn 测试二进制（不经 conanrun.sh），
        `Error loading shared library libjson-c.so.5 (needed by
        libcryptsetup.so.12)` + json_* 全量符号 reloc 失败。
        """
        view = os.path.join(self.build_folder, "ohos-runtime-libs")
        os.makedirs(view, exist_ok=True)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                real_dir = os.path.join(dep.package_folder, libdir)
                if not os.path.isdir(real_dir):
                    continue
                for name in os.listdir(real_dir):
                    if ".so" not in name or name.endswith(".la"):
                        continue
                    src = os.path.join(real_dir, name)
                    if not os.path.isfile(src):
                        continue
                    dst = os.path.join(view, name)
                    if not os.path.exists(dst):
                        shutil.copy2(os.path.realpath(src), dst)
        return view

    # ── 层 B：OHOS CLI 端到端消费者用例 ──────────────────────────────
    def _ohos_cli_case(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        cs = os.path.join(pkg, "bin", "cryptsetup")
        if not os.path.isfile(cs):
            raise ConanException(f"packaged CLI missing: {cs}")

        work = os.path.join(self.build_folder, "ohos-luks2-case")
        os.makedirs(work, exist_ok=True)
        img = os.path.join(work, "luks2-container.img")
        key = os.path.join(work, "keyfile")
        backup = os.path.join(work, "header.backup")
        plain = os.path.join(work, "not-a-container.img")

        # 40MiB 稀疏文件（LUKS2 默认 16MiB 元数据区 + 数据偏移）
        for path, size in ((img, 40 * 1024 * 1024), (plain, 8 * 1024 * 1024)):
            with open(path, "wb") as f:
                f.truncate(size)
        with open(key, "wb") as f:
            f.write(b"ohos-consumer-key-0123456789\n")

        self.run(f'"{cs}" --version')

        # 1. 负向：非容器文件必须被判否（退出码非 0）
        rc = self.run(f'"{cs}" isLuks "{plain}"', ignore_errors=True)
        if rc == 0:
            raise ConanException("isLuks accepted a non-LUKS file (false positive)")
        self.output.info(f"OHOS case: isLuks rejects plain file (rc={rc})")

        # 2. 正向：在普通文件上创建 LUKS2 容器（无 root / 无 dm 内核模块亦可）
        self.run(
            f'"{cs}" --batch-mode luksFormat --type luks2 '
            f'--pbkdf pbkdf2 --pbkdf-force-iterations 1000 '
            f'--key-file "{key}" "{img}"',
        )

        # 3. 判真 + 头可解析（LUKS2 JSON 元数据由 libjson-c 解析）
        self.run(f'"{cs}" isLuks "{img}"')
        out_dump = os.path.join(work, "luksDump.txt")
        self.run(f'"{cs}" luksDump "{img}" > "{out_dump}"')
        with open(out_dump, "r", errors="replace") as f:
            dump = f.read()
        if "aes" not in dump or "Keyslots" not in dump:
            raise ConanException(f"luksDump output unexpected:\n{dump[:400]}")
        self.output.info("OHOS case: luksDump reports LUKS2 segments + aes")

        # 4. UUID 读取（libuuid 路径）
        out_uuid = os.path.join(work, "luksUUID.txt")
        self.run(f'"{cs}" luksUUID "{img}" > "{out_uuid}"')
        with open(out_uuid, "r", errors="replace") as f:
            uuid = f.read().strip()
        if len(uuid) != 36:
            raise ConanException(f"luksUUID returned '{uuid}' (expected 36 chars)")
        self.output.info(f"OHOS case: luksUUID = {uuid}")

        # 5. LUKS2 头备份（元数据区 + checksum 全量读写）
        self.run(
            f'"{cs}" --batch-mode luksHeaderBackup "{img}" '
            f'--header-backup-file "{backup}"',
        )
        if not (os.path.isfile(backup) and os.path.getsize(backup) > 1024 * 1024):
            raise ConanException("luksHeaderBackup produced no usable backup file")
        self.output.info(
            f"OHOS case: header backup {os.path.getsize(backup)} bytes")
        return img, uuid, backup

    def test(self):
        view = self._runtime_view()
        prev = os.environ.get("LD_LIBRARY_PATH")
        paths = [view] + ([prev] if prev else [])
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(paths)
        self.output.info(f"OHOS runtime view: {view}")
        try:
            cmake = CMake(self)
            cmake.test()           # 层 A：C API 消费者探针
            self._ohos_cli_case()  # 层 B：OHOS CLI 消费者用例
        finally:
            if prev is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = prev
