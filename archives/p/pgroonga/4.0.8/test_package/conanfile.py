#!/usr/bin/env python3
"""pgroonga 4.0.8 test_package —— 在 OHOS aarch64 + PostgreSQL 18.3 上真机验证。

三层验证，全部在 test() 里跑：

  1) **静态布局 / 自包含性**
     - 7 个 shared module（pgroonga 主体 + check/database/crash_safer/
       standby_maintainer/wal_applier/wal_resource_manager）都落在**本包** lib/；
     - share/extension/ 下 control + 版本 SQL 齐备；
     - pgroonga.so 是 aarch64 ELF 共享对象；
     - **反向断言**：postgresql/18.3 包自身的 pkglibdir / sharedir/extension 里
       *不存在* pgroonga —— 证明产物落点确实是本包，靠
       extension_control_path / dynamic_library_path 被发现，
       而不是"装进 PG 安装目录"那条不可重定位的捷径。

  2) **行为断言**（test_package/assert_pgroonga.sql，psql -v ON_ERROR_STOP=1）
     启一个真实 PG 18.3 集群，跑 14 条断言：CREATE EXTENSION（$libdir 重定位）、
     版本、C 函数执行、groonga 引擎可达、probin 路径卫生、v1 全文检索、
     查询语法、pgroonga_score、v2 词项前缀、jsonb、highlight_html、
     query_extract_keywords、tokenize、DROP+CREATE 可逆性。
     走 self.run() 且 ON_ERROR_STOP → 断言失败直接让 conan create 失败。

  3) **上游 pg_regress 回归**
     vendored 的 sql/ + expected/ 全量实跑（钉版 1600 例中实跑 1598 例），
     仅排除 2 例需要
     OHOS groonga/16.0.8 未编入的 mecab / stem 外部插件的用例
     （清单见 test_package/regress-skip.txt）。pg_regress 的 _1/_2 备用
     oracle 会覆盖 PG 版本差异与环境差异。

为什么必须启真集群、而不能只做符号/ELF 检查：
pgroonga 是 PostgreSQL 的 **index access method**（`CREATE INDEX ... USING
pgroonga`）加一整套 `&@` / `&@~` / `&^` 运算符与 `pgroonga_*` 函数。这些既依赖
服务端头文件 ABI，也依赖运行期 dlopen 到包内 lib/pgroonga.so 后再去 dlopen
libgroonga.so。只有真集群跑起来、真建索引真查询，才能证明适配成立。

为什么用 TCP 而不是 Unix socket：
仓库打包的 postgresql/18.3 定义了 HAVE_NO_UNIX_SOCKETS（OHOS 无可靠的
AF_UNIX 服务端支持），所以必须 listen_addresses='localhost' + 显式端口，
pg_regress 也通过 --host/--port 连既有集群，不能用 --temp-instance。

为什么要把依赖的 .so 符号链接物化并重签：
groonga/16.0.8 包内的 `lib/libgroonga.so` 与 `lib/libgroonga.so.0` 只是指向
`libgroonga.so.0.0.0` 的符号链接 → PG 后端 dlopen `pgroonga.so` 时它的
DT_NEEDED `libgroonga.so.0` 加载失败（`Error loading shared library
libgroonga.so.0: (needed by ...)`，strerror 为空 = 找得到但载不进）。
只物化不够：随包带来的旧 `.codesign` 设备仍拒绝映射，必须丢掉后重签。
因此测试前把各依赖 libdir 顶层的符号链接展开成真文件副本、去 `.codesign`
再 `binary-sign-tool -selfSign 1`，放在 LD_LIBRARY_PATH 最前
（详见 `_stage_symlinked_libs`；A/B 实测见其 docstring）。
"""
import json
import os
import random
import re
import shutil
import stat
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException


# OHOS 侧工具：objcopy 去旧 .codesign、binary-sign-tool 就地重签。
# 路径同 archives/l/libratbag/0.18/test_package/conanfile.py（其重签方案已实测通过 CI）。
_HNP_BIN = "/data/service/hnp/bin"


def _ohos_sign_tools():
    """返回 (llvm-objcopy, binary-sign-tool) 的绝对路径，缺失即报错。

    宁可在这里给出明确诊断，也不要静默退回「只物化」，否则设备侧只会抛
    一条空 strerror 的 `Error loading shared library xxx.so.0`，很难定位。
    """
    objcopy = os.path.join(_HNP_BIN, "llvm-objcopy")
    signer = os.path.join(_HNP_BIN, "binary-sign-tool")
    for tool in (objcopy, signer):
        if not os.path.isfile(tool):
            raise ConanException("OHOS 签名工具缺失: %s" % tool)
    return objcopy, signer


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    _PG_REF = "postgresql/18.3"
    _PGROONGA_NAME = "pgroonga"
    _PGROONGA_VERSION = "4.0.8"

    # 上游 meson.build 里 7 个 shared_module（name_prefix=''，所以就叫 <name>.so）
    # 的清单与断言逻辑在 test_pgroonga.py（单一事实来源，避免两处漂移）。

    # assert_pgroonga.sql 里的断言条数（A1..A14）
    _ASSERTION_COUNT = 14

    # ── 依赖定位 ──────────────────────────────────────────────────────────
    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # 测试期要真的起一个 PG 服务端：initdb / pg_ctl / postgres / psql /
        # pg_regress 全在打包好的 postgresql/18.3 里。
        self.tool_requires(self._PG_REF)

    def _pkg(self):
        try:
            folder = self.dependencies[self._PGROONGA_NAME].package_folder
        except Exception as exc:
            raise ConanException("pgroonga 依赖未解析: %s" % exc)
        if not folder or not os.path.isdir(folder):
            raise ConanException("pgroonga package_folder 不可用: %r" % folder)
        return folder

    def _pg(self):
        try:
            folder = self.dependencies.build["postgresql"].package_folder
        except Exception as exc:
            raise ConanException("%s tool_requires 未解析: %s" % (self._PG_REF, exc))
        if not folder or not os.path.isdir(folder):
            raise ConanException("postgresql package_folder 不可用: %r" % folder)
        return folder

    def _collect_libdirs(self):
        """递归收集 host/build 两个上下文所有依赖的绝对 lib 目录。

        pgroonga.so 只在 DT_NEEDED 里记 libgroonga.so（无 rpath），libgroonga.so
        又依赖 lz4/zlib 等，所以服务端进程必须靠 LD_LIBRARY_PATH 才能把它们
        全部找到。这里不写死包名，直接走依赖图，避免以后依赖增删漏配。
        """
        found = []

        def add(path):
            if not path:
                return
            path = os.path.normpath(path)
            if os.path.isdir(path) and path not in found:
                found.append(path)

        def walk(deps):
            for dep in deps.values():
                pkg_folder = dep.package_folder
                if not pkg_folder:
                    continue
                dirs = None
                try:
                    dirs = list(dep.cpp_info.aggregated_components().libdirs)
                except Exception:
                    dirs = None
                if not dirs:
                    try:
                        dirs = list(dep.cpp_info.libdirs)
                    except Exception:
                        dirs = ["lib"]
                for d in dirs:
                    add(d if os.path.isabs(d) else os.path.join(pkg_folder, d))
                try:
                    walk(dep.dependencies)
                except Exception:
                    pass

        for ctx in ("host", "build"):
            try:
                walk(getattr(self.dependencies, ctx))
            except Exception:
                pass
        return found

    def _groonga_plugins_dir(self, libdirs):
        """groonga 的插件目录。

        groonga 把「插件目录」在编译期烘焙成 <build_prefix>/lib/groonga/plugins，
        而 Conan 构建用的是临时 build 目录（实测 libgroonga.so 里硬编码的是
        /storage/Users/currentUser/.conan2/p/b/<hash>/p/lib/groonga/plugins），
        设备上不存在该路径。运行时用 GRN_PLUGINS_DIR 覆盖即可。
        """
        for d in libdirs:
            cand = os.path.join(d, "groonga", "plugins")
            if os.path.isdir(cand):
                return cand
        return None

    def _stage_symlinked_libs(self, libdirs, build_folder):
        """把依赖 libdir 里的 .so 符号链接物化成真文件副本，并**重签**。

        groonga/16.0.8 的包内 `lib/libgroonga.so` 与 `lib/libgroonga.so.0`
        都只是指向 `libgroonga.so.0.0.0` 的符号链接（conanmanifest.txt 里
        两者记的是**目标字符串**的 md5，可据此判定），于是 pgroonga.so 的
        DT_NEEDED `libgroonga.so.0` 在设备上加载失败：

            Error loading shared library libgroonga.so.0:
                (needed by .../p/lib/pgroonga.so)

        strerror 为空正是「文件找到了、但加载不了」的特征（找不到时 musl 会
        报 `No such file or directory`）。

        ★ 只做「物化」是不够的。同一批 PR 的 A/B 实测（2026-09-27）：
          - libratbag/0.18：物化 → CI 仍 FAIL；物化 **+ 重签** → CI PASS
            （同一个 PR 先 09:20 FAIL、09:37 推重签后 09:43 PASS）。
          - pgroonga/4.0.8 与 libgmobile/0.7.2、libgsystemservice/0.3.0
            只做物化，09:42~09:46 仍是同一条空 strerror FAIL。
        因此这里的做法是：把真文件复制进 staging 目录后，用
        `llvm-objcopy --remove-section .codesign` 丢掉随包带过来的旧签名，
        再用 `binary-sign-tool sign -selfSign 1` 就地重签（Conan 缓存保持
        只读，只动物化出来的副本）。同一写法见
        archives/l/libratbag/0.18/test_package/conanfile.py 与
        archives/g/gxr/0.15.1。

        staging 目录置于 LD_LIBRARY_PATH 最前，让加载器命中的是重签后的普通
        文件，而不是包内那个带旧签名的符号链接目标。
        """
        staged = os.path.join(build_folder, "staged-lib")
        if os.path.isdir(staged):
            shutil.rmtree(staged, ignore_errors=True)
        os.makedirs(staged, exist_ok=True)
        objcopy, signer = _ohos_sign_tools()
        materialized = []
        for libdir in libdirs:
            if not os.path.isdir(libdir):
                continue
            for name in sorted(os.listdir(libdir)):
                src = os.path.join(libdir, name)
                if not os.path.islink(src):
                    continue
                dst = os.path.join(staged, name)
                if os.path.exists(dst):
                    continue
                real = os.path.realpath(src)
                if not os.path.isfile(real):
                    continue
                # copy2 默认跟随符号链接 → 落下来的是真文件内容
                shutil.copy2(real, dst)
                os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR
                         | stat.S_IXGRP | stat.S_IXOTH)
                # 丢掉随包带来的旧签名后重签，否则设备仍拒绝映射（空 strerror）
                self.run('"%s" --remove-section .codesign "%s"' % (objcopy, dst))
                self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                         % (signer, dst, dst))
                materialized.append(name)
        if not materialized:
            return None
        self.output.info("E073: 物化并重签 %d 个符号链接库到 %s（%s）"
                         % (len(materialized), staged,
                            ", ".join(materialized)))
        return staged

    # ── 静态布局断言 ──────────────────────────────────────────────────────
    # 实现放在 test_pgroonga.py（独立可执行、也是 L0c 认得的测试源），
    # 这里只负责以子进程真跑它：非零退出即让 conan create 失败。
    def _run_layout_test(self, pkg, pg):
        script = os.path.join(os.path.dirname(__file__), "test_pgroonga.py")
        if not os.path.isfile(script):
            raise RuntimeError("test_pgroonga.py 缺失: %s" % script)
        self.run('"%s" "%s" "%s" "%s"' % (sys.executable, script, pkg, pg))

    # ── 集群生命周期 ──────────────────────────────────────────────────────
    def _build_env(self, pg, libdirs, build_folder):
        bindir = os.path.join(pg, "bin")
        tmpdir = os.path.join(build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = {
            "PATH": bindir + os.pathsep + os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", os.path.expanduser("~")),
            "TMPDIR": tmpdir,
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            "SHELL": os.environ.get("SHELL", "/bin/sh"),
            "LD_LIBRARY_PATH": os.pathsep.join(libdirs),
            "USER": "hmbstest",
            "LOGNAME": "hmbstest",
        }
        term = os.environ.get("TERM")
        if term is not None:
            env["TERM"] = term
        plugins = self._groonga_plugins_dir(libdirs)
        if plugins:
            env["GRN_PLUGINS_DIR"] = plugins
        return env

    def _write_auto_conf(self, pgdata, pkg, pg, port):
        """把集群参数写进 postgresql.auto.conf。

        listen_addresses/port：OHOS PG 无 Unix socket，只能 TCP。
        extension_control_path / dynamic_library_path：本适配的关键——
          把扩展发现路径指向 pgroonga 包（share 与 lib），后面接 PG 包自己的
          share/postgresql，否则 initdb 建的 plpgsql 也会找不到。
          注意 extension_control_path 收的是**基目录**（PG 会自行补 /extension），
          见下面函数体内的说明；dynamic_library_path 不收。二者语义不同。
        enable_partitionwise_join / max_prepared_transactions / random_page_cost：
          与 pgroonga 上游 CI 的 postgresql.conf 追加项保持一致，保证
          expected/*.out 里的计划与用法逐字节可比。
        """
        # ★ 这里必须是**父目录**，不能写 `share/extension`：PG 18 的
        # get_extension_control_directories()（src/backend/commands/extension.c）
        # 对列表中**每一个不是字面量 "$system" 的元素**都会再拼一层 "/extension"：
        #
        #     if (strcmp(piece, "$system") == 0)
        #         mangled = substitute_path_macro(piece, "$system", system_dir);
        #     else
        #         mangled = psprintf("%s/extension", piece);
        #
        # 而且 parse_extension_control_file() 里还有
        #     Assert(strcmp(control->control_dir + strlen(...) - 10, "/extension") == 0);
        # 即 PG 断言解析出来的目录必须以 /extension 结尾。
        # 所以写 `<pkg>/share/extension` 会让 PG 去搜
        # `<pkg>/share/extension/extension/pgroonga.control`（不存在）→
        # psql 报 `ERROR: extension "pgroonga" is not available`。
        # 正确写法是给**基目录**，由 PG 自己补 /extension。
        extension_control_path = ":".join([
            os.path.join(pkg, "share"),
            os.path.join(pg, "share", "postgresql"),
        ])
        dynamic_library_path = ":".join([
            os.path.join(pkg, "lib"),
            os.path.join(pg, "lib", "postgresql"),
            "$libdir",
        ])
        with open(os.path.join(pgdata, "postgresql.auto.conf"), "a",
                  encoding="utf-8") as fh:
            fh.write("listen_addresses = 'localhost'\n")
            fh.write("port = %d\n" % port)
            fh.write("extension_control_path = '%s'\n" % extension_control_path)
            fh.write("dynamic_library_path = '%s'\n" % dynamic_library_path)
            fh.write("enable_partitionwise_join = on\n")
            fh.write("max_prepared_transactions = 1\n")
            fh.write("random_page_cost = 0\n")
        return extension_control_path, dynamic_library_path

    @staticmethod
    def _tail(path, limit=1500):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read()[-limit:]
        except Exception:
            return ""

    def _run(self, cmd, env, cwd=None, timeout=600):
        return subprocess.run(cmd, capture_output=True, text=True, env=env,
                              cwd=cwd, timeout=timeout)

    # ── 上游回归：pg_regress ──────────────────────────────────────────────
    def _skip_set(self):
        path = os.path.join(os.path.dirname(__file__), "regress-skip.txt")
        names = set()
        if not os.path.isfile(path):
            return names
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                names.add(line.split()[0])
        return names

    def _write_schedule(self, upstream, schedule_path, outdir):
        """按上游 test/prepare.rb 的口径生成 pg_regress schedule。

        prepare.rb 用 ruby 递归遍历 sql/**.sql，每个生成一行 `test: <相对路径>`，
        并为每个目录级预建 results/<dir>。这里用 Python 复刻同一行为，
        从而在不引入 ruby 的前提下保持与上游完全一致的用例集合与目录结构。

        刻意**不做**任何"顺手过滤"：不筛 oracle 是否存在、不按 group 挑，
        唯一的删减就是 regress-skip.txt 里逐条写明原因的 2 例。oracle 缺失
        这类问题应当由 pg_regress 自己报失败，而不是在生成 schedule 时静默
        消失（否则会得到"跑得全绿但用例集缩水"的假绿）。排序只影响执行顺序，
        不改变集合。
        """
        skip = self._skip_set()
        sql_root = os.path.join(upstream, "sql")
        tests = []
        for dirpath, _dirnames, filenames in os.walk(sql_root):
            for fname in filenames:
                if not fname.endswith(".sql"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fname), sql_root)
                tests.append(rel.replace(os.sep, "/")[:-4])
        tests.sort()
        selected = [t for t in tests if t not in skip]

        lines = []
        for name in selected:
            # pg_regress 需要 results/<子目录> 已存在（上游 prepare.rb 显式 mkdir_p）
            results_dir = os.path.join(outdir, "results",
                                       os.path.dirname(name))
            if results_dir:
                os.makedirs(results_dir, exist_ok=True)
            lines.append("test: %s" % name)
        with open(schedule_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        return tests, selected

    def _run_pg_regress(self, pg, pkg, libdirs, env, build_folder):
        bindir = os.path.join(pg, "bin")
        pg_regress = os.path.join(pg, "lib", "postgresql", "pgxs", "src",
                                  "test", "regress", "pg_regress")
        if not os.path.isfile(pg_regress):
            return None
        upstream = os.path.join(pkg, "upstream")
        if not os.path.isdir(os.path.join(upstream, "sql")):
            return None

        outdir = os.path.join(build_folder, "regress")
        os.makedirs(outdir, exist_ok=True)
        upstream_copy = os.path.join(outdir, "upstream")
        # pg_regress 的 --inputdir 必须是可写的（它会往里写 results/），
        # 而 <pkg>/upstream 在 Conan cache 里只读 → 复制一份到 build 目录。
        if os.path.isdir(upstream_copy):
            shutil.rmtree(upstream_copy, ignore_errors=True)
        shutil.copytree(upstream, upstream_copy)

        schedule = os.path.join(outdir, "schedule.txt")
        total, selected = self._write_schedule(upstream_copy, schedule, outdir)
        if not selected:
            return None

        regress_env = dict(env)
        regress_env.update({
            "PGHOST": "localhost",
            "PGPORT": str(self._port),
            "PGUSER": "hmbstest",
            "PGDATABASE": "regression",
        })
        # 上游 meson.build:633 也传了 --launcher test/short-pgappname
        # （壳脚本，作用只是把 PGAPPNAME 钉成 pg_regress）。vendored 副本在
        # 上游 test/ 里，package() 已补回可执行位；找不到就退回默认行为，
        # 因为随包用例没有任何一条读 application_name / pg_stat_activity。
        launcher = os.path.join(upstream_copy, "test", "short-pgappname")
        cmd = [
            pg_regress,
            "--bindir", bindir,
            "--dlpath", os.path.join(pkg, "lib"),
            "--inputdir", upstream_copy,
            "--outputdir", outdir,
            "--host", "localhost",
            "--port", str(self._port),
            "--user", "hmbstest",
            "--dbname", "regression",
            "--load-extension", self._PGROONGA_NAME,
        ]
        if os.path.isfile(launcher):
            cmd += ["--launcher", launcher]
        cmd += ["--schedule", schedule]

        result = self._run(cmd, regress_env, cwd=outdir, timeout=3600)
        output = (result.stdout or "") + "\n" + (result.stderr or "")

        seen = {}
        for line in output.splitlines():
            m = re.match(r"^\s*test\s+(\S+)\s+\.\.\.\s+(ok|FAILED)\s*$",
                         line.strip())
            if m:
                seen[m.group(1)] = m.group(2)
        passed = [t for t in selected if seen.get(t) == "ok"]
        failed = [t for t in selected if seen.get(t) == "FAILED"]

        diffs = self._tail(os.path.join(outdir, "regression.diffs"), 4000)
        return {
            "total_in_tree": len(total),
            "selected": len(selected),
            "seen": len(seen),
            "passed": len(passed),
            "failed": len(failed),
            "failed_names": failed[:40],
            "exit": result.returncode,
            "log_tail": output[-2500:],
            "diff_tail": diffs,
        }

    # ── 主流程 ────────────────────────────────────────────────────────────
    def test(self):
        pkg = self._pkg()
        pg = self._pg()
        libdirs = self._collect_libdirs()
        build_folder = self.build_folder

        # libgroonga.so.0 是符号链接且带旧签名，设备载不进：物化成真文件
        # 副本 + 去 .codesign 重签，并置于 LD_LIBRARY_PATH 最前，
        # 见 _stage_symlinked_libs 的说明。
        staged = self._stage_symlinked_libs(libdirs, build_folder)
        if staged:
            libdirs.insert(0, staged)

        # ---- 0. 静态布局（真跑 test_pgroonga.py；非零退出即失败）----
        self._run_layout_test(pkg, pg)
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": True,
                "passed": True,
                "command": "package layout + live PG 18.3 cluster + pg_regress",
            }))

        # ---- 1. 起集群 ----
        bindir = os.path.join(pg, "bin")
        initdb = os.path.join(bindir, "initdb")
        pg_ctl = os.path.join(bindir, "pg_ctl")
        psql = os.path.join(bindir, "psql")
        for name, path in (("initdb", initdb), ("pg_ctl", pg_ctl), ("psql", psql)):
            if not os.path.isfile(path):
                raise RuntimeError("PostgreSQL server binary %s 缺失: %s"
                                   % (name, path))

        work = os.path.join(build_folder, "pg_cluster")
        pgdata = os.path.join(work, "pgdata")
        for d in (work, pgdata):
            os.makedirs(d, exist_ok=True)
        logfile = os.path.join(work, "postgresql.log")
        self._port = 49152 + random.randint(0, 9999)

        env = self._build_env(pg, libdirs, build_folder)
        self.output.info("LD_LIBRARY_PATH        = %s"
                         % env.get("LD_LIBRARY_PATH", ""))

        server_started = False
        try:
            r = self._run([initdb, "-D", pgdata, "--auth=trust",
                           "--no-instructions", "--user=hmbstest"],
                          env, timeout=300)
            if r.returncode != 0:
                raise RuntimeError("initdb 失败 (exit %d): %s"
                                   % (r.returncode, (r.stderr or r.stdout)[-1200:]))

            # auto.conf 必须等 initdb **之后**再写：initdb 拒绝在非空目录里建集群
            # （"directory ... exists but is not empty"），而它自己会往 pgdata 里写
            # postgresql.conf / pg_hba.conf / base/ 等。PG 读配置的顺序是
            # postgresql.conf → postgresql.auto.conf，所以先 initdb、后追加
            # auto.conf，参数照样生效（这也是 ALTER SYSTEM 的写入位置）。
            ctrl, dyn = self._write_auto_conf(pgdata, pkg, pg, self._port)
            self.output.info("extension_control_path = %s" % ctrl)
            self.output.info("dynamic_library_path   = %s" % dyn)

            r = self._run([pg_ctl, "-D", pgdata, "-l", logfile, "-w", "start"],
                          env, timeout=300)
            if r.returncode != 0:
                raise RuntimeError("pg_ctl start 失败 (exit %d): %s | log: %s"
                                   % (r.returncode,
                                      (r.stderr or r.stdout)[-600:],
                                      self._tail(logfile)))
            server_started = True
            self.output.info("PostgreSQL 18.3 集群已启动 (port %d)" % self._port)

            # ---- 2. 行为断言（ON_ERROR_STOP → 失败即 raise）----
            assert_sql = os.path.join(os.path.dirname(__file__),
                                      "assert_pgroonga.sql")
            if not os.path.isfile(assert_sql):
                raise RuntimeError("assert_pgroonga.sql 缺失: %s" % assert_sql)

            os.environ["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH"]
            os.environ["PATH"] = env["PATH"]
            os.environ["GRN_PLUGINS_DIR"] = env.get("GRN_PLUGINS_DIR", "")
            cmd = ('"%s" -X -q -v ON_ERROR_STOP=1 -h localhost -p %d '
                   '-U hmbstest -d postgres -f "%s"'
                   % (psql, self._port, assert_sql))
            try:
                self.run(cmd)
            except ConanException as exc:
                raise RuntimeError(
                    "pgroonga 行为断言失败（%d 条，见上方 psql 输出）: %s"
                    % (self._ASSERTION_COUNT, exc))
            self.output.info("行为断言 %d/%d 通过"
                             % (self._ASSERTION_COUNT, self._ASSERTION_COUNT))

            # ---- 3. 上游 pg_regress 全量回归 ----
            regress = self._run_pg_regress(pg, pkg, libdirs, env, build_folder)
        finally:
            if server_started:
                self._run([pg_ctl, "-D", pgdata, "-m", "fast", "stop"],
                          env, timeout=120)

        if regress is None:
            self.output.warning("未找到 pg_regress 或 vendored 上游用例，跳过回归")
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                    "status": "skipped",
                    "framework": "pg_regress",
                    "reason": "pg_regress/vendored upstream suite unavailable",
                }))
            return

        status = "failed" if regress["failed"] else "passed"
        reason = ("pg_regress: %d/%d passed, %d failed, %d unparsed"
                  % (regress["passed"], regress["selected"],
                     regress["failed"],
                     regress["selected"] - regress["seen"]))
        if regress["failed_names"]:
            reason += "; failed=%s" % ",".join(regress["failed_names"])
        self.output.info("pg_regress %s" % reason)
        if regress["diff_tail"]:
            self.output.info("regression.diffs tail:\n%s" % regress["diff_tail"])
        elif regress["log_tail"]:
            self.output.info("pg_regress log tail:\n%s" % regress["log_tail"])

        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": status,
                "framework": "pg_regress",
                "command": "pg_regress --load-extension pgroonga --schedule <generated>",
                "discovered": regress["total_in_tree"],
                "executed": regress["selected"],
                "passed": regress["passed"],
                "failed": regress["failed"],
                "skipped": regress["total_in_tree"] - regress["selected"],
                "reason": reason,
                "failed_names": regress["failed_names"],
            }))

        if regress["failed"]:
            raise RuntimeError(reason)
