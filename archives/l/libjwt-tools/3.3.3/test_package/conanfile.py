#!/usr/bin/env python3
"""Conan test_package for libjwt-tools 3.3.3 — 消费者视角验证（L1）。

两个 C 用例：
  * test_consumer.c —— 消费者另外直接 requires(libjwt/3.3.3)（见 requirements()
    注释：libjwt-tools 是 application 包，不 re-export libjwt 头/库，传递位置会被
    Conan 按 headers/libs 过滤），真实调用 libjwt 公开 API 完成
    HS256 签发 / 校验 / 篡改负样本。
  * test_ohos.c —— **本适配新增的鸿蒙（OHOS）测试用例**：从消费者视角验证
    libjwt-tools 交付的 4 个命令行工具经 Conan bindirs 通道可达，且为合法的
    OHOS aarch64 可执行文件（ELF64 / e_machine=183 / PT_INTERP / X_OK），
    并验证 DT_NEEDED 含 libjansson.so 而不含 libjwt.so（上游 jwt_add_tool()
    用 PRIVATE jwt_static 静态链接 libjwt → 工具交付物不依赖本体共享库）。

另有工具端到端执行（Python 层）：实际运行 bin/ 下的 key2jwk 与
jwt-generate / jwt-verify 完成「生成 JWK → 签发 → 校验通过 → 篡改后拒绝」。
C 用例只做静态/ELF 语义断言，不在 C 层 fork/exec（OHOS 对跨二进制 spawn
有额外管控），故工具的动态功能验证放在此处，两者互补。

OHOS 注意：本设备加载器对 LD_LIBRARY_PATH 的遵守不可靠（fcft/pango 先例），
故 generate() 给测试二进制嵌入 RUNPATH，并额外用
CMAKE_INSTALL_RPATH_USE_LINK_PATH 把链接行上的全部 libdir（含 jansson 等
传递依赖）自动纳入 RPATH。
"""
import glob
import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv

# 与上游 tests/keys/oct_key_256.json 同值的 HS256 对称密钥（用于工具端到端）
JWK_HS256 = ('{"keys":[{"kty":"oct","alg":"HS256",'
             '"k":"0gmNspkRljssLSrldySnYUS-zhtCo5sqeqo_yl7n2XA"}]}')

UPSTREAM_TOOLS = ("jwt-verify", "jwt-generate", "jwk2key", "key2jwk")


class LibjwtToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_consumer.c", "test_ohos.c"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ★ 必须显式声明 libjwt/3.3.3，才能让 test_consumer 拿到 libjwt 的头文件与库。
        #   libjwt-tools 的 package_type="application"，只把 bin/ 暴露给消费者，
        #   不 re-export libjwt 的头/库；libjwt 处于**传递**位置时 Conan 会按
        #   headers=False / libs=False 过滤其 cpp_info，CMakeDeps 生成的
        #   libjwt-release-armv8-data.cmake 里两个变量都是空值：
        #       set(libjwt_INCLUDE_DIRS_RELEASE )   # ← 空
        #       set(libjwt_LIBS_RELEASE )           # ← 空
        #     （同文件里 LIB_DIRS/BIN_DIRS/SYSTEM_LIBS 正常，说明包的 cpp_info 本身
        #       没问题、lib/libjwt.so 与 include/jwt.h 都在包内，纯粹是传递过滤）
        #   于是 test_consumer.c 的 #include <jwt.h> 报 "file not found"。
        #   显式声明后 libjwt 成为直接依赖，CMakeDeps 正常导出
        #   libjwt::libjwt 的 INTERFACE_INCLUDE_DIRECTORIES 与 -ljwt，
        #   test_consumer 才能真实调用 libjwt 公开 API（签发/校验/篡改负样本）。
        #   注：test_ohos.c 不依赖 libjwt 的头/库，只经 bindirs 通道验证 4 个工具
        #   本身，它才是「libjwt-tools 消费者」的本义用例。
        self.requires("libjwt/3.3.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()   # 提供 conanrun 环境（运行时库路径）

        tc = CMakeToolchain(self)
        # 消费者视角的 bin 目录通道：由被测包的 cpp_info.bindirs 决定
        tc.cache_variables["LIBJWT_TOOLS_BINDIR"] = self._tools_bindir()
        if str(self.settings.os) == "OHOS":
            libdirs = self._ohos_libdirs()
            if libdirs:
                rpath = ";".join(libdirs)
                tc.cache_variables["CMAKE_INSTALL_RPATH"] = rpath
                tc.cache_variables["CMAKE_BUILD_RPATH"] = rpath
                tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
                tc.cache_variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = True
                self.output.info("OHOS test RUNPATH dirs: %s" % ":".join(libdirs))
        tc.generate()

    def _tools_bindir(self):
        """被测包（libjwt-tools）的 bin 目录（经 cpp_info.bindirs 通道）。"""
        dep = self.dependencies[self.tested_reference_str]
        pkgdir = dep.package_folder
        if not pkgdir:
            raise ConanException("tested package folder unavailable")
        return os.path.join(pkgdir, "bin")

    def _ohos_libdirs(self):
        dirs = []
        for dep in self.dependencies.values():
            pkgdir = dep.package_folder
            if not pkgdir or not os.path.isdir(pkgdir):
                continue
            for sub in ("lib", "lib64"):
                d = os.path.join(pkgdir, sub)
                if os.path.isdir(d) and d not in dirs:
                    dirs.append(d)
        return dirs

    def _find_test_binary(self, name):
        for d in list(self.cpp.build.bindirs or []):
            cand = os.path.join(d, name)
            if os.path.isfile(cand):
                return cand
        hits = glob.glob(os.path.join(str(self.build_folder), "**", name),
                         recursive=True)
        for p in hits:
            if os.path.isfile(p) and not os.path.islink(p):
                return p
        return None

    def _sdk_llvm_libdir(self):
        """OHOS SDK 编译器 llvm/lib（含 lld 的 libxml2.so.16 运行时依赖）。"""
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or compilers.get("cpp") or "/data/service/hnp/bin/clang"
        cc_real = os.path.realpath(cc)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        return llvm_lib if os.path.isdir(llvm_lib) else ""

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # OHOS：conan 的 cmake.build() 会注入 -j<cpu_count> 并行，make jobserver
        # 在 musl 进程树下并行 spawn clang 会静默失败（同主包 conanfile 的规避）。
        # 改 subprocess 直接 `make -j1` 串行编译（绝对路径），绕开 jobserver 竞态。
        make = "/data/service/hnp/bin/make"
        env = os.environ.copy()
        sdk_ld = self._sdk_llvm_libdir()
        if sdk_ld:
            old_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(p for p in (sdk_ld, old_ld) if p)
            self.output.info("OHOS build LD_LIBRARY_PATH=%s" % env["LD_LIBRARY_PATH"])
        proc = subprocess.run([make, "-j1"], cwd=str(self.build_folder), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True)
        if proc.stdout:
            for line in proc.stdout.splitlines():
                self.output.info(line)
        if proc.returncode != 0:
            raise ConanException("test_package make -j1 build failed rc=%d"
                                 % proc.returncode)

    def _run_test(self, name, out_path):
        """执行单个测试二进制（失败 self.run 直接抛错），输出重定向后
        解析 ok:/FAIL: 行动态计数（不硬编码用例数）。"""
        binary = self._find_test_binary(name)
        if binary is None:
            raise ConanException("%s binary not found in the build tree" % name)
        self.run('"%s" > "%s" 2>&1' % (binary, out_path), env="conanrun")
        ok = fail = 0
        try:
            with open(out_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("ok:"):
                        ok += 1
                    elif line.startswith("FAIL:"):
                        fail += 1
        except OSError:
            pass
        return {"test": name, "ok": ok, "fail": fail}

    # ── 工具端到端（Python 层实际执行交付物）──────────────────────────────
    def _tool_env(self):
        """工具运行时环境：只需各依赖包的 libdir（工具静态链接 libjwt/OpenSSL，
        运行时动态依赖仅 libjansson.so）。"""
        env = os.environ.copy()
        libdirs = self._ohos_libdirs()
        old = env.get("LD_LIBRARY_PATH", "")
        if old:
            libdirs = libdirs + [old]
        if libdirs:
            env["LD_LIBRARY_PATH"] = ":".join(libdirs)
        return env

    def _tool_run(self, cmd):
        """执行工具命令并返回退出码（失败不抛异常，由调用方判定期望）。"""
        proc = subprocess.run(cmd, shell=True, cwd=str(self.build_folder),
                              env=self._tool_env(),
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        return proc.returncode

    def _run_tool_e2e(self):
        """实际执行 libjwt-tools 包内的命令，验证交付物动态可用。

        流程（对称 HS256）：写入 JWK → jwt-generate 签发 → jwt-verify 校验通过
        → 篡改末位后必须被拒绝。另用 key2jwk 从随机密钥生成 JWK，验证其可用。
        """
        bindir = self._tools_bindir()
        workdir = os.path.join(str(self.build_folder), "hmbs-tool-e2e")
        os.makedirs(workdir, exist_ok=True)

        for tool in UPSTREAM_TOOLS:
            if not os.path.isfile(os.path.join(bindir, tool)):
                raise ConanException("delivered tool missing: %s"
                                     % os.path.join(bindir, tool))

        jwk_path = os.path.join(workdir, "jwk_hs256.json")
        with open(jwk_path, "w", encoding="utf-8") as fh:
            fh.write(JWK_HS256)

        checks = []

        def record(name, ok, detail=""):
            checks.append({"name": name, "result": "PASS" if ok else "FAIL",
                           "detail": detail})

        # 1) key2jwk：随机密钥 → JWK（消费者可用性）
        key_bin = os.path.join(workdir, "rand.bin")
        with open(key_bin, "wb") as fh:
            fh.write(os.urandom(64))
        jwk_out = os.path.join(workdir, "generated.json")
        cmd = ('"%s" -o "%s" "%s"' % (os.path.join(bindir, "key2jwk"),
                                      jwk_out, key_bin))
        rc = self._tool_run(cmd)
        generated_ok = False
        if rc == 0 and os.path.isfile(jwk_out):
            try:
                with open(jwk_out, encoding="utf-8") as fh:
                    doc = json.load(fh)
                generated_ok = bool(doc.get("keys")) and all(
                    k.get("kty") for k in doc["keys"])
            except (OSError, ValueError):
                generated_ok = False
        record("key2jwk: 随机密钥 → 合法 JWK 文档", generated_ok, "rc=%s" % rc)

        # 2) jwt-generate：签发
        tok_path = os.path.join(workdir, "token.txt")
        cmd = ('"%s" -v -k "%s" -a HS256 -c s:iss=ohc-test '
               '-c s:sub=libjwt-tools -c i:exp=2000000000 > "%s"'
               % (os.path.join(bindir, "jwt-generate"), jwk_path, tok_path))
        rc = self._tool_run(cmd)
        token = ""
        if os.path.isfile(tok_path):
            with open(tok_path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if line.count(".") == 2 and " " not in line:
                        token = line
        record("jwt-generate: 产出三段式 token", bool(token) and rc == 0,
               "rc=%s token_len=%d" % (rc, len(token)))

        # 3) jwt-verify：正向校验必须通过
        if token:
            cmd = ('"%s" -v -k "%s" "%s" > /dev/null 2>&1'
                   % (os.path.join(bindir, "jwt-verify"), jwk_path, token))
            rc = self._tool_run(cmd)
            record("jwt-verify: 校验自签 token 通过", rc == 0, "rc=%s" % rc)

            # 4) jwt-verify：篡改后必须拒绝（负样本）
            bad = token[:-1] + ("A" if token[-1] != "A" else "B")
            cmd = ('"%s" -v -k "%s" "%s" > /dev/null 2>&1'
                   % (os.path.join(bindir, "jwt-verify"), jwk_path, bad))
            rc = self._tool_run(cmd)
            record("jwt-verify: 篡改 token 被拒绝（负样本）", rc != 0, "rc=%s" % rc)

        return checks

    def test(self):
        results = []
        tool_checks = []
        if can_run(self):
            if str(self.settings.os) == "OHOS":
                # RUNPATH 是主解析路径，这里再用 LD_LIBRARY_PATH 兜底
                libdirs = self._ohos_libdirs()
                if libdirs:
                    old = os.environ.get("LD_LIBRARY_PATH", "")
                    os.environ["LD_LIBRARY_PATH"] = ":".join(
                        libdirs + ([old] if old else []))
                    self.output.info("OHOS test LD_LIBRARY_PATH=%s"
                                     % os.environ["LD_LIBRARY_PATH"])

            out_dir = os.path.join(str(self.build_folder), "hmbs-testlog")
            os.makedirs(out_dir, exist_ok=True)
            # 1) 消费者用例（传递依赖 libjwt）
            results.append(self._run_test(
                "test_consumer", os.path.join(out_dir, "test_consumer.log")))
            # 2) 鸿蒙（OHOS）平台特有消费者用例（工具交付物形态）
            results.append(self._run_test(
                "test_ohos", os.path.join(out_dir, "test_ohos.log")))
            # 3) 工具端到端实际执行（交付物动态可用性）
            tool_checks = self._run_tool_e2e()

        discovered = sum(r["ok"] for r in results)
        failed = sum(r["fail"] for r in results)
        tool_failed = sum(1 for c in tool_checks if c["result"] == "FAIL")
        passed = (bool(results) and failed == 0 and tool_failed == 0
                  and all(r["ok"] > 0 for r in results))
        marker = {
            "executed": bool(results),
            "passed": passed,
            "command": "./test_consumer + ./test_ohos + tool e2e (key2jwk/jwt-generate/jwt-verify)",
            "discovered": discovered + len(tool_checks),
            "passedCount": (discovered + len(tool_checks)) if passed else 0,
            "tests": results,
            "ohos_specific_tests": [r for r in results if r["test"] == "test_ohos"],
            "tool_e2e": tool_checks,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if not results:
            raise ConanException(
                "libjwt-tools test consumer is not runnable on this configuration")
        if not passed:
            raise ConanException(
                "libjwt-tools test_package had failing checks: %s" % marker)
