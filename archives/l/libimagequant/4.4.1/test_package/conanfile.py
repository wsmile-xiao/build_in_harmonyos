#!/usr/bin/env python3
"""Conan test_package — libimagequant 4.4.1.

两段式验证：

1. 消费者测试（test_package/test_consumer.c，R34 实质调用被测库 API）：
   pngquant 同款用法 roundtrip —— liq_attr_create → liq_image_create_rgba
   → liq_quantize_image → liq_write_remapped_image，断言调色板规模、
   索引范围、dither 设置、销毁全链路。

2. 上游测试（cargo test --release --workspace --tests 真跑）：
   21 项（imagequant lib 16 + imagequant-sys ffi 4 + c_test 1——
   c_test 内部串跑 test.c 的 5 个 C 断言函数）。
   hmbs preflight 只在 test_package 阶段 stdout 采集 HMBS 标记
   （tlsx/scooter 先例），故上游测试在本 test() 中执行。

emits:
  HMBS_TEST_PACKAGE_RESULT  — 消费者 roundtrip 测试结果
  HMBS_UPSTREAM_TEST_RESULT — 上游 cargo test 结果
"""
import json
import os
import platform
import re
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy
from conan.tools.layout import basic_layout

UPSTREAM_TEST_DISCOVERED = 21
UPSTREAM_TEST_FRAMEWORK = "cargo-test"
UPSTREAM_TEST_COMMAND = "cargo test --release --workspace --tests --no-fail-fast"


class LibimagequantTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("rust-toolchain/1.97.1")
        self.tool_requires("openssl/3.5.6.1.1")

    def layout(self):
        basic_layout(self)

    @staticmethod
    def _build_machine_is_ohos():
        try:
            return (platform.machine() == "aarch64"
                    and platform.system() in ("Linux", "HarmonyOS"))
        except Exception:
            return False

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return (compilers.get("c")
                or os.environ.get("CC")
                or "clang")

    def _sign_tool(self):
        cc = self._cc()
        sign_tool = os.path.join(os.path.dirname(cc), "binary-sign-tool")
        return sign_tool if os.path.isfile(sign_tool) else None

    # ------------------------------------------------------------------
    # Rust runtime（与主配方同款：签名私有拷贝 + openssl relink）
    # ------------------------------------------------------------------
    def _prepare_rust_runtime(self):
        import certifi
        from pathlib import Path
        rust = self.dependencies.build["rust-toolchain"].package_folder
        openssl = self.dependencies.build["openssl"].package_folder
        runtime = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(runtime, exist_ok=True)
        cc = self._cc()
        sign_tool = self._sign_tool()

        # openssl → 私有 libssl/libcrypto
        for name in ("crypto", "ssl"):
            dst = os.path.join(runtime, f"lib{name}.so")
            if os.path.isfile(dst):
                continue
            matches = [str(p) for p in Path(openssl).rglob(f"lib{name}.a")]
            if not matches:
                raise ConanException(f"lib{name}.a not found in openssl package")
            cmd = [cc, "-shared", "-Wl,-z,relro,-z,now",
                   f"-Wl,-soname,lib{name}.so",
                   "-Wl,--whole-archive", matches[0], "-Wl,--no-whole-archive",
                   "-ldl", "-pthread"]
            if name == "ssl":
                cmd += ["-L" + runtime, "-lcrypto"]
            cmd += ["-o", dst]
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)

        # 签名 cargo/rustc/driver
        bin_dir = os.path.join(runtime, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        final_cargo = os.path.join(bin_dir, "cargo")
        final_rustc = os.path.join(bin_dir, "rustc")
        if not (os.path.isfile(final_cargo) and os.path.isfile(final_rustc)):
            pkg_cargo = os.path.join(rust, "bin", "cargo")
            pkg_rustc = os.path.join(rust, "bin", "rustc")
            # OHOS（HMDFS 执行标签限制）：os.access(X_OK) 不可靠——包内
            # 二进制有执行位但仍无法 exec。有签名工具时永远走签名路径；
            # 仅无签名工具（Linux worker）时才探测原生可执行性。
            if (sign_tool is None
                    and os.access(pkg_cargo, os.X_OK)
                    and os.access(pkg_rustc, os.X_OK)):
                return pkg_cargo, pkg_rustc, rust
            if sign_tool is None:
                raise ConanInvalidConfiguration(
                    "binary-sign-tool unavailable; rust binaries not executable")
            for tool in ("cargo", "rustc"):
                result = subprocess.run(
                    [sign_tool, "sign", "-inFile", os.path.join(rust, "bin", tool),
                     "-outFile", os.path.join(bin_dir, tool), "-selfSign", "1"],
                    capture_output=True, timeout=300)
                if result.returncode:
                    raise ConanException(
                        "signing %s failed: %s" % (
                            tool, result.stderr.decode(errors="replace")[-2000:]))
                os.chmod(os.path.join(bin_dir, tool), 0o755)
            for driver in os.listdir(os.path.join(rust, "lib")):
                if driver.startswith("librustc_driver") and driver.endswith(".so"):
                    dst = os.path.join(runtime, driver)
                    if os.path.isfile(dst):
                        continue
                    result = subprocess.run(
                        [sign_tool, "sign", "-inFile",
                         os.path.join(rust, "lib", driver),
                         "-outFile", dst, "-selfSign", "1"],
                        capture_output=True, timeout=300)
                    if result.returncode:
                        raise ConanException(
                            "signing %s failed: %s" % (
                                driver, result.stderr.decode(errors="replace")[-2000:]))
                    os.chmod(dst, 0o755)
        # libc++_shared.so：防 /data/storage/el1/bundle/libs/arm64 的
        # 不兼容副本遮蔽系统库（Electron 应用自带）；HMDFS 拷贝的
        # .so 需签名才能加载
        libcxx = os.path.join(runtime, "libc++_shared.so")
        if not os.path.isfile(libcxx):
            import shutil
            source = None
            for candidate in ("/system/lib64/libc++_shared.so",
                              "/usr/lib/libc++_shared.so"):
                if os.path.isfile(candidate):
                    source = candidate
                    break
            if source is None:
                raise ConanInvalidConfiguration(
                    "libc++_shared.so not found on this system")
            if sign_tool is not None:
                result = subprocess.run(
                    [sign_tool, "sign", "-inFile", source,
                     "-outFile", libcxx, "-selfSign", "1"],
                    capture_output=True, timeout=300)
                if result.returncode:
                    raise ConanException(
                        "signing libc++_shared.so failed: %s" %
                        result.stderr.decode(errors="replace")[-2000:])
                os.chmod(libcxx, 0o755)
            else:
                shutil.copy2(source, libcxx)
        # rustc sysroot 推导布局：签名 driver 放 runtime/lib/（真实文件），
        # rustlib 目录符号链接挂进同一 lib/ → sysroot=runtime
        lib_dir = os.path.join(runtime, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        rustlib_link = os.path.join(lib_dir, "rustlib")
        if not os.path.exists(rustlib_link):
            os.symlink(os.path.join(rust, "lib", "rustlib"), rustlib_link)
        for driver in os.listdir(runtime):
            if driver.startswith("librustc_driver") and driver.endswith(".so"):
                src = os.path.join(runtime, driver)
                dst = os.path.join(lib_dir, driver)
                if not os.path.exists(dst):
                    os.rename(src, dst)
        # realpath 归一：防 conan env 脚本的 conan/../../ 前缀让 rustc
        # 字面推导出错误 sysroot
        return (os.path.realpath(final_cargo),
                os.path.realpath(final_rustc), rust)

    def _rust_target(self):
        if str(self.settings.os) != "OHOS":
            return None
        return "aarch64-unknown-linux-ohos"

    def _ensure_cc_linker(self):
        """Expose clang as cc/gcc for the cc crate (c_test builds test.c)."""
        import shutil
        cc = self._cc()
        if os.path.basename(cc) in ("cc", "gcc"):
            return
        bindir = os.path.join(self.build_folder, ".ccbin")
        os.makedirs(bindir, exist_ok=True)
        for name in ("cc", "gcc"):
            link = os.path.join(bindir, name)
            if not os.path.lexists(link):
                os.symlink(cc, link)
        return bindir

    # ------------------------------------------------------------------
    # test()
    # ------------------------------------------------------------------
    def build(self):
        if not can_run(self):
            return
        # 编译消费者测试（链接打包产物 lib/libimagequant.a）
        copy(self, "test_consumer.c", src=self.source_folder,
             dst=self.build_folder)
        cc = self._cc()
        libdir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "lib")
        incdir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "include")
        self.run(
            f"{shlex.quote(cc)} -O2 -Wall -Werror "
            f"-I{shlex.quote(incdir)} test_consumer.c "
            f"-L{shlex.quote(libdir)} -limagequant -lpthread -lm -ldl "
            f"-o test_consumer",
            env=["conanbuild"])

    def test(self):
        # ---------- 1. 消费者 roundtrip 测试 ----------
        consumer_ok = False
        consumer_cmd = ""
        if self._build_machine_is_ohos() and can_run(self):
            consumer_cmd = "./test_consumer"
            try:
                self.run(consumer_cmd, env=["conanbuild", "conanrun"])
                consumer_ok = True
            except ConanException:
                consumer_ok = False
        else:
            self.output.info("consumer runtime test deferred: "
                             "build machine is not aarch64 OHOS host")
        marker = {
            "executed": consumer_ok,
            "passed": consumer_ok,
            "command": consumer_cmd or "test_consumer (deferred to OHOS CI)",
            "discovered": 1,
            "passedCount": 1 if consumer_ok else 0,
            "failed": 0 if consumer_ok else 1,
            "skipped": 0 if consumer_ok else 1,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(marker)}")
        if not consumer_ok and self._build_machine_is_ohos():
            raise ConanException("consumer roundtrip test failed")

        # ---------- 2. 上游 cargo test 真跑 ----------
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        import certifi
        cargo, rustc, rust = self._prepare_rust_runtime()
        target = self._rust_target()
        cc = self._cc()
        ccbin = self._ensure_cc_linker()

        # cargo config（镜像 + linker + CA）
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
        ca = certifi.where()
        config = (
            '[source.crates-io]\n'
            'replace-with = "rsproxy-sparse"\n'
            '[source.rsproxy-sparse]\n'
            'registry = "sparse+https://rsproxy.cn/index/"\n'
            '[net]\nretry = 10\n'
            '[http]\ntimeout = 600\ncainfo = "%s"\n' % ca
        )
        if target:
            config += f'\n[target.{target}]\nlinker = "{cc}"\n'
        with open(os.path.join(cargo_home, "config.toml"), "w", encoding="utf-8") as f:
            f.write(config)

        # 源码：重新下载被测包 conandata 声明的源码（与包构建同源），
        # 解压到 build/src-upstream 跑上游测试
        from conan.tools.files import get as conan_get
        src_root = os.path.join(self.build_folder, "src-upstream")
        os.makedirs(src_root, exist_ok=True)
        # 源码地址：test_package 的 conan_data 为空，从主配方 conandata.yml
        # 读（recipe_folder = 原始 test_package/ 目录，上一级是版本目录）
        import yaml
        version_dir = os.path.dirname(self.recipe_folder)
        with open(os.path.join(version_dir, "conandata.yml"),
                  encoding="utf-8") as f:
            sources = yaml.safe_load(f)["sources"]
        conan_get(self, **sources, strip_root=True, destination=src_root)

        env = dict(os.environ)
        runtime = os.path.join(self.build_folder, "rust-runtime")
        env.update({
            "CARGO": cargo,
            "RUSTC": rustc,
            "CC": cc,
            "CARGO_HOME": cargo_home,
            "CARGO_NET_RETRY": "10",
            "CARGO_HTTP_TIMEOUT": "600",
            "CARGO_HTTP_CAINFO": ca,
            "SSL_CERT_FILE": ca,
            "LD_LIBRARY_PATH": os.pathsep.join([
                os.path.join(runtime, "lib"),
                runtime,
                env.get("LD_LIBRARY_PATH", ""),
            ]),
            "PATH": os.pathsep.join([
                os.path.dirname(cargo),
                ccbin or "",
                env.get("PATH", ""),
            ]),
        })
        rustflags = f"-C linker={cc}"
        env["RUSTFLAGS"] = rustflags

        test_args = [cargo, "test", "--release", "--workspace", "--tests",
                     "--no-fail-fast"]
        if target:
            test_args += ["--target", target]
        print(f"running upstream tests: {' '.join(test_args)}", flush=True)

        proc = subprocess.run(
            test_args, capture_output=True, text=True,
            cwd=src_root, env=env, timeout=3600)
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)

        result_lines = re.findall(
            r"test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;"
            r" (\d+) measured; (\d+) filtered out",
            output)
        passed = sum(int(n) for _, n, _, _, _, _ in result_lines)
        failed = sum(int(n) for _, _, n, _, _, _ in result_lines)
        ignored = sum(int(n) for _, _, _, n, _, _ in result_lines)
        executed = passed + failed
        status = ("passed"
                  if (proc.returncode == 0 and failed == 0 and executed > 0)
                  else "failed")
        marker = {
            "status": status,
            "framework": UPSTREAM_TEST_FRAMEWORK,
            "command": " ".join(shlex.quote(p) for p in test_args),
            "discovered": executed + ignored,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": ignored,
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker, ensure_ascii=False)}")
        if status != "passed":
            raise ConanException(
                f"upstream cargo test failed (rc={proc.returncode}, "
                f"passed={passed}, failed={failed})")
