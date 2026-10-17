#!/usr/bin/env python3
"""Conan recipe — termbg 0.6.2 (Rust crate: terminal background color detection)。

上游 https://github.com/dalance/termbg，tag ``v0.6.2``（crates.io 官方 crate 包，
sha256 见 conandata.yml）。构建系统 **cargo**（``Cargo.toml`` 的 ``build = false``，
上游无 ``build.rs``、无 CMake/autotools/meson）；产物为 ``bin/termbg``（上游自带的
check program）。

工具链
------
制品仓基础设施包 ``rust-toolchain/1.97.1``（tool_requires）：rust-lang 官方 dist
预编译，宿主与目标均为 ``aarch64-unknown-linux-ohos``。不使用 rustup —— 标准 rustup
无法识别 HarmonyOS 宿主（``unrecognized OS type: HarmonyOS``，知识 E105/E154）。

OHOS 平台适配（均为**构建环境**适配，上游源码零改动）
------------------------------------------------------
1. ``tool_requires`` 包内的 ``cargo``/``rustc``/``librustc_driver*.so`` 无 code
   signature，HarmonyOS 拒绝 execve 未签名 ELF（EACCES errno 13）。配方把它们复制到
   build 目录并用 ``binary-sign-tool -selfSign 1`` 自签名，其余只读负载用符号链接
   （below/librsvg 先例）。**CI 干净环境**二进制可直接执行时，``_probe`` 探测
   ``cargo --version`` 成功即直接使用包内路径，不做任何复制/签名。
2. ``cargo`` 动态链接 ``libssl.so``/``libcrypto.so``（OpenSSL 3.x 符号），系统
   ``/usr/lib`` 的 OpenSSL 3.0 缺 ``SSL_get0_group_name`` 等符号 → 使用 Harmonybrew
   的 OHOS 预编译 bottle（sha256 固定，知识 E509），并在 ``LD_LIBRARY_PATH`` 前置。
3. crates.io 直连在设备上无可用 CA 且速度差 → ``rsproxy.cn`` sparse 镜像 + CA bundle
   （argc/below/cargo-bloat 先例）。

上游测试（R51 三步法）
-----------------------
``cargo test --release --locked --target aarch64-unknown-linux-ohos --tests``：
上游共 **6** 个 ``#[test]``（全部位于 ``src/lib.rs`` 的 ``#[cfg(test)] mod tests``），
设备实测 **6 passed / 0 failed / 0 ignored**。结果落盘 ``res/upstream_test_result.json``，
由 test_package 重发 ``HMBS_UPSTREAM_TEST_RESULT`` 标记（hmbs preflight 只从
test_package 阶段 stdout 采集该标记 —— scooter/abuild-sudo 先例）。
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches)
from conan.tools.layout import basic_layout

# 上游测试静态清点（src/lib.rs 的 #[test] 宏数量，见 test_package/MANIFEST.yml）
UPSTREAM_TEST_DISCOVERED = 6
UPSTREAM_TEST_FRAMEWORK = "cargo-test"


class TermbgConan(ConanFile):
    name = "termbg"
    version = "0.6.2"
    description = ("A Rust library for terminal background color detection "
                   "(ships the termbg check program)")
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/dalance/termbg"
    url = "https://github.com/dalance/termbg"
    package_type = "application"

    # L0p: OHOS profile 要求 settings 四项齐全
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        # conandata.yml 的 patches 段当前为空（上游源码零改动），仍保留补丁管线
        # 入口，便于后续版本以补丁形式承载平台修复。
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"termbg requires Linux or OHOS, got {self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64", "aarch64"):
            raise ConanInvalidConfiguration(
                f"termbg 0.6.2 recipe targets aarch64, got {self.settings.arch}")

    def build_requirements(self):
        # R36：依赖先发布再构建下游。rust-toolchain/1.97.1 已发布在 ohpcd 制品仓，
        # 配方只声明引用，不硬编码 remote（remote 属 CI 环境配置，见 notes.md §2.1）。
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        # crates.io 的 `.crate` 是 gzip tar，但扩展名不被 conan get() 识别
        # （会按 zip 解包并抛 BadZipFile），因此显式下载 + tarfile 解包。
        sources = self.conan_data["sources"]
        tarball = os.path.join(self.source_folder, "termbg-0.6.2.tar.gz")
        download(self, sources["url"], tarball, sha256=sources["sha256"])
        with tarfile.open(tarball, "r:gz") as handle:
            handle.extractall(self.source_folder)
        os.remove(tarball)
        # crate 包顶层目录为 termbg-0.6.2/，等价于 strip_root=True
        inner = os.path.join(self.source_folder, "termbg-0.6.2")
        if not os.path.isdir(inner):
            raise ConanException("unexpected crate layout: termbg-0.6.2/ missing")
        for entry in os.listdir(inner):
            shutil.move(os.path.join(inner, entry),
                        os.path.join(self.source_folder, entry))
        os.rmdir(inner)

    # ── 工具链解析 ──────────────────────────────────────────────────────

    def _rust_target(self):
        if str(self.settings.os) != "OHOS":
            return None
        return "aarch64-unknown-linux-ohos"

    @staticmethod
    def _find_binary_sign_tool():
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/toolchains/"
            "lib/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _toolchain_root(self):
        dep = self.dependencies.build.get("rust-toolchain")
        if dep is None:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available")
        return dep.package_folder

    def _runtime_lib_dirs(self):
        """下载 Harmonybrew 的 OHOS 预编译运行库（cargo 的 libssl/libcrypto/libz）。

        下载失败只警告不中断：CI 镜像可能已自带可用的 OpenSSL 3.x。
        """
        if str(self.settings.os) != "OHOS":
            return []
        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for item in self.conan_data.get("rust_runtime", []):
            tgz = os.path.join(base, item["name"] + ".tar.gz")
            try:
                if not os.path.isfile(tgz):
                    download(self, item["url"], tgz, sha256=item["sha256"])
                extract_dir = os.path.join(base, item["name"])
                os.makedirs(extract_dir, exist_ok=True)
                with tarfile.open(tgz, "r:gz") as handle:
                    handle.extractall(extract_dir)
            except Exception as exc:  # noqa: BLE001 - 网络/校验失败降级
                self.output.warning(
                    "rust runtime bottle %s unavailable (%s); relying on the "
                    "system OpenSSL" % (item["name"], exc))
                continue
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) != "lib":
                    continue
                if any(name.startswith(("libssl.", "libcrypto.", "libz."))
                       for name in files):
                    lib_dirs.append(root)
        return lib_dirs

    def _ca_bundle(self):
        candidates = [
            os.environ.get("CURL_CA_BUNDLE"),
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
        ]
        try:
            import certifi
            candidates.append(certifi.where())
        except ImportError:
            pass
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _prepare_signed_toolchain(self):
        """把 rust-toolchain 包内的可执行件复制到 build 目录并自签名。

        HarmonyOS 拒绝 execve 未签名 ELF。rustc 以自身可执行文件路径上两级为
        sysroot，因此保持 ``<root>/bin/{cargo,rustc}`` + ``<root>/lib/{librustc_driver,
        rustlib}`` 布局，其余只读负载（etc/libexec/share 及 lib 下其它文件）用符号链接。
        幂等（marker 文件）。
        """
        src = self._toolchain_root()
        root = os.path.join(self.build_folder, "rust-toolchain-signed")
        bin_dir = os.path.join(root, "bin")
        lib_dir = os.path.join(root, "lib")
        marker = os.path.join(root, ".prepared")
        if os.path.isfile(marker):
            return os.path.join(bin_dir, "cargo"), os.path.join(bin_dir, "rustc"), root

        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        signer = self._find_binary_sign_tool()
        if signer is None:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found and rust-toolchain package binaries "
                "are not directly executable on this filesystem")

        to_sign = []
        for name in ("cargo", "rustc"):
            source = os.path.join(src, "bin", name)
            if not os.path.isfile(source):
                raise ConanException(f"rust-toolchain package misses bin/{name}")
            dest = os.path.join(bin_dir, name)
            shutil.copy2(source, dest)
            to_sign.append(dest)
        src_lib = os.path.join(src, "lib")
        for name in sorted(os.listdir(src_lib)):
            if name.startswith("librustc_driver") and name.endswith(".so"):
                dest = os.path.join(lib_dir, name)
                shutil.copy2(os.path.join(src_lib, name), dest)
                to_sign.append(dest)

        for path in to_sign:
            signed = path + ".signed"
            result = subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", signed,
                 "-selfSign", "1"],
                capture_output=True, timeout=300)
            if result.returncode != 0 or not os.path.isfile(signed):
                raise ConanException(
                    "binary-sign-tool failed for %s (rc=%d): %s"
                    % (path, result.returncode,
                       result.stderr.decode(errors="replace")[-500:]))
            os.replace(signed, path)
            os.chmod(path, 0o755)

        # 只读负载：符号链接（rustc 的 sysroot == root，lib/rustlib 必须可见）
        for name in sorted(os.listdir(src_lib)):
            dest = os.path.join(lib_dir, name)
            if not os.path.exists(dest):
                os.symlink(os.path.join(src_lib, name), dest)
        for name in ("etc", "libexec", "share"):
            source = os.path.join(src, name)
            dest = os.path.join(root, name)
            if os.path.isdir(source) and not os.path.exists(dest):
                os.symlink(source, dest)

        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("signed rust toolchain prepared\n")
        return os.path.join(bin_dir, "cargo"), os.path.join(bin_dir, "rustc"), root

    def _resolve_toolchain(self, extra_lib_dirs):
        """返回 (cargo, rustc, toolchain_root, base_env)。

        先探测 tool_requires 包内二进制能否直接执行（CI 干净环境）；失败再走
        签名私有副本（OHOS 设备的 HMDFS/签名限制）。
        """
        src = self._toolchain_root()
        ca = self._ca_bundle()
        base_env = os.environ.copy()
        for key in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "CPATH",
                    "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH",
                    "CARGO_BUILD_TARGET", "RUSTC_BOOTSTRAP", "RUSTUP_TOOLCHAIN"):
            base_env.pop(key, None)
        if ca:
            base_env["SSL_CERT_FILE"] = ca
            base_env["CURL_CA_BUNDLE"] = ca
        # cargo 运行期库搜索路径：签名 driver 目录 + Harmonybrew 运行库
        base_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            extra_lib_dirs + [os.path.join(src, "lib")]
            + ([base_env["LD_LIBRARY_PATH"]] if base_env.get("LD_LIBRARY_PATH")
               else []))

        package_cargo = os.path.join(src, "bin", "cargo")
        probe_env = dict(base_env)
        probe_env["PATH"] = os.path.join(src, "bin") + os.pathsep + probe_env.get(
            "PATH", "")
        if os.path.isfile(package_cargo) and self._cargo_works(
                package_cargo, probe_env):
            self.output.info(
                "rust-toolchain package binaries are directly executable; "
                "using them as-is (no signing needed)")
            return package_cargo, os.path.join(src, "bin", "rustc"), src, base_env

        self.output.info(
            "rust-toolchain package binaries are not executable here "
            "(unsigned ELF / HMDFS); preparing signed private copy")
        cargo, rustc, root = self._prepare_signed_toolchain()
        env = dict(base_env)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            extra_lib_dirs + [os.path.join(root, "lib")]
            + ([base_env["LD_LIBRARY_PATH"]] if base_env.get("LD_LIBRARY_PATH")
               else []))
        return cargo, rustc, root, env

    @staticmethod
    def _cargo_works(cargo, env):
        try:
            result = subprocess.run([cargo, "--version"], env=env,
                                    capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0

    # ── 构建环境 ────────────────────────────────────────────────────────

    def _build_env(self, cargo, rustc, toolchain_root):
        env = os.environ.copy()
        target = self._rust_target()
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}) or {}
        cc = compilers.get("c") or "/data/service/hnp/bin/clang"
        cxx = compilers.get("cpp") or "/data/service/hnp/bin/clang++"

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)

        env.update({
            "CARGO": cargo,
            "RUSTC": rustc,
            "CC": cc,
            "CXX": cxx,
            "CARGO_HOME": cargo_home,
            "CARGO_TARGET_DIR": os.path.join(self.build_folder, "target"),
            "CARGO_NET_RETRY": "10",
            "CARGO_HTTP_TIMEOUT": "600",
            "CARGO_BUILD_JOBS": "2",
            "TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir,
        })
        if target:
            upper = target.upper().replace("-", "_")
            env[f"CARGO_TARGET_{upper}_LINKER"] = cc
            env["RUSTFLAGS"] = f"-C linker={cc}"
        env["PATH"] = os.pathsep.join(
            [os.path.dirname(cargo)]
            + [d for d in ("/system/bin", "/system/sbin") if os.path.isdir(d)]
            + [env.get("PATH", "")])
        # LD_LIBRARY_PATH 由 _resolve_toolchain 配好，但 PATH 上的 cargo 被
        # conanbuild 注入的 tool_requires 包路径覆盖时会指回未签名二进制，
        # 因此这里再保险地把签名目录前置一次。
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [os.path.join(toolchain_root, "lib"), env.get("LD_LIBRARY_PATH", "")])
        self._write_cargo_config(cargo_home, cc, target)
        return env

    def _write_cargo_config(self, cargo_home, cc, target):
        """$CARGO_HOME/config.toml：rsproxy 镜像 + CA + 目标 linker（不改源码树）。"""
        ca = self._ca_bundle()
        content = (
            "[source.crates-io]\n"
            'replace-with = "rsproxy-sparse"\n\n'
            "[source.rsproxy-sparse]\n"
            'registry = "sparse+https://rsproxy.cn/index/"\n\n'
            "[net]\n"
            "retry = 10\n\n"
            "[http]\n"
            "timeout = 600\n"
        )
        if ca:
            content += 'cainfo = "%s"\n' % ca
        if target:
            content += ('\n[target.%s]\nlinker = "%s"\n' % (target, cc))
        with open(os.path.join(cargo_home, "config.toml"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _run_cargo(self, cmd, env, cwd, log_name):
        """用**显式 env 字典**运行 cargo，并把 stdout/stderr 落盘。

        必须走 subprocess 而不是 ``self.run(env=...)``：conan 的 ``self.run``
        默认套用 conanbuild 环境，会把 tool_requires ``rust-toolchain/1.97.1``
        注入的 ``LD_LIBRARY_PATH=<pkg>/lib``（未签名副本所在目录）盖回我们的
        签名目录之上，rustc 随即找不到 ``librustc_driver*.so`` 而 exit 127
        （librsvg round-39 同款问题）。
        """
        log = os.path.join(self.build_folder, log_name)
        with open(log, "w", encoding="utf-8") as handle:
            handle.write("$ " + " ".join(shlex.quote(p) for p in cmd) + "\n")
            handle.write("LD_LIBRARY_PATH=%s\n\n" % env.get("LD_LIBRARY_PATH"))
            handle.flush()
            result = subprocess.run(cmd, cwd=cwd, env=env, stdout=handle,
                                    stderr=subprocess.STDOUT)
            handle.write("\nexit=%d\n" % result.returncode)
        self.output.info("%s -> exit %d (log: %s)"
                         % (log_name, result.returncode, log))
        return result.returncode, log

    @staticmethod
    def _tail(path, size=4000):
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                return handle.read()[-size:]
        except OSError:
            return ""

    # ── 上游测试（R51）──────────────────────────────────────────────────

    def _run_upstream_tests(self, cargo, env):
        """真实运行上游 cargo 测试套件，结果落盘供 test_package 重发标记。"""
        target = self._rust_target()
        cmd = [cargo, "test", "--release", "--locked", "--tests",
               "--no-fail-fast"]
        if target:
            cmd += ["--target", target]
        returncode, log = self._run_cargo(cmd, env, self.source_folder,
                                         "upstream_cargo_test.log")
        with open(log, encoding="utf-8", errors="replace") as handle:
            text = handle.read()

        cases = {}
        for name, state in re.findall(r"^test (\S+) \.\.\. (\w+)", text,
                                      re.MULTILINE):
            cases[name] = state
        summary = {"passed": 0, "failed": 0, "ignored": 0}
        for passed, failed, ignored in re.findall(
                r"test result: \w+\. (\d+) passed; (\d+) failed; (\d+) ignored",
                text):
            summary["passed"] += int(passed)
            summary["failed"] += int(failed)
            summary["ignored"] += int(ignored)

        failed_names = sorted(n for n, s in cases.items() if s != "ok")
        payload = {
            "status": "passed" if returncode == 0
            and summary["failed"] == 0 else "failed",
            "framework": UPSTREAM_TEST_FRAMEWORK,
            "command": " ".join(cmd),
            "discovered": len(cases),
            "executed": len(cases),
            "passed": summary["passed"],
            "failed": summary["failed"],
            "skipped": summary["ignored"],
            "cases": dict(sorted(cases.items())),
            "log": os.path.basename(log),
        }
        if failed_names:
            payload["failed_cases"] = failed_names
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(payload, ensure_ascii=False))
        if payload["status"] != "passed":
            raise ConanException(
                "upstream termbg test suite failed: %s" % payload)
        return payload

    # ── 主流程 ─────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        lib_dirs = self._runtime_lib_dirs()
        cargo, rustc, toolchain_root, base_env = self._resolve_toolchain(lib_dirs)
        env = self._build_env(cargo, rustc, toolchain_root)
        # 保留 _resolve_toolchain 配置好的 LD_LIBRARY_PATH（含 Harmonybrew
        # 运行库），仅把工具链目录前置。
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [os.path.join(toolchain_root, "lib")] + lib_dirs
            + ([base_env.get("LD_LIBRARY_PATH", "")]
               if base_env.get("LD_LIBRARY_PATH") else []))

        self._run_upstream_tests(cargo, env)

        target = self._rust_target()
        cmd = [cargo, "build", "--release", "--locked"]
        if target:
            cmd += ["--target", target]
        returncode, log = self._run_cargo(cmd, env, self.source_folder,
                                          "cargo_build.log")
        if returncode != 0:
            raise ConanException(
                "cargo build failed (rc=%d); log %s\n%s"
                % (returncode, log, self._tail(log)))

        artifact = self._binary_path()
        if not os.path.isfile(artifact):
            raise ConanException(f"cargo build output not found: {artifact}")
        self.output.info("termbg built: %s" % artifact)

    def _binary_path(self):
        target = self._rust_target()
        if target:
            return os.path.join(self.build_folder, "target", target, "release",
                                "termbg")
        return os.path.join(self.build_folder, "target", "release", "termbg")

    def package(self):
        copy(self, "termbg", src=os.path.dirname(self._binary_path()),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE-*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # 上游测试证据随包携带：hmbs preflight 只从 test_package 阶段 stdout
        # 采集 HMBS_UPSTREAM_TEST_RESULT，且 conan 命中缓存时会跳过 build()。
        result = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_result.json", self.build_folder, res_dir,
                 keep_path=False)
        else:
            self.output.warning(
                "upstream_test_result.json missing; package will lack upstream "
                "test evidence")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
