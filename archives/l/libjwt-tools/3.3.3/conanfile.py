#!/usr/bin/env python3
"""Conan recipe — libjwt-tools 3.3.3 (CMake).

libjwt-tools 是 LibJWT 项目命令行工具子包：上游 libjwt v3.3.3 同一源码树
tools/ 目录下的 4 个可执行文件（jwt-verify / jwt-generate / jwk2key /
key2jwk），发行版视角下由 `libjwt-tools` 单独承载（Alpine Origin=libjwt、
Provides cmd:jwk2key cmd:jwt-generate cmd:jwt-verify cmd:key2jwk）。

与本体 libjwt/3.3.3 的关系：
  * 同一 tarball、同一 sha256、同一补丁（同源子包，先例
    archives/b/babl-tools/0.1.126 → requires babl/0.1.126）；
  * requires("libjwt/3.3.3")（已发布 ohpcd，R35 实测 EXIT=0）；
  * 只构建 4 个工具目标，package() 只安装 bin/ 与 share/man/man1/；
  * OHOS 适配手法（串行 make、codegen 预生成、SONAME、依赖 .pc 生成）
    与本体保持一致，理由见本体 conanfile 与 notes.md。

上游测试（真实执行，非替代品）：
  上游 CMakeLists.txt:342 注册 add_test(NAME jwt_cli ...) 直接执行
  tests/jwt-cli.bats（9 个用例），由 `check` target 经 ctest 驱动。
  本镜像内没有 bats（find_program(bats) 探测不到），故按 add_test() 的
  等价语义逐条复现 9 个用例的「命令 + 断言」（见 _run_upstream_cli_tests），
  差异逐条登记在 notes.md「上游测试」节。
"""
import glob
import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps

# 上游 tools/ 的产出（CMakeLists.txt:194-205 四处 jwt_add_tool() 调用）
UPSTREAM_TOOLS = ("jwt-verify", "jwt-generate", "jwk2key", "key2jwk")

# 上游 tests/jwt-cli.bats 的用例数（add_test(NAME jwt_cli) 的执行体）
UPSTREAM_BATS_CASES = 9

# 与上游 tests/jwt-cli.bats 逐条对应的用例名（顺序即 bats 文件中的顺序）
UPSTREAM_CLI_CASE_NAMES = (
    "Generate a JWT with alg none",
    "Verify a JWT with alg none",
    "Generate a JWT with alg HS256",
    "Verify a JWT with alg HS256",
    "Generate a JWT with alg HS256 and claims",
    "Verify a JWT with alg HS256 with claims",
    "Generate JWKS from PEM Files",
    "Convert JWK to PEM - RSA",
    "Convert JWK to PEM - OCT",
)

# 上游 bats 断言里写死的期望值（照抄 tests/jwt-cli.bats）
BASIC_RES = "eyJhbGciOiJub25lIn0.e30."
HS256_RES = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30."
             "CM4dD95Nj0vSfMGtDas432AUW1HAo7feCiAbt5Yjuds")
CLAIM_RES = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
             "eyJhZG1pbiI6ZmFsc2UsImV4cCI6MTgzOTMxNzU2MiwiZm9vIjoiYmFyIiw"
             "iZ3JvdXAiOiJzdGFmZiIsImlzcyI6ImRpc2suc3dpc3NkaXNrLmNvbSIsInVzZXIiOiJi"
             "Y29sbGlucyJ9."
             "9RCEoB3XXGZrlU3JAx21x6p8mZguZS_NviKgJqEu330")


class LibjwtToolsConan(ConanFile):
    name = "libjwt-tools"
    version = "3.3.3"
    description = ("LibJWT command-line tools — jwt-verify, jwt-generate, "
                   "jwk2key and key2jwk for JWT/JWK(S) workflows")
    license = "MPL-2.0"
    homepage = "https://github.com/benmcollins/libjwt"
    url = "https://github.com/benmcollins/libjwt"

    # 只交付命令行工具（bin/ + man1），与同源子包先例 babl-tools 同款
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 同源子包惯例：requires 本体同版本（先例 archives/b/babl-tools/0.1.126）。
        # libjwt/3.3.3 已发布 ohpcd（R35：conan download --only-recipe EXIT=0，
        # 且含 OHOS aarch64 二进制包）。
        self.requires("libjwt/3.3.3")
        # ★ openssl/3.5.6 必须显式声明为 direct require，不能只依赖 libjwt 传递。
        #   上游 CMakeLists.txt:71 用 pkg_check_modules(OPENSSL openssl>=3.0.0 REQUIRED)
        #   无条件求值，因此 openssl.pc 必须落在 generators 目录里。
        #   仅靠 libjwt/3.3.3 传递时拿不到 openssl.pc，链路如下（conan 2.29.1 实测）：
        #     1) libjwt 的 package_info() 只暴露 cpp_info.libs=["jwt"]，openssl 的
        #        libcrypto.a/libssl.a 已静态链入 libjwt.so（libjwt.so 的 DT_NEEDED
        #        只有 libjansson.so）→ openssl 在 libjwt 上 run=false / libs=true；
        #     2) 该 require 经 graph.py:154 Requirement.transform_downstream() 传播到
        #        消费者这一层时 run=false / libs=false（消费者链接 libjwt.so 不需要
        #        openssl 的库与头文件）；
        #     3) graph_binaries.py:556-564 _skip_binaries() 对根节点只把 direct require
        #        放进 deps_required，于是该边 require.skip=True，节点 binary 变
        #        BINARY_SKIP；
        #     4) conan/internal/model/dependencies.py:167
        #        host = filter({"build": False, "test": False, "skip": False})
        #        → openssl 被过滤掉；pkgconfigdeps.py:335/364 正是遍历
        #        dependencies.host → 不产出 openssl.pc；
        #     5) CMake configure 报 "No package 'openssl' found"，构建失败。
        #   conan graph info 实测（消费者 → 依赖）：
        #        → libjwt/3.3.3     direct=true  run=true  libs=true  skip=false
        #        → jansson/2.15.1.1 direct=false run=true  libs=false skip=false
        #        → openssl/3.5.6    direct=false run=false libs=false skip=true(binary=Skip)
        #   jansson 之所以不受影响：libjwt.so 动态依赖 libjansson.so（run=true）→ skip=false。
        #   父包 libjwt/3.3.3 配方里 openssl 是它自己的 direct require，所以父包构建无此问题。
        #   声明为 direct require 后 conan graph info 变为 direct=true/skip=false，
        #   PkgConfigDeps 正常产出 openssl.pc（含 -L${libdir} -lssl -lcrypto -ldl -lpthread）。
        self.requires("openssl/3.5.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游用 pkg_check_modules()（pkg-config）而非 find_package() 定位
        # jansson / openssl → 必须生成它们的 .pc；CMakeToolchain 会把
        # generators 目录追加进 PKG_CONFIG_PATH。
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        # 工具包不构建/不注册上游测试（上游 check target 需要 libcheck）。
        # 关闭它只影响 add_test/check 注册，tools 目标本身是无条件构建的
        # （CMakeLists.txt:179-205 在 WITH_TESTS 块之外）。
        tc.variables["WITH_TESTS"] = "OFF"
        # 钉死全部可选加密/JSON 后端，保证构建结果与依赖图一致、可复现
        tc.variables["WITH_JSON_C"] = "OFF"
        tc.variables["WITH_GNUTLS"] = "OFF"
        tc.variables["WITH_MBEDTLS"] = "OFF"
        tc.variables["WITH_LIBCURL"] = "OFF"
        tc.variables["WITH_KCAPI_MD"] = "OFF"
        tc.variables["ENABLE_COVERAGE"] = "OFF"
        # HarmonyOS 平台模块缺失补偿（与本体同款，见本体 conanfile 的详注）：
        # CMake 无 Modules/Platform/HarmonyOS.cmake → SONAME 变量不会被赋值。
        # 本包只取 4 个静态链接的工具、不安装任何 .so，但 tools 链接目标
        # jwt_static 与共享库目标同处一个 CMakeLists，保持与本体一致的
        # 「实体文件 + 裸 SONAME」语义可避免依赖解析期出现版本化软链链。
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    # ── 构建 ──────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 只构建 4 个工具目标（jwt_static 会自动随之编译，但不构建
        # libcheck 测试套件与共享库目标，缩短构建面）。
        self._pregen_codegen_files()
        self._make_serial_build()
        # 上游测试：真实执行 tests/jwt-cli.bats 的 9 个用例语义
        self._run_upstream_cli_tests()

    def _sdk_llvm_libdir(self):
        """OHOS SDK 编译器 llvm/lib（lld 运行时依赖 libxml2.so.16）。

        本配方用 subprocess 直接调 make 以绕开 conan 的 buildenv 激活，
        故需显式把 llvm/lib 前置进 LD_LIBRARY_PATH，否则链接阶段会报
        "Error loading shared library libxml2.so.16"（同本体配方）。
        """
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or compilers.get("cpp") or "/data/service/hnp/bin/clang"
        cc_real = os.path.realpath(cc)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        return llvm_lib if os.path.isdir(llvm_lib) else ""

    def _pregen_codegen_files(self):
        """预生成 jwt-builder.i / jwt-checker.i。

        上游用 add_custom_command() 以 clang -E 预处理 libjwt/jwt-common.c
        得到这两个 .i（被 libjwt/jwt-builder.c、jwt-checker.c #include）。
        未打补丁前该命令的 `bash -c "..."` 引号会被 add_custom_command 的
        参数切分丢掉；补丁已改为直接调用编译器。此处仍预先生成，避免
        make 在 OHOS 上执行该 codegen 步骤（本体实测的 jobserver 竞态规避
        手法，保持一致）。输出目录 = cmake 的 binary dir = self.build_folder。
        """
        compiler = "/data/service/hnp/bin/clang"
        src = os.path.join(self.source_folder, "libjwt", "jwt-common.c")
        out_dir = self.build_folder
        for flag, out_name in (("JWT_BUILDER", "jwt-builder.i"),
                               ("JWT_CHECKER", "jwt-checker.i")):
            out = os.path.join(out_dir, out_name)
            if os.path.isfile(out):
                continue
            cmd = [compiler, "-E", "-D" + flag, src, "-o", out]
            self.output.info("OHOS pregen codegen: %s" % " ".join(cmd))
            proc = subprocess.run(cmd, cwd=out_dir,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True)
            if proc.returncode != 0:
                raise ConanException("pregen %s failed rc=%d:\n%s"
                                     % (out_name, proc.returncode, proc.stdout or ""))

    def _make_serial_build(self):
        """串行 make（-j1）构建 4 个工具目标，绕开 OHOS/musl 下 make
        jobserver 的并行 spawn 竞态（与本体同款规避，见本体 notes.md）。

        不调用 cmake.build()：它会按 tools.build:jobs 注入 -jN。
        """
        make = "/data/service/hnp/bin/make"
        cmd = [make, "-j1"] + list(UPSTREAM_TOOLS)
        self.output.info("OHOS serial build: %s" % " ".join(cmd))
        env = os.environ.copy()
        sdk_ld = self._sdk_llvm_libdir()
        if sdk_ld:
            old_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(p for p in (sdk_ld, old_ld) if p)
            self.output.info("OHOS build LD_LIBRARY_PATH=%s" % env["LD_LIBRARY_PATH"])
        proc = subprocess.run(cmd, cwd=self.build_folder, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True)
        if proc.stdout:
            for line in proc.stdout.splitlines():
                self.output.info(line)
        if proc.returncode != 0:
            raise ConanException("make -j1 (tools) build failed rc=%d"
                                 % proc.returncode)

    # ── 上游测试：tests/jwt-cli.bats 9 用例语义复现 ────────────────────────
    def _tools_dir(self):
        return os.path.join(self.build_folder, "tools")

    def _cli_test_env(self):
        """构造 CLI 测试运行时环境。

        工具经 jwt_static 静态链接 libjwt 与 OpenSSL，运行时只需
        libjansson.so（本体包实测 DT_NEEDED = libjansson.so + libc.so）。
        OHOS 加载器解析依赖包产物不依赖二进制内嵌 DT_RPATH，故把各依赖
        包 libdir 放进 LD_LIBRARY_PATH。
        """
        env = os.environ.copy()
        libdirs = []
        for dep in self.dependencies.values():
            pkgdir = dep.package_folder
            if not pkgdir or not os.path.isdir(pkgdir):
                continue
            for sub in ("lib", "lib64"):
                d = os.path.join(pkgdir, sub)
                if os.path.isdir(d) and d not in libdirs:
                    libdirs.append(d)
        old = env.get("LD_LIBRARY_PATH", "")
        if old:
            libdirs.append(old)
        if libdirs:
            env["LD_LIBRARY_PATH"] = ":".join(libdirs)
        return env

    @staticmethod
    def _json_normalize(value):
        """复现 bats 用例 7 里 jq 的 normalize 语义：

            def walk(f): ... def normalize: walk(if type == "array" then sort else . end);
            def equiv(x): normalize == (x | normalize);

        即：对象递归处理；数组先递归处理各元素再排序。
        """
        if isinstance(value, dict):
            return {k: LibjwtToolsConan._json_normalize(v)
                    for k, v in value.items()}
        if isinstance(value, list):
            items = [LibjwtToolsConan._json_normalize(v) for v in value]
            return sorted(items,
                          key=lambda y: json.dumps(y, sort_keys=True,
                                                   ensure_ascii=False))
        return value

    def _run_upstream_cli_tests(self):
        """逐条执行 tests/jwt-cli.bats 的 9 个用例（命令 + 断言）。

        每例独立记 PASS/FAIL；任一例失败即抛异常（避免"编译过但测试红"
        流入 CI）。结果以 HMBS_UPSTREAM_TEST_RESULT 标记打印供框架采集。
        """
        tools = self._tools_dir()
        srcdir = self.source_folder
        env = self._cli_test_env()
        cwd = self.build_folder

        for tool in UPSTREAM_TOOLS:
            if not os.path.isfile(os.path.join(tools, tool)):
                raise ConanException("upstream tool missing after build: %s"
                                     % os.path.join(tools, tool))

        def run(argv, stdin_text=None):
            return subprocess.run(argv, cwd=cwd, env=env,
                                  input=stdin_text,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, timeout=300)

        def tool(name):
            return os.path.join(tools, name)

        key_hs256 = os.path.join(srcdir, "tests", "keys", "oct_key_256.json")
        cases = []

        def record(name, ok, detail):
            cases.append({"name": name, "result": "PASS" if ok else "FAIL",
                          "detail": detail})
            self.output.info("  [%-4s] %s%s"
                             % ("PASS" if ok else "FAIL", name,
                                "" if ok else "  <- " + str(detail)[:200]))

        # ── 1. Generate a JWT with alg none ──
        p = run([tool("jwt-generate"), "-v", "-a", "none", "-n"])
        got = (p.stdout or "").strip()
        record(UPSTREAM_CLI_CASE_NAMES[0], got == BASIC_RES,
               "stdout=%r expected=%r rc=%d" % (got, BASIC_RES, p.returncode))

        # ── 2. Verify a JWT with alg none ──
        p = run([tool("jwt-verify"), "-v", BASIC_RES])
        record(UPSTREAM_CLI_CASE_NAMES[1], p.returncode == 0,
               "rc=%d stderr_tail=%r" % (p.returncode, (p.stderr or "")[-200:]))

        # ── 3. Generate a JWT with alg HS256 ──
        p = run([tool("jwt-generate"), "-v", "-a", "HS256", "-n", "-k", key_hs256])
        got = (p.stdout or "").strip()
        record(UPSTREAM_CLI_CASE_NAMES[2], got == HS256_RES,
               "stdout=%r expected=%r rc=%d" % (got, HS256_RES, p.returncode))

        # ── 4. Verify a JWT with alg HS256 ──
        p = run([tool("jwt-verify"), "-v", "-k", key_hs256, HS256_RES])
        record(UPSTREAM_CLI_CASE_NAMES[3], p.returncode == 0,
               "rc=%d stderr_tail=%r" % (p.returncode, (p.stderr or "")[-200:]))

        # ── 5. Generate a JWT with alg HS256 and claims ──
        p = run([tool("jwt-generate"), "-v", "-n",
                 "-k", key_hs256,
                 "-c", "s:group=staff",
                 "-c", "b:admin=false",
                 "-c", "s:iss=disk.swissdisk.com",
                 "-c", "s:user=bcollins",
                 "-c", "i:exp=1839317562",
                 "-j", '{"foo":"bar"}'])
        got = (p.stdout or "").strip()
        record(UPSTREAM_CLI_CASE_NAMES[4], got == CLAIM_RES,
               "stdout=%r expected=%r rc=%d" % (got, CLAIM_RES, p.returncode))

        # ── 6. Verify a JWT with alg HS256 with claims ──
        p = run([tool("jwt-verify"), "-v", "-k", key_hs256, CLAIM_RES])
        record(UPSTREAM_CLI_CASE_NAMES[5], p.returncode == 0,
               "rc=%d stderr_tail=%r" % (p.returncode, (p.stderr or "")[-200:]))

        # ── 7. Generate JWKS from PEM Files ──
        # 上游：key2jwk --disable-kid -o - <pem-files/*.pem> <pem-files/*.bin>
        #        | grep -v libjwt.io: > output.json
        #       然后 jq -n --slurpfile A tests/cli/all.json --slurpfile B output.json
        #       做 normalize 等价比较（jq 不在 OHOS 镜像中 → python3 等价实现）
        pem_dir = os.path.join(srcdir, "tests", "keys", "pem-files")
        pem_files = sorted(glob.glob(os.path.join(pem_dir, "*.pem"))) + \
            sorted(glob.glob(os.path.join(pem_dir, "*.bin")))
        p = run([tool("key2jwk"), "--disable-kid", "-o", "-"] + pem_files)
        filtered = [ln for ln in (p.stdout or "").splitlines()
                    if "libjwt.io:" not in ln]
        out_json = os.path.join(cwd, "output.json")
        with open(out_json, "w", encoding="utf-8") as fh:
            fh.write("\n".join(filtered) + "\n")
        try:
            with open(os.path.join(srcdir, "tests", "cli", "all.json"),
                      encoding="utf-8") as fh:
                expected_doc = json.load(fh)
            with open(out_json, encoding="utf-8") as fh:
                produced_doc = json.load(fh)
            equiv = (self._json_normalize(expected_doc)
                     == self._json_normalize(produced_doc))
            detail = ("equiv=%s keys(expected/produced)=%s/%s rc=%d"
                      % (equiv, sorted(expected_doc.keys()),
                         sorted(produced_doc.keys()), p.returncode))
        except (OSError, ValueError) as exc:
            equiv = False
            detail = "json compare failed: %s (rc=%d)" % (exc, p.returncode)
        record(UPSTREAM_CLI_CASE_NAMES[6], equiv, detail)

        # ── 8. Convert JWK to PEM - RSA ──
        rsa_out = "rsa_1024_0023a6e1-f093-448d-9038-9ff168611b86.pem"
        rsa_out_abs = os.path.join(cwd, rsa_out)
        if os.path.exists(rsa_out_abs):
            os.remove(rsa_out_abs)
        p = run([tool("jwk2key"), "-d", ".",
                 os.path.join(srcdir, "tests", "keys", "rsa_key_1024.json")])
        same = False
        detail = "rc=%d" % p.returncode
        if p.returncode == 0 and os.path.isfile(rsa_out_abs):
            with open(rsa_out_abs, "rb") as fa, \
                 open(os.path.join(srcdir, "tests", "keys", "pem-files",
                                   "rsa_key_1024.pem"), "rb") as fb:
                same = fa.read() == fb.read()
            detail = "cmp=%s rc=%d" % (same, p.returncode)
        else:
            detail = ("no output file rc=%d stderr=%r"
                      % (p.returncode, (p.stderr or "")[-200:]))
        record(UPSTREAM_CLI_CASE_NAMES[7], same, detail)

        # ── 9. Convert JWK to PEM - OCT ──
        oct_out = "oct_384.bin"
        oct_out_abs = os.path.join(cwd, oct_out)
        if os.path.exists(oct_out_abs):
            os.remove(oct_out_abs)
        p = run([tool("jwk2key"), "-d", ".",
                 os.path.join(srcdir, "tests", "keys", "oct_key_384.json")])
        same = False
        if p.returncode == 0 and os.path.isfile(oct_out_abs):
            with open(oct_out_abs, "rb") as fa, \
                 open(os.path.join(srcdir, "tests", "cli", "oct_384.bin"),
                      "rb") as fb:
                same = fa.read() == fb.read()
            detail = "cmp=%s rc=%d" % (same, p.returncode)
        else:
            detail = ("no output file rc=%d stderr=%r"
                      % (p.returncode, (p.stderr or "")[-200:]))
        record(UPSTREAM_CLI_CASE_NAMES[8], same, detail)

        passed = sum(1 for c in cases if c["result"] == "PASS")
        failed = len(cases) - passed
        marker = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "bats",
            "command": ("cd <build>; ./tools/<tool> ...  "
                        "(逐条复现 tests/jwt-cli.bats；镜像无 bats，"
                        "按 add_test(NAME jwt_cli) 的等价语义执行)"),
            "discovered": UPSTREAM_BATS_CASES,
            "executed": len(cases),
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "cases": cases,
            "deviations": [
                "用例 3-6 的密钥路径：上游 bats 写 '../tests/keys/oct_key_256.json'"
                "（假定 build 目录位于源码树内），本配方用源码树绝对路径"
                " '<source>/tests/keys/oct_key_256.json' 等价替代。",
                "用例 7 的 JSON 等价比较：上游用 jq（normalize = walk(if type =="
                " \"array\" then sort else . end)），OHOS 镜像内无 jq，本配方用"
                " python3 复现同一 normalize/equiv 语义。",
            ],
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if failed:
            raise ConanException(
                "upstream jwt-cli.bats suite did not fully pass: %d/%d cases "
                "failed" % (failed, len(cases)))

    # ── 打包 ──────────────────────────────────────────────────────────────
    def package(self):
        # 4 个工具（构建产物）
        for tool in UPSTREAM_TOOLS:
            copy(self, tool, src=self._tools_dir(),
                 dst=os.path.join(self.package_folder, "bin"))
        # 工具手册：上游 CMakeLists 无条件 install(tools/*.1 → man1)
        for man in sorted(glob.glob(os.path.join(self.source_folder,
                                                 "tools", "*.1"))):
            copy(self, os.path.basename(man), src=os.path.dirname(man),
                 dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 本包交付的是命令行工具；声明 bindirs 使消费者可经 Conan 的 bin
        # 目录拿到它们，并触发 R38 的 commands.json 校验（L0k）。
        self.cpp_info.bindirs = ["bin"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
        # 供消费者/CI 直接定位入口（先例 archives/b/babl-tools/0.1.126）
        self.conf_info.define("user.libjwt-tools:bin",
                              os.path.join(self.package_folder, "bin"))
        self.conf_info.define("user.libjwt-tools:exe",
                              os.path.join(self.package_folder, "bin",
                                           "jwt-verify"))
