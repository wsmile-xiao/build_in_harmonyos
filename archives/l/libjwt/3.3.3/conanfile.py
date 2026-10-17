#!/usr/bin/env python3
"""Conan recipe — libjwt 3.3.3 (CMake).

JWT C Library：C 语言实现的 JSON Web Token 生成/签名/校验库，支持 JWK/JWKS。
构建产物：共享库 libjwt.so、静态库 libjwt.a，以及 4 个命令行工具
（jwt-verify / jwt-generate / jwk2key / key2jwk）。

OHOS 适配要点（均为实测结论，详见 notes.md）：
  1. 依赖解析方式：上游 CMakeLists 用 pkg_check_modules()（pkg-config）而非
     find_package() 定位依赖 → generate() 必须启用 PkgConfigDeps 生成
     jansson.pc/openssl.pc/check.pc；CMakeToolchain 会自动把 generators 目录
     追加进 PKG_CONFIG_PATH，无需手工注入。
  2. 构建开关：上游 add_library(jwt SHARED) + add_library(jwt_static STATIC) 是
     无条件的，BUILD_SHARED_LIBS 完全不起作用 → 本配方不提供该无效开关，
     package_type 直接声明为 shared-library（对外主链接目标为 libjwt.so）。
  3. 上游测试：11 个 libcheck 单元测试套件。libcheck 用 P_tmpdir（OHOS 上被 libc
     定义为只读 erofs 的 /tmp）建 fork 通信临时文件，必须把优先级更高的 TEMP
     指到可写目录，见 _prepare_ohos_test_runtime()。
  4. 上游 add_test() 把解释器硬编码成 /bin/bash；OHOS 根文件系统只有 /bin/sh
     （bash 在 /data/service/hnp/bin/bash，非 FHS 路径）→ 本配方不使用 ctest，
     按 add_test() 的等价语义直接执行测试二进制。
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps

# 上游 CMakeLists.txt 在 WITH_TESTS=ON 且 pkg-config 找到 check>=0.9.10 时注册的套件
UPSTREAM_UNIT_TESTS = (
    "jwt_crypto",
    "jwt_jwks",
    "jwt_jwks_errors",
    "jwt_ec",
    "jwt_rsa",
    "jwt_hs",
    "jwt_builder",
    "jwt_checker",
    "jwt_flipflop",
    "jwt_claims",
    "jwt_security",
)

# tests/jwt-cli.bats 另有 9 个 bats 用例。上游 CMakeLists 用 find_program(bats) 探测，
# 探测不到即不注册该测试（上游的优雅降级）；镜像内没有 bats，故本配方不运行它。
UPSTREAM_BATS_SUITE = "jwt_cli"
UPSTREAM_BATS_CASES = 9


class LibjwtConan(ConanFile):
    name = "libjwt"
    version = "3.3.3"
    description = ("JWT C Library — JSON Web Token (JWT) creation, signing and "
                   "verification with JWK/JWKS support")
    license = "MPL-2.0"
    homepage = "https://libjwt.io"
    url = "https://github.com/benmcollins/libjwt"

    # 上游无条件产出共享库 jwt 与静态库 jwt_static，对外的标准链接目标是 libjwt.so
    # （上游自带的 libjwt.pc 也是 Libs: -ljwt）→ 对外声明为 shared-library。
    # 静态归档 libjwt.a 随包一并安装，但两者文件基名相同（均为 jwt），
    # 无法用 cpp_info.libs 区分，故不作为独立链接目标导出。
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # 上游硬依赖（CMakeLists 中 pkg_check_modules(... REQUIRED)）：
        #   jansson>=2.0（WITH_JSON_C=OFF 时的 JSON 后端）
        #   openssl>=3.0.0
        # 两版本均已发布到 ohpcd 制品仓（W0/R35 实测 conan download 通过）。
        self.requires("jansson/2.15.1.1")
        self.requires("openssl/3.5.6")

    def build_requirements(self):
        # 上游测试套件基于 libcheck。test_requires 不参与 package_id、
        # 不向下游传播，仅用于本包的编译期测试（与 fcft/3.3.3 同款处理）。
        self.test_requires("check/0.15.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # (1) 上游用 pkg_check_modules()，必须生成依赖的 .pc 文件；
        #     CMakeToolchain 会把 generators 目录注入 PKG_CONFIG_PATH。
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        # 显式钉死全部可选加密/JSON 后端，保证构建结果与依赖图一致、可复现。
        tc.variables["WITH_JSON_C"] = "OFF"      # 默认 OFF；显式声明避免误探测 json-c
        tc.variables["WITH_GNUTLS"] = "OFF"      # 默认 ON(auto)，OHOS 上不引入 gnutls 依赖
        tc.variables["WITH_MBEDTLS"] = "OFF"     # 默认 OFF
        tc.variables["WITH_LIBCURL"] = "OFF"     # 默认 OFF；开启会引入 libcurl
        tc.variables["WITH_KCAPI_MD"] = "OFF"    # 默认 OFF；Linux 内核 crypto API
        tc.variables["ENABLE_COVERAGE"] = "OFF"  # 覆盖率会把 check 变成 REQUIRED
        # 不要设置 BUILD_SHARED_LIBS：上游对该变量无任何分支
        # (2) HarmonyOS 平台模块缺失补偿 —— 两处必须同时给，缺一不可：
        #     CMake 没有 Modules/Platform/HarmonyOS.cmake，所以
        #     CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG 不会在 Platform/Linux.cmake 里被赋值。
        #     而该变量正是 cmGeneratorTarget::HasSOName() 的判据，于是：
        #       a) 变量为空 → 链接期不发 -soname → libjwt.so 没有 DT_SONAME
        #          （L5a 门禁失败），且 CMakeDeps 生成 IMPORTED_NO_SONAME TRUE（L5c 失败）；
        #       b) 只补该变量 → CMake 立即启用 SONAME 语义；上游 jwt 目标声明了
        #          VERSION/SOVERSION，产物随即变成 libjwt.so.14.2.7 + 两级版本化符号
        #          链接链，而 HMDFS 上版本化符号链接无法创建/替换（实测
        #          cmake_symlink_library 报 "failed to create symbolic link
        #          'libjwt.so.14': Permission denied"，链接步骤 Error 1）。
        #     故必须再显式关闭版本化命名，让平台产出「实体文件 libjwt.so +
        #     可重定位 SONAME」，与 expat/2.8.4、libharu/2.3.0、attica/6.14.0 同款处理。
        #     依据：knowledge/drafts/DRAFT-cmake-harmonyos-platform-soname-flag.md
        #           archives/l/libevent/2.1.13/patches/0001-cmake-ohos-unversioned-shared-libraries.patch
        #           （libevent 注释原文：HMDFS cannot reliably create or replace the
        #             versioned symlink chain. Emit the public unversioned library
        #             as the real file.）
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 上游用 add_custom_command(COMMAND bash -c "...") 预处理 jwt-common.c 生成
        # jwt-builder.i / jwt-checker.i（被 jwt-builder.c / jwt-checker.c #include）。
        # 在 OHOS 上，conan 的 self.run()（musl python + shell=True）驱动
        # `cmake --build -jN`（N>1）时，make 的 jobserver 并行 spawn clang 子进程会静默失败
        # （Error 1 且无任何编译器输出；失败点随并行调度漂移：codegen→任意 .c.obj）。
        # 手动 `make -j1` / 直接 subprocess 执行同一命令 100% 成功，故根因是
        # jobserver 在 musl 进程树下的并行 spawn 竞态（详见 notes.md）。
        # 规避：
        #   (1) 预生成两个 .i，跳过 make 的 codegen 步骤；
        #   (2) 不用 conan 的 cmake.build()（会注入 -j<cpu_count> 并行），改用
        #       subprocess 直接 `make -j1` 串行编译，彻底绕开 jobserver 竞态。
        # 本库编译量小（11 测试 + 2 库 + 4 工具），-j1 代价可忽略，换取确定性。
        self._pregen_codegen_files(cmake)
        self._make_serial_build()
        self._run_upstream_tests()

    def _sdk_llvm_libdir(self):
        """返回 OHOS SDK 编译器的 llvm/lib 目录（含 lld 运行时依赖的
        libxml2.so.16）。

        OHOS SDK 的 lld 链接器动态链接 libxml2.so.16（interp 为 musl ld.so，
        RUNPATH 为 $ORIGIN/../lib 即 SDK 的 llvm/lib）。本配方用 subprocess 直接
        调 make 绕开了 conan 的 buildenv 激活，故需在此显式把 llvm/lib 前置到
        LD_LIBRARY_PATH，否则 CI worker 上链接 libjwt.so 会报
        "Error loading shared library libxml2.so.16 ... symbol not found"
        （详见 knowledge E120/E132/E341，及 abr2gbr/abseil/absl 同款先例）。
        """
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or compilers.get("cpp") or "/data/service/hnp/bin/clang"
        cc_real = os.path.realpath(cc)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        return llvm_lib if os.path.isdir(llvm_lib) else ""

    def _make_serial_build(self):
        """串行 make（-j1），绕开 OHOS/musl 下 make jobserver 的并行 spawn 竞态。

        不调用 cmake.build()：它会按 tools.build:jobs（默认 cpu_count）注入 -jN，
        触发 jobserver 并行竞态。这里直接 subprocess 跑 `make -j1`（绝对路径），
        与手动验证 100% 通过的方式一致。

        同时把 SDK llvm/lib 前置进 LD_LIBRARY_PATH（lld 链接器的 libxml2.so.16
        运行时依赖），弥补 subprocess 绕过 conan buildenv 造成的 env 缺失。
        """
        make = "/data/service/hnp/bin/make"
        cmd = [make, "-j1"]
        self.output.info("OHOS serial build: %s" % " ".join(cmd))
        env = os.environ.copy()
        sdk_ld = self._sdk_llvm_libdir()
        if sdk_ld:
            old_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(
                p for p in (sdk_ld, old_ld) if p)
            self.output.info("OHOS build LD_LIBRARY_PATH=%s" % env["LD_LIBRARY_PATH"])
        proc = subprocess.run(cmd, cwd=self.build_folder, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True)
        # make 输出实时透传（build 日志较长，逐行打印便于定位）
        if proc.stdout:
            for line in proc.stdout.splitlines():
                self.output.info(line)
        if proc.returncode != 0:
            raise ConanException("make -j1 build failed rc=%d" % proc.returncode)

    def _pregen_codegen_files(self, cmake):
        """预生成 jwt-builder.i / jwt-checker.i，绕开 make 并行 codegen 的
        musl spawn 竞态（OHOS 特有问题）。

        上游 CMakeLists 的 codegen 命令（补丁后等价形式）：
            ${CMAKE_C_COMPILER} -E -D<JWT_BUILDER|JWT_CHECKER> \
                ${CMAKE_SOURCE_DIR}/libjwt/jwt-common.c -o jwt-<builder|checker>.i
        输出落在 build_folder/build/Release（cmake_layout 的 Release 子目录），
        即 cmake.build() 的 cwd；.i 被 jwt-builder.c / jwt-checker.c 从同一目录 include。
        """
        compiler = "/data/service/hnp/bin/clang"
        src = os.path.join(self.source_folder, "libjwt", "jwt-common.c")
        # cmake_layout 下 self.build_folder 即 cmake 的实际输出根
        # （build/Release），.i 由 make 在该目录内生成并被同目录的
        # jwt-builder.c / jwt-checker.c include。
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
                raise ConanException(
                    "pregen %s failed rc=%d:\n%s"
                    % (out_name, proc.returncode, proc.stdout or ""))

    # ── 上游测试 ──────────────────────────────────────────────────────────
    def _run_upstream_tests(self):
        """运行上游 libcheck 单元测试套件并打印 HMBS_UPSTREAM_TEST_RESULT。

        不使用 ctest：上游 add_test() 把解释器硬编码为 /bin/bash，OHOS 根文件系统
        只有 /bin/sh。本方法按上游 add_test() 的等价语义逐个执行测试二进制：

            export TEST=<suite>; . <src>/tests/test-env.sh; exec <build>/tests/<suite>

        测试套件未通过时抛异常，避免"编译过但测试红"流入 CI。
        """
        tests_dir = self._find_tests_dir()
        bash = self._find_shell()

        # 测试期临时改动进程环境（TEMP/TMPDIR/TMP/LD_LIBRARY_PATH）；
        # 必须在 finally 中还原：conan 在同一个进程里接着跑 test_package，
        # 残留的 TMPDIR 会让后续 make 把 jobserver fifo 建到本包的构建目录
        # （实测报 "make: jobserver mkfifo ... Operation not permitted"）。
        _ENV_KEYS = ("TEMP", "TMPDIR", "TMP", "LD_LIBRARY_PATH")
        _saved_env = {k: os.environ.get(k) for k in _ENV_KEYS}
        try:
            self._prepare_ohos_test_runtime(tests_dir)
            results, checks_total, checks_failed, checks_errors, passed, failed = \
                self._execute_test_suites(tests_dir, bash)
        finally:
            for k, v in _saved_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        status = "passed" if failed == 0 else "failed"
        marker = {
            "status": status,
            "framework": "check",
            "command": ("export TEST=<suite>; . tests/test-env.sh; exec tests/<suite> "
                        "(ctest 不可用: 上游 add_test 硬编码 /bin/bash, OHOS 无此路径)"),
            "discovered": len(UPSTREAM_UNIT_TESTS),
            "executed": len(UPSTREAM_UNIT_TESTS),
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "checks_total": checks_total,
            "checks_failed": checks_failed,
            "checks_errors": checks_errors,
            "suites": results,
            "not_registered": {
                UPSTREAM_BATS_SUITE: {
                    "cases": UPSTREAM_BATS_CASES,
                    "reason": "bats 未随镜像提供；上游 CMakeLists 用 find_program(bats) "
                              "探测，探测不到即不注册该测试（上游优雅降级），非配方裁剪",
                }
            },
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if status != "passed":
            raise ConanException(
                "upstream libjwt test suite did not fully pass: %d/%d suites passed, "
                "%d checks failed, %d checks errored"
                % (passed, len(UPSTREAM_UNIT_TESTS), checks_failed, checks_errors)
            )

    def _execute_test_suites(self, tests_dir, bash):
        """逐套件执行测试二进制，返回 (results, checks_total, checks_failed,
        checks_errors, passed_suites, failed_suites)。"""
        results = []
        checks_total = checks_failed = checks_errors = 0
        passed = failed = 0

        for suite in UPSTREAM_UNIT_TESTS:
            binary = os.path.join(tests_dir, suite)
            if not os.path.isfile(binary):
                raise ConanException(
                    "upstream test executable missing: %s "
                    "(check 未被 pkg-config 找到？WITH_TESTS 未生效？)" % binary
                )
            # 与上游 add_test() 完全同形：先设 TEST，再 source test-env.sh
            cmd = ("export TEST=%s; . %s/tests/test-env.sh; exec %s"
                   % (suite, self.source_folder, binary))
            proc = subprocess.run(
                [bash, "-c", cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, cwd=self.build_folder, timeout=1800)
            out = proc.stdout or ""
            m = re.search(r"Checks:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)", out)
            n = int(m.group(1)) if m else 0
            f = int(m.group(2)) if m else 0
            e = int(m.group(3)) if m else 0
            checks_total += n
            checks_failed += f
            checks_errors += e
            ok = (proc.returncode == 0 and f == 0 and e == 0 and n > 0)
            passed += 1 if ok else 0
            failed += 0 if ok else 1
            results.append({"suite": suite, "rc": proc.returncode,
                            "checks": n, "failures": f, "errors": e,
                            "result": "PASS" if ok else "FAIL"})
            self.output.info("  [%-4s] %-18s rc=%d checks=%d failures=%d errors=%d"
                             % (results[-1]["result"], suite, proc.returncode, n, f, e))
            if not ok:
                self.output.error("=== %s output tail ===\n%s" % (suite, out[-2000:]))
        return results, checks_total, checks_failed, checks_errors, passed, failed

    def _find_tests_dir(self):
        """定位上游测试二进制目录（CMakeLists: RUNTIME_OUTPUT_DIRECTORY <bin>/tests）。"""
        direct = os.path.join(self.build_folder, "tests")
        if os.path.isdir(direct):
            return direct
        for root, _dirs, files in os.walk(self.build_folder):
            if UPSTREAM_UNIT_TESTS[0] in files:
                return root
        raise ConanException("upstream test binaries not found under %s"
                             % self.build_folder)

    @staticmethod
    def _find_shell():
        """选一个可用的 POSIX shell 来复现上游 add_test() 的 `. test-env.sh` 语义。

        /bin/sh 在 OHOS 上恒存在；CONFIG_SHELL（profile buildenv 注入）指向
        /data/service/hnp/bin/bash。两者都可 source test-env.sh（纯 POSIX 语法）。
        """
        for candidate in (os.environ.get("CONFIG_SHELL"), "/data/service/hnp/bin/bash",
                          "/bin/sh"):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "sh"

    def _prepare_ohos_test_runtime(self, tests_dir):
        """OHOS 测试运行时前置（不跳过任何测试用例）。

        [readonly_tmp] libcheck 选择临时目录的优先级是
            TEMP → P_tmpdir 宏 → TMPDIR → 当前目录
        （check-0.15.2/src/check_msg.c）。OHOS 的 libc 把 P_tmpdir 定义为 /tmp，
        而 /tmp 是只读 erofs（"Read-only file system"）→ TEMP/TMPDIR 若不同时设，
        libcheck 仍会去 /tmp 建 fork 通信临时文件，导致每个套件在 core_setup()
        前就 abort：
            "Unable to create temporary file for communication"
        故这里把 TEMP/TMPDIR/TMP 全部钉到构建目录下的可写路径（TEMP 优先级最高）。

        [runtime_lib_path] 测试二进制链接的是构建树里尚未安装的 libjwt.so，
        而 OHOS 加载器解析依赖包产物不依赖二进制内嵌的 DT_RPATH（见 knowledge E505），
        故把测试目录、构建目录与各依赖 libdir 放进 LD_LIBRARY_PATH 保证可加载。
        """
        tmpdir = os.path.join(self.build_folder, "hmbs-tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for key in ("TEMP", "TMPDIR", "TMP"):
            os.environ[key] = tmpdir

        libdirs = [tests_dir, self.build_folder]
        for dep in self.dependencies.values():
            pkgdir = dep.package_folder
            if not pkgdir or not os.path.isdir(pkgdir):
                continue
            for sub in ("lib", "lib64"):
                d = os.path.join(pkgdir, sub)
                if os.path.isdir(d) and d not in libdirs:
                    libdirs.append(d)
        old = os.environ.get("LD_LIBRARY_PATH", "")
        if old:
            libdirs.append(old)
        os.environ["LD_LIBRARY_PATH"] = ":".join(libdirs)
        self.output.info("OHOS test LD_LIBRARY_PATH=%s" % os.environ["LD_LIBRARY_PATH"])
        self.output.info("OHOS test temp dir=%s" % tmpdir)

    # ── 打包 ──────────────────────────────────────────────────────────────
    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游 lib/ 下同时有 libjwt.so 与 libjwt.a（同为 OUTPUT_NAME jwt），
        # 对外主链接目标为共享库，故 libs=["jwt"]。
        self.cpp_info.libs = ["jwt"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # 包内确实安装了 4 个命令行工具（bin/jwt-verify 等），声明 bindirs
        # 使消费者能通过 Conan 的 bin 目录拿到它们，并触发 R38 的
        # commands.json 校验（L0k）。
        self.cpp_info.bindirs = ["bin"]

        self.cpp_info.set_property("cmake_file_name", "libjwt")
        self.cpp_info.set_property("cmake_target_name", "libjwt::libjwt")
        self.cpp_info.set_property("pkg_config_name", "libjwt")

        # libjwt.so 的 DT_NEEDED 实测为 libjansson.so + libc.so：
        # OpenSSL 由 openssl/3.5.6 包提供的静态库（libcrypto.a/libssl.a）
        # 静态链入，不产生运行时动态依赖。
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
