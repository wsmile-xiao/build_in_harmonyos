#!/usr/bin/env python3
"""Conan recipe for astroterm 1.0.9 — Meson project.

astroterm is a terminal-based star map written in C, displaying real-time
positions of stars, planets, and constellations. Upstream uses the Meson build
system and depends on argtable3, ncurses, and the math library.

R26: Terminal tools must be statically linked for DevBox deployment.
The OHOS build uses official cmd-pkgs ncurses because CI workers do not ship
the corresponding development headers.

meson 获取策略：OHOS 真机与 CI worker 的 PATH 上均无 meson 可执行文件，且
ohpcd/conancenter 远端不存在可解析的 meson/1.11.0 工具包（连续多轮 conan
create 报 "Unable to find 'meson/1.11.0' in remotes"，依赖图阶段即失败）。
采用 libdvdnav/7.0.0 已验证的 vendored meson 方案：source() 直接下载官方
meson 1.11.2 源码到 source_folder/meson-vendor/，build() 经
`python3 -c` 在进程内 sys.path.insert 注入后调用 mesonmain.main()，
完全不依赖远端工具包。
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.meson import MesonToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class AstrotermConan(ConanFile):
    name = "astroterm"
    version = "1.0.9"
    description = (
        "A terminal-based star map written in C, displaying real-time positions "
        "of stars, planets, and constellations"
    )
    license = "MIT"
    homepage = "https://github.com/da-luce/astroterm"
    url = "https://github.com/da-luce/astroterm"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "res"),
            dst=os.path.join(self.export_sources_folder, "res"),
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        download(
            self,
            **self.conan_data["bsc5_source"],
            filename=os.path.join(self.source_folder, "data", "bsc5"),
        )
        get(
            self,
            **self.conan_data["argtable3_source"],
            destination=os.path.join(self.source_folder, "deps", "argtable3"),
            strip_root=True,
        )
        get(
            self,
            **self.conan_data["ncurses_ohos"],
            destination=os.path.join(self.source_folder, "deps", "ncurses-ohos"),
        )
        # vendored meson 构建工具源码（libdvdnav/7.0.0 已验证方案）：解压官方
        # meson 1.11.2 源码到 meson-vendor/，build() 时经 python3 进程内
        # sys.path 注入调用，替代 PATH 上的 meson 可执行文件。
        mv = os.path.join(self.source_folder, "meson-vendor")
        get(
            self,
            **self.conan_data["meson_source"],
            strip_root=True,
            destination=mv,
        )
        # Copy exported res/ (ncurses headers) into source folder so that
        # generate()/build() can reference res/ncurses/include consistently.
        # In Conan 2 cache builds the exported sources are already placed into
        # the source folder (export_sources_folder == source_folder), so the
        # copy must be skipped: copy() raises ConanException when src == dst.
        res_dst = os.path.join(self.source_folder, "res")
        if not os.path.isdir(res_dst):
            for src_base in (self.export_sources_folder, self.recipe_folder):
                if not src_base or not os.path.isdir(src_base):
                    continue
                res_src = os.path.join(src_base, "res")
                if os.path.isdir(res_src) and os.path.abspath(res_src) != \
                        os.path.abspath(res_dst):
                    copy(self, "*", src=res_src, dst=res_dst)
                    break

    # 真机 python3.12 运行 vendored meson 所需前缀（libdvdnav/facad notes 已验证）
    _PY_HOME = "/data/service/hnp/python.org/python_3.12"
    _PY_LIB = "/data/service/hnp/python.org/python_3.12/lib"

    def _meson_cmd(self, meson_argv):
        # 真机 HMBS_PYTHON3 的 site-packages 无 mesonbuild，且 Conan
        # self.run(env=list) 设的 PYTHONPATH 未传到子进程（sys.path 不含它）。
        # 故绕过 PYTHONPATH：用 `python3 -c` 脚本在进程内 sys.path.insert(0,
        # vendored meson) 再调 mesonmain.main()。mesonmain.main() 无参（读
        # sys.argv），argv 注入 sys.argv；sys.argv[0] 是程序名占位（meson
        # 跳过），真参数从 argv[1] 起——故前置 "meson" 占位。
        # argv 直接编成 Python list 字面量（json.dumps 产生合法 list literal）。
        py = os.environ.get("HMBS_PYTHON3") or "python3"
        mv = os.path.join(self.source_folder, "meson-vendor")
        argv_lit = json.dumps(["meson"] + list(meson_argv))
        mv_lit = json.dumps(mv)  # 合法 Python 字符串字面量："..."
        script = (
            "import sys;"
            f"sys.path.insert(0,{mv_lit});"
            f"sys.argv={argv_lit};"
            "from mesonbuild import mesonmain;"
            "rc=mesonmain.main();"
            "sys.exit(rc or 0)"
        )
        # 用单引号包住脚本（脚本内只有双引号字面量，无单引号，故单引号安全）
        return py, ["-c", f"'{script}'"]

    def _meson_env(self, extra=None):
        # Conan 2.x self.run(env=...) 要 list（["KEY=VALUE", ...]），不是 dict。
        env = {"PATH": os.environ.get("PATH", "")}
        mv = os.path.join(self.source_folder, "meson-vendor")
        pp = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (mv + ":" + pp).strip(":") if pp else mv
        # PYTHONHOME / LD_LIBRARY_PATH：真机 python3.12 需要（libdvdnav
        # notes #27/#28）。目录不存在时跳过（如 Linux 本机构建），不影响
        # OHOS 真机（目录存在，与 libdvdnav 已验证环境一致）。
        if os.path.isdir(self._PY_HOME):
            env["PYTHONHOME"] = self._PY_HOME
        ll = os.environ.get("LD_LIBRARY_PATH", "")
        if os.path.isdir(self._PY_LIB):
            env["LD_LIBRARY_PATH"] = (self._PY_LIB + ":" + ll).strip(":")
        # 保留真机注入的工具路径变量，供 ninja 调 meson 内部命令时用
        for k in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            if k in os.environ:
                env[k] = os.environ[k]
        if extra:
            env.update(extra)
        return [f"{k}={v}" for k, v in env.items()]

    def generate(self):
        tc = MesonToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.project_options["default_library"] = "static"
        if self.settings.os == "OHOS":
            ncurses_include = os.path.join(
                self.source_folder, "res", "ncurses", "include"
            ).replace("\\", "/")
            # Upstream public headers expose curses types to targets that do
            # not depend directly on the Meson curses dependency.
            tc.extra_cflags.extend(
                [f"-I{ncurses_include}", "-DNCURSES_WIDECHAR"]
            )
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("cpp") or executables.get("c") or ""
            bindir = os.path.dirname(compiler)
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                candidate_ranlib = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(candidate_ranlib):
                    ranlib = candidate_ranlib
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        binaries = "[binaries]\nar = '%s'\n" % ar
        if ranlib:
            binaries += "ranlib = '%s'\n" % ranlib
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", binaries, 1))

    def build(self):
        apply_conandata_patches(self)
        meson_file = os.path.join(self.source_folder, "meson.build")
        # argtable3 v3.3.1 是分模块库：官方 CMakeLists 编译 15 个 .c 模块
        # （arg_cmd/arg_date/arg_dbl/arg_dstr/arg_end/arg_file/arg_getopt_long/
        #  arg_hashtable/arg_int/arg_lit/arg_rem/arg_rex/arg_str/arg_utils/
        #  argtable3）。旧实现只把 argtable3.c 单文件编进 declare_dependency，
        # 链接时报 arg_dbl0/arg_str0/arg_end/argtable3_xmalloc/arg_dstr_* 等
        # 未定义符号（真机 ld.lld 日志实证）。改为在 source() 解包出的模块
        # 目录中动态收集全部 .c 模块，由 meson 一并编译进可执行文件。
        argtable_src = os.path.join(self.source_folder, "deps", "argtable3", "src")
        argtable_modules = sorted(
            name for name in os.listdir(argtable_src) if name.endswith(".c")
        )
        if not argtable_modules:
            raise ConanInvalidConfiguration(
                "no argtable3 module sources found in %s" % argtable_src
            )
        argtable_entries = ",\n".join(
            "            'deps/argtable3/src/%s'" % name for name in argtable_modules
        )
        replace_in_file(
            self,
            meson_file,
            "argtable = dependency('argtable3', required: false)",
            "argtable = declare_dependency(\n"
            "        sources: files(\n"
            f"{argtable_entries},\n"
            "        ),\n"
            "        include_directories: include_directories('deps/argtable3/src'),\n"
            "    )",
        )
        if self.settings.os == "OHOS":
            ncurses_include = os.path.join(
                self.source_folder, "res", "ncurses", "include"
            )
            ncurses_library = os.path.join(
                self.source_folder,
                "deps",
                "ncurses-ohos",
                "lib",
                "libncursesw.a",
            )
            for required_path in (ncurses_include, ncurses_library):
                if not os.path.exists(required_path):
                    raise ConanInvalidConfiguration(
                        f"required OHOS ncurses asset missing: {required_path}"
                    )
            ncurses_library = ncurses_library.replace("\\", "/")
            replace_in_file(
                self,
                meson_file,
                "curses = dependency('curses', required : true)",
                "curses = declare_dependency(\n"
                "        include_directories: include_directories('res/ncurses/include'),\n"
                f"        link_args: ['{ncurses_library}'],\n"
                "    )",
            )
        # 不用 Conan Meson 工具（裸名 `meson` 不在真机 PATH，且远端无 meson
        # 工具包可解析），改用 vendored meson 通过 `python3 -c` 脚本调
        # mesonmain.main(argv)，与 MesonToolchain 生成的 native file 配合。
        env = self._meson_env()
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        bdir = self.build_folder
        sdir = self.source_folder
        # configure（meson setup <source> <build> [options]），参数顺序沿用
        # libdvdnav 已验证写法（meson 1.11.2 自动识别 source/build 目录）。
        py, margs = self._meson_cmd(
            ["setup", sdir, bdir, "--prefix=/", "--native-file", nf]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=env)
        # build（ninja，真机注入 HMBS_NINJA 绝对路径）
        ninja = os.environ.get("HMBS_NINJA") or "ninja"
        self.run(f'"{ninja}" -C "{bdir}" -j1', env=env)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream meson test suite (Unity framework, 7 test
        executables: coord / astro / city / bit / core / stopwatch / drawing)
        and emit the HMBS_UPSTREAM_TEST_RESULT hard-gate marker. The counts
        come from the meson framework summary output (Ok:/Fail:/Skipped:),
        not from hardcoded values.
        """
        # drawing_test 的 newterm("xterm", ...) 需要 terminfo 数据库：
        # cmd-pkgs ncurses-6.4-ohos 包自带 share/terminfo（含 x/xterm），而
        # OHOS 系统默认 terminfo 路径无该条目，newterm 返回 NULL，测试报
        # "Failed to create fake terminal"（drawing_test.c:413-419）。
        # 注意：Conan 2 self.run(env=...) 的 KEY=VALUE 列表传不到子进程
        # （本配方 _meson_cmd 注释与 acf-db/0.2.1 notes 均实证），所以不能
        # 依赖 _meson_env() 注入；改为进程级 os.environ，子进程必然继承。
        if self.settings.os == "OHOS":
            ti = os.path.join(
                self.source_folder, "deps", "ncurses-ohos", "share", "terminfo"
            )
            os.environ["TERMINFO"] = ti
            self.output.info(
                "TERMINFO set: %s (xterm entry exists: %s)"
                % (ti, os.path.isfile(os.path.join(ti, "x", "xterm")))
            )
        log_path = os.path.join(self.build_folder, "meson_test.log")
        # 实际执行的命令（含日志重定向），hmbs 要求 command 为真机真实命令
        py, margs = self._meson_cmd(
            ["test", "-v", "-C", self.build_folder,
             "--timeout-multiplier=16", "--no-rebuild", "--print-errorlogs"]
        )
        test_cmd = f'"{py}" {" ".join(margs)} > "{log_path}" 2>&1'
        self.run(test_cmd, env=self._meson_env(), ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("=== upstream meson test (tail) ===")
        for line in (out.splitlines() or [])[-25:]:
            self.output.info(line)

        def _cnt(pat):
            m = re.search(pat, out, flags=re.MULTILINE)
            return int(m.group(1)) if m else 0

        ok = _cnt(r"^Ok:\s+(\d+)")
        fail = _cnt(r"^Fail:\s+(\d+)")
        skipped = _cnt(r"^Skipped:\s+(\d+)")
        timeout = _cnt(r"^Timeout:\s+(\d+)")
        not_run = _cnt(r"^Not run:\s+(\d+)")
        executed = ok + fail + skipped + timeout + not_run
        discovered = executed
        passed = ok
        gate_ok = executed > 0 and fail == 0 and skipped == 0 \
            and timeout == 0 and not_run == 0
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
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result, ensure_ascii=False)
        )
        if ut_status != "passed":
            raise RuntimeError(
                "upstream meson tests failed: executed=%d failed=%d skipped=%d"
                % (executed, fail, skipped)
            )

    def package(self):
        # meson install（DESTDIR staging 到 package_folder）。
        # libdvdnav 经验：Conan self.run(env=...) 注入的 DESTDIR 环境变量未可靠
        # 到达 vendored meson install 子进程（真机日志证实 meson install 仍尝试
        # 写 /lib/...，触发只读文件系统）。故传 --destdir 为 CLI 标志
        # （minstall.py 优先读 option，不依赖 os.environ）。配合 setup 阶段的
        # --prefix=/，安装产物落到 package_folder/ 下。
        bdir = self.build_folder
        py, margs = self._meson_cmd(
            ["install", "-C", bdir, "--no-rebuild", "--destdir", self.package_folder]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=self._meson_env())
        # R26: avoid shipping shared libraries for terminal tools
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for root, _dirs, files in os.walk(lib_dir):
                for f in files:
                    if f.endswith((".so", ".la")) or ".so." in f:
                        os.remove(os.path.join(root, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
