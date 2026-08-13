#!/usr/bin/env python3
"""Conan recipe — Rizin v0.9.1 (Meson build system).

Rizin is a fork of radare2, a reverse engineering framework with command-line
tooling (rizin, rz-asm, rz-bin, rz-diff, rz-find, rz-gg, rz-hash, rz-run,
rz-sign, rz-test). Adapted to OpenHarmony PC (aarch64).

Adaptation notes (see notes.md for full details):
  1. librz/util/thread.c: guard pthread_setcancelstate/type with
     HAVE_PTHREAD_SETCANCELSTATE feature probe (R8-compliant; see patch 0003/0004;
     HarmonyOS bionic libc does not implement POSIX thread cancel API).
  2. librz/debug/meson.build: extend linux/android branch with 'harmonyos' so
     linux_debug.c/linux_coredump.c are compiled in.
     HarmonyOS native build reports host_machine.system()=='harmonyos'.
  3. OpenSSL disabled entirely (use_sys_openssl=disabled, not required):
     conancenter openssl/3.5.6 recipe rejects OHOS/armv8/clang ("Unsupported
     configuration"), and the OHOS toolchain has no published OHOS openssl.
     Rizin supports this out of the box: every openssl include is guarded by
     HAVE_LIB_SSL, and pure-C fallbacks exist (librz/util/big.c instead of
     big-ssl.c; librz/hash internal md4/md5/sha1/sha2/sm3 implementations).
     TLS support in rz_socket is compiled out — acceptable for the consumer
     test (rz_core API round-trip) and upstream unit/integration tests.
  4. v0.9.1 official release tarball (rizin-src-v0.9.1.tar.xz) already vendors
     subproject sources (capstone-next, pcre2-10.47, libdemangle, zydis, ...),
     so no git pre-clone is needed — meson resolves them from subprojects/ dirs.
  5. pcre2 JIT 不可用（真机实测）：ohpcd 预构建 pcre2/10.45.1 二进制不含 JIT
     （pcre2_jit_compile 返回 PCRE2_ERROR_JIT_BADOPTION、pcre2_jit_stack_create
     返回 NULL）。该环境的包 ID 按 settings-only 计算（file/pcre2/zlib 同 ID），
     conan 选项 support_jit 无法改变所选二进制，故改走上游同款排除法：补丁 0005
     把 'harmonyos' 加入 meson.build 的 SUPPORTS_PCRE2_JIT 排除列表（与
     darwin/serenity 一致），rizin 全部 regex 走 pcre2 解释器，上游测试语义不变。
  6. 上游 CI（ci.yml）先 `meson install`（--prefix=$HOME）再跑 meson test，主题/
     types sdb 等数据由此可达。本配方编译期 prefix 为 "/"（conan DESTDIR 打包），
     build() 内把 meson install 产物 stage 到可写目录并以 HOME=stage 运行测试，
     使 rz_path_home_prefix($HOME/.local/share/rizin) 命中主题，补齐 autocmplt 的
     eco 主题补全测试数据源。

Deps strategy ("only enable published" per W0/R36):
  use_sys_pcre2/libmagic/zlib/lz4/libzstd enabled (ohpcd published);
  use_sys_openssl disabled (no OHOS-compatible openssl on conancenter/ohpcd;
  rizin has pure-C fallbacks — see point 3);
  use_sys_capstone/libzip/xxhash/libmspack/tree_sitter/softfloat/liblzma
  disabled (use Rizin vendored Meson subprojects).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
import glob
import json
import os
import re
import shutil


class RizinConan(ConanFile):
    name = "rizin"
    version = "0.9.1"
    description = "Rizin is a fork of radare2, a reverse engineering framework with command-line tooling"
    license = "LGPL-3.0-only"
    homepage = "https://rizin.re"
    url = "https://github.com/rizinorg/rizin/releases/tag/v0.9.1"

    package_type = "application"
    build_system = "meson"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0/R36: only require ohpcd-published recipes.
        self.requires("pcre2/10.45.1")
        self.requires("file/5.48")        # provides libmagic.a / magic
        self.requires("zlib/1.3.1.1")     # PIC-enabled
        self.requires("lz4/1.10.0")
        self.requires("zstd/1.5.7")

    def configure(self):
        # OHOS libc 无 glibc 签名 qsort_r（dictBuilder/cover.c 引用），zstd CLI
        # （programs/zstd）真机链接报 undefined symbol: qsort_r。rizin 只经
        # pkg-config 使用 libzstd 库，不需要 zstd 命令行程序；关闭 build_programs
        # 仅构建 libzstd_static（该目标真机已验证构建成功），同时避免链接失败。
        self.options["zstd"].build_programs = False
        # pcre2 JIT：ohpcd 预构建 pcre2/10.45.1 二进制不含 JIT（真机实测
        # pcre2_jit_compile 返回 "bad JIT option"、pcre2_jit_stack_create 返回
        # NULL → rz_regex_new_multi 返回 NULL → 字符串搜索集合 add 失败）。本环境
        # 包 ID 按 settings-only 计算，support_jit 选项无法改变所选二进制，故不再
        # 设置；改用补丁 0005 把 'harmonyos' 加入 SUPPORTS_PCRE2_JIT 排除列表，
        # rizin 全量 regex 走 pcre2 解释器（上游 darwin/serenity 同款做法）。

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # v0.9.1 release tarball vendors subproject sources under subprojects/
        # (capstone-next, pcre2-10.47, libdemangle, zydis, softfloat, ...).
        # sigdb.wrap is a git-form wrap but is only installed when present;
        # meson does not resolve it as a build dependency, so no pre-clone.
        # 上游测试数据：官方源码包不含 test/bins（test/README.md：样本取自
        # rizinorg/rizin-testbins，CI 为 `git clone rizin-testbins test/bins`）。
        # integration 测试以 test/ 为 workdir 打开 "bins/..."，缺数据即失败；
        # 此处把固定提交（85a4965）的 testbins 归档解到 test/bins（仓库根目录
        # 即 bins 内容：elf/ firmware/ pe/ pdb/ arm/ ...）。
        tb = self.conan_data["test_bins"]
        # codeload 的 /tar.gz/<commit> URL basename 是 commit hash，无扩展名；
        # Conan get() 此时按 URL basename 存盘，unzip 因后缀不匹配落入 zipfile
        # 分支 → BadZipFile（真机预检实测）。显式 filename 以 .tar.gz 结尾，
        # 让 unzip 走 tar 分支（sha256 校验不变，归档内容与官方完全一致）。
        get(self, url=tb["url"], sha256=tb["sha256"], filename="rizin-testbins.tar.gz",
            destination=os.path.join(self.source_folder, "test", "bins"), strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: non-system-name libs default dynamic; Conan manages dep chain.
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Only enable use_sys_* for published deps; vendored for the rest.
        tc.project_options["use_sys_pcre2"] = "enabled"
        tc.project_options["use_sys_magic"] = "enabled"
        tc.project_options["use_sys_zlib"] = "enabled"
        tc.project_options["use_sys_lz4"] = "enabled"
        tc.project_options["use_sys_libzstd"] = "enabled"
        # openssl/3.5.6 (conancenter) rejects OHOS/armv8/clang and no OHOS
        # openssl is published; rizin ships pure-C fallbacks (big.c, internal
        # md4/md5/sha1/sha2/sm3) so the whole feature is disabled.
        tc.project_options["use_sys_openssl"] = "disabled"
        tc.project_options["use_sys_capstone"] = "disabled"
        tc.project_options["use_sys_libzip"] = "disabled"
        tc.project_options["use_sys_lzma"] = "disabled"
        tc.project_options["use_sys_xxhash"] = "disabled"
        tc.project_options["use_sys_libmspack"] = "disabled"
        tc.project_options["use_sys_tree_sitter"] = "disabled"
        tc.project_options["use_sys_softfloat"] = "disabled"
        tc.generate()
        # OHOS conan lacks MesonDeps; use PkgConfigDeps so meson's dependency('libpcre2-8')
        # etc. resolve via pkg-config. PkgConfigDeps writes .pc into generators_folder.
        PkgConfigDeps(self).generate()
        # meson.build looks up deps by names Conan doesn't emit: create alias .pc files.
        import re
        pc_dir = self.generators_folder
        if pc_dir and os.path.isdir(pc_dir):
            aliases = {
                "libpcre2-8": "pcre2",    # meson: dependency('libpcre2-8')
                "libmagic":   "file",     # meson: dependency('libmagic')
                "liblz4":     "lz4",      # meson: dependency('liblz4')
            }
            for alias, real in aliases.items():
                real_pc = os.path.join(pc_dir, real + ".pc")
                alias_pc = os.path.join(pc_dir, alias + ".pc")
                if os.path.isfile(real_pc) and not os.path.isfile(alias_pc):
                    with open(real_pc) as fr:
                        body = fr.read()
                    body = re.sub(r"^Name:.*$", "Name: " + alias, body, count=1, flags=re.MULTILINE)
                    with open(alias_pc, "w") as fw:
                        fw.write(body)

    def build(self):
        apply_conandata_patches(self)
        # Inject wrap_mode into native.ini [built-in options] section.
        # wrap_mode is a meson built-in (not project) option; use 'default' so meson
        # auto-falls back to vendored subprojects (has_buildfile() returns early).
        native_ini = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.isfile(native_ini):
            with open(native_ini) as f:
                content = f.read()
            import re
            content = re.sub(r"^wrap_mode\s*=.*\n", "", content, flags=re.MULTILINE)
            marker = "[built-in options]\n"
            inject = "wrap_mode = 'default'\n"
            if "wrap_mode = 'default'" not in content:
                if marker in content:
                    content = content.replace(marker, marker + inject, 1)
                else:
                    content = marker + inject + "\n" + content
            with open(native_ini, "w") as f:
                f.write(content)
        # Conan's MesonToolchain omits ar/ranlib/strip/ld from [binaries]; register an
        # EXTRA machine file via Conan's conf mechanism (extra_machine_files) so meson
        # finds the absolute HNP tool paths.
        extra_ini_path = os.path.join(self.generators_folder, "ohos_extra_binaries.ini")
        hnp_bin = os.environ.get("HNP_BIN_DIR", "/data/service/hnp/bin")
        extra_ini_content = (
            "[binaries]\n"
            "ar = '" + hnp_bin + "/llvm-ar'\n"
            "ranlib = '" + hnp_bin + "/llvm-ranlib'\n"
            "strip = '" + hnp_bin + "/llvm-strip'\n"
            "ld = '" + hnp_bin + "/ld.lld'\n"
        )
        os.makedirs(os.path.dirname(extra_ini_path), exist_ok=True)
        with open(extra_ini_path, "w") as f:
            f.write(extra_ini_content)
        conf_key = "tools.meson.mesontoolchain:extra_machine_files"
        existing = self.conf.get(conf_key, default=[], check_type=list)
        if extra_ini_path not in existing:
            existing.append(extra_ini_path)
        self.conf.define(conf_key, existing)
        meson = Meson(self)
        meson.configure()
        meson.build()

        # ── 上游测试数据供给（镜像上游 ci.yml 的 "Install with meson" 步骤）────
        # 上游 CI：meson setup --prefix=$HOME && ninja install 后才跑 meson test，
        # 主题（share/rizin/cons）与 types sdb 等数据经 RZ_PREFIX 可达。本配方
        # 编译期 prefix 为 "/"（conan 以 DESTDIR=package_folder 打包），故把
        # meson install 产物 stage 到可写目录，并以 HOME={stage} 运行测试：
        # rz_path_home_prefix → $HOME/.local/share/rizin（.local 前缀），经
        # 符号链接指向 {stage}/share/rizin，autocmplt 的 eco 主题补全测试即可
        # 枚举到主题（首个为 ayu）。仅服务测试期数据可达，不改变打包布局。
        stage_dir = os.path.join(self.build_folder, "rzstage")
        self.run('meson install -C "{}" --destdir "{}"'.format(self.build_folder, stage_dir),
                 ignore_errors=True)
        home_rz = os.path.join(stage_dir, ".local", "share", "rizin")
        if not os.path.lexists(home_rz):
            os.makedirs(os.path.dirname(home_rz), exist_ok=True)
            try:
                os.symlink(os.path.join("..", "..", "share", "rizin"), home_rz)
            except OSError:
                pass

        # ── 上游官方测试（TEST_QUALITY_SPEC §3 层 1）─────────────────────────
        # rizin v0.9.1: enable_tests 默认 true，meson test 驱动 test/unit（137 个
        # 测试目标）+ test/integration。真机（OHOS aarch64）上 lld 链接时即写入
        # .codesign，测试二进制可直接执行（与 glib 2.84.0.1 同款：build() 内直接
        # 跑 meson test，install 前无需重签）。--timeout-multiplier=16 与真机同源。
        # 末尾产出 HMBS_UPSTREAM_TEST_RESULT 硬门禁标记，数字解析自 meson 框架
        # summary 输出（非硬编码）。
        log_path = os.path.join(self.build_folder, "meson_test.log")
        # 真机 meson 是 pip --user 安装（~/.local/bin/meson），其 Python 模块
        # mesonbuild 位于 ~/.local/lib/python*/site-packages。测试命令需要
        # HOME={stage} 让测试二进制经 rz_path_home_prefix 命中 stage 主题数据，
        # 但覆盖 HOME 后 meson 自身（pip --user 安装，随 HOME 解析用户
        # site-packages）会报 ModuleNotFoundError: No module named 'mesonbuild'
        # （真机预检实测，meson test 直接崩溃、discovered=0）。这里从 meson
        # 可执行文件位置推导其用户 site-packages（bin/ 的上一级 lib/python*），
        # 显式注入 PYTHONPATH：meson 仍可加载 mesonbuild，测试二进制照常继承
        # HOME={stage} 命中 stage 数据。
        user_site_dirs = []
        meson_exe = shutil.which("meson")
        if meson_exe:
            local_root = os.path.dirname(os.path.dirname(meson_exe))
            user_site_dirs = glob.glob(
                os.path.join(local_root, "lib", "python*", "site-packages"))
        py_path = ":".join(sorted(set(user_site_dirs)))
        # 测试二进制经 rz_path_system(RZ_SDB_TYPES) 解析 types sdb 数据目录：
        # 本配方 meson 编译期 --prefix=/，编译进二进制的前缀为 "/"，系统数据目录
        # 落在设备上不存在的 /share/rizin/types（上游 CI 用 --prefix=$HOME +
        # ninja install 所以可达）。此处注入 RZ_PREFIX={stage}（patch 0006 让
        # rz_path_prefix 优先读 RZ_PREFIX 环境变量），rz_path_system 即解析到
        # {stage}/share/rizin/types（stage 已含 meson install 全部 share 数据），
        # 修复 test_parse_dwarf_types（typedb 无基础类型致 union 解析失败）与
        # analysis_graph（printf 签名缺失致 format 参数检测不触发）。
        env_prefix = 'RZ_PREFIX="{}" HOME="{}"'.format(stage_dir, stage_dir)
        if py_path:
            env_prefix = 'PYTHONPATH="{}:${{PYTHONPATH}}" {}'.format(py_path, env_prefix)
        test_cmd = (
            '{} meson test -v -C "{}" --timeout-multiplier=16 '
            '--no-rebuild --print-errorlogs > "{}" 2>&1'
        ).format(env_prefix, self.build_folder, log_path)
        self.run(test_cmd, ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                out = f.read()
        # 测试框架真实输出回显到 conan 日志（CI L1c 痕迹 + 人工可查）。
        self.output.info("=== upstream meson test (tail) ===")
        for line in (out.splitlines() or [])[-25:]:
            self.output.info(line)
        # 回显失败用例的输出块（--print-errorlogs 已捕获到 meson_test.log），
        # 便于真机预检失败时直接看到断言级失败明细，而不仅是 summary 计数。
        lines = out.splitlines()
        for i, ln in enumerate(lines):
            if re.search(r"\bFAIL\b", ln) and re.search(r"^\s*\d+/\d+\s+", ln):
                block = [ln]
                for j in range(i + 1, min(i + 40, len(lines))):
                    nxt = lines[j]
                    if re.search(r"^\s*\d+/\d+\s+", nxt):
                        break
                    block.append(nxt)
                self.output.info("--- failed test detail ---")
                for bl in block:
                    self.output.info(bl)

        def _cnt(pat):
            m = re.search(pat, out, flags=re.MULTILINE)
            return int(m.group(1)) if m else 0

        ok = _cnt(r"^Ok:\s+(\d+)")
        exp_fail = _cnt(r"^Expected Fail:\s+(\d+)")
        fail = _cnt(r"^Fail:\s+(\d+)")
        unexp_pass = _cnt(r"^Unexpected Pass:\s+(\d+)")
        skipped = _cnt(r"^Skipped:\s+(\d+)")
        timeout = _cnt(r"^Timeout:\s+(\d+)")
        not_run = _cnt(r"^Not run:\s+(\d+)")
        executed = ok + exp_fail + fail + unexp_pass + skipped + timeout + not_run
        discovered = executed
        passed = ok
        gate_ok = (executed > 0 and fail == 0 and skipped == 0
                   and timeout == 0 and not_run == 0)
        ut_status = "passed" if gate_ok else "failed"
        ut_result = {
            "status": ut_status,
            "framework": "meson",
            "command": test_cmd,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": fail,
            "skipped": skipped,
            "expected_fail": exp_fail,
            "unexpected_pass": unexp_pass,
            "timeout": timeout,
            "not_run": not_run,
            "reason": "meson test 于 build() 真机执行 test/unit + test/integration"
                      "（enable_tests 默认开启），数字来自 meson 框架 summary 输出",
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result))

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = [
            "rz_core", "rz_main", "rz_config", "rz_cons", "rz_util",
            "rz_io", "rz_socket", "rz_bin", "rz_lang", "rz_asm", "rz_analysis",
            "rz_arch", "rz_bp", "rz_crypto", "rz_debug", "rz_egg", "rz_flag",
            "rz_hash", "rz_magic", "rz_reg", "rz_sign", "rz_syscall", "rz_type",
        ]
        self.cpp_info.includedirs = ["include/librz"]  # rz_core.h etc. live under p/include/librz/
        self.cpp_info.bindirs = ["bin"]
        # Command-line tools (R38 declared in archives/r/rizin/commands.json)
        self.cpp_info.exes = [
            "rizin", "rz-asm", "rz-ax", "rz-bin", "rz-diff", "rz-find",
            "rz-gg", "rz-hash", "rz-run", "rz-sign", "rz-test",
        ]
