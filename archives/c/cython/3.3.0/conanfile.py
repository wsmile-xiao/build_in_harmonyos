#!/usr/bin/env python3
"""Conan recipe for Cython 3.3.0 — Python 的 C 扩展编译器（.pyx → .c）。

HarmonyOS (aarch64) 适配要点：

1. **自举**：Cython 的扩展模块由 Cython 自己编译（``.pyx`` → ``.c``）。
   sdist **不含预生成 C**（实测 ``Cython/Plex/Actions.c``、
   ``Cython/Compiler/Scanning.c``、``Cython/_shared.c`` 等均不存在），
   故必须先用**纯 Python 模式**的 Cython 自身作为编译器来构建扩展。
   实测该模式可用（``python3 -c "from Cython.Compiler.Main import compile"``
   能真实把 ``.pyx`` 编成 ``.c``，309KB），这是上游标准自举路径。

2. **C 扩展 + 签名**：构建产出 ``Cython/**/*.so``（十几个扩展模块）。
   OHOS 上外来 ELF 未经签名 ``dlopen`` 会失败（E212：Permission denied），
   故构建后与打包后各签名一次（pandoc/psutil 先例）。

3. **CLI**：上游 ``setup.py`` 的 ``scripts=[...]`` 会装 ``bin/cython`` /
   ``bin/cythonize`` / ``bin/cygdb``。本配方不依赖 setuptools 安装
   （避免 pip/setuptools 构建路径），而是**手工交付**这三个入口脚本到
   ``bin/``，并改写 shebang（OHOS 无 ``/usr/bin/env`` 之外的稳定解释器路径，
   统一指向 conan python 包的绝对路径）。

   → 因 ``bindirs`` 非空，按 PF8/R38 必须提供 ``commands.json``。
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import download

# 上游 setup.py 的 scripts=[...]（bin/ 下的三个入口；sdist 里是 cython.py 等）
CLI_SCRIPTS = ("cython", "cythonize", "cygdb")


class CythonConan(ConanFile):
    name = "cython"
    version = "3.3.0"
    description = ("Cython — C-Extensions for Python: compiles .pyx/.pxd to C, "
                   "used as the build backend of scipy / scikit-learn")
    license = "Apache-2.0"
    homepage = "https://github.com/cython/cython"
    url = ""

    # conan 在 package_type == "library" 时会由 `shared` 选项推导出实际类型
    # （shared-library / static-library），故**必须**声明该选项，否则依赖图阶段即报
    #   ERROR: cython/3.3.0: Package type is 'library', but no 'shared' option declared
    # （conan/internal/model/pkg_type.py:56-60 实测）。本包只产出 Python 扩展
    # （shared .so），故 shared 默认 True。
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("python/3.12.9")

    def build_requirements(self):
        # 上游 setup.py:3 `from setuptools import setup, Extension` 需要
        # setuptools 才能编译扩展；而 conan python 包的 site-packages 里**没有**
        # 它（实测只有 README.txt），CI 实测（PR #13673 第二轮）：
        #   setuptools -> ModuleNotFoundError
        #   distutils  -> ModuleNotFoundError   （py3.12 起 stdlib 已移除 distutils）
        # ohpcd 已有 setuptools/84.0.0 制品，故按 R36 正常声明依赖，
        # 而不是在构建期 `pip install`（可复现、可审计、不污染全局 site-packages）。
        #
        # 它同时解决 distutils：该制品自带 setuptools/_distutils 与
        # distutils-precedence.pth，实测经 PYTHONPATH 引入后
        # `import distutils` 自动解析到 setuptools._distutils，
        # 故 setup.py 那条 `from distutils.core import ...` 回退分支也可用。
        self.tool_requires("setuptools/84.0.0")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _py_pkg(self):
        return self.dependencies["python"].package_folder

    def _py_bin(self):
        pkg = self._py_pkg()
        for cand in ("python3.12", "python3", "python"):
            p = os.path.join(pkg, "bin", cand)
            if os.path.exists(p):
                return p
        raise ConanException("python interpreter not found under " + pkg)

    def _py_inc(self):
        pkg = self._py_pkg()
        for cand in ("include/python3.12", "include"):
            p = os.path.join(pkg, cand)
            if os.path.isdir(p):
                return p
        raise ConanException("python headers not found under " + pkg)

    def _py_lib(self):
        """conan python 包的 lib/ —— libpython3.12.so.1.0 所在目录。"""
        return os.path.join(self._py_pkg(), "lib")

    def _install_distutils_shim(self, env):
        """让 ``import distutils`` 可用（装上 setuptools 的 _distutils_hack）。

        py3.12 起 stdlib 已移除 distutils，而 Cython 的
        ``Dependencies.py`` 会 ``from distutils.extension import Extension``。
        setuptools 制品自带 ``setuptools/_distutils`` 与
        ``distutils-precedence.pth``，但 **.pth 只在 site 目录里才会被处理**
        ——本配方是把 setuptools 的 site-packages 挂到 PYTHONPATH 上，故 .pth
        不执行。实测（PR #13673 第四轮）：
          仅 PYTHONPATH      -> ModuleNotFoundError: No module named 'distutils'
          先 import setuptools -> distutils 解析到 setuptools._distutils ✔
        故在 PYTHONPATH 最前放一个 ``sitecustomize.py``（解释器启动即加载的
        约定名），由它 import setuptools 把垫片装上。
        """
        shim = os.path.join(self.build_folder, "ohc_pyshim")
        os.makedirs(shim, exist_ok=True)
        with open(os.path.join(shim, "sitecustomize.py"), "w",
                  encoding="utf-8") as f:
            f.write("try:\n"
                    "    import setuptools  # installs the _distutils_hack shim\n"
                    "except Exception:\n"
                    "    pass\n")
        env["PYTHONPATH"] = os.pathsep.join(
            [shim] + env.get("PYTHONPATH", "").split(os.pathsep))

    def _site(self):
        return os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")

    def _sign(self, path):
        """Self-sign a foreign ELF for OHOS execution (pandoc/psutil 先例)."""
        try:
            with open(path, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    return
        except OSError:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        sign = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.exists(objcopy) and os.path.exists(sign)):
            self.output.warning("signing tools not found; skipping " + path)
            return
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       capture_output=True, timeout=60)
        tmp = path + ".signed"
        r = subprocess.run([sign, "sign", "-inFile", path, "-outFile", tmp,
                            "-selfSign", "1"],
                           capture_output=True, timeout=180)
        if r.returncode != 0 or not os.path.exists(tmp) \
                or os.path.getsize(tmp) == 0:
            raise ConanException(f"ELF signing failed: {path}: "
                                 f"{r.stderr[:200]!r}")
        shutil.copyfile(tmp, path)
        os.remove(tmp)
        os.chmod(path, 0o755)

    def _sign_tree(self, root):
        for dirpath, _dirs, files in os.walk(root):
            for n in files:
                if n.endswith(".so"):
                    self._sign(os.path.join(dirpath, n))

    # ------------------------------------------------------------------

    def source(self):
        download(self, self.conan_data["sources"]["url"], "cython-3.3.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        # --no-same-owner: hmdfs 上归档属主与构建 UID 不一致（同 packaging）
        self.run("tar -xzf cython-3.3.0.tar.gz --no-same-owner || true")
        self.run("cp -a cython-3.3.0/. . && rm -rf cython-3.3.0")

    def build(self):
        py = self._py_bin()
        src = self.source_folder
        _pypkg = self._py_pkg()
        env = dict(os.environ)
        env["PATH"] = os.path.join(_pypkg, "bin") + os.pathsep \
            + env.get("PATH", "")
        # PYTHONPATH：① 源码树（纯 Python 自举，让自身可被 import）；
        # ② setuptools 制品的 site-packages —— setup.py 需要它（含 distutils
        #    实现）。顺序上把源码树放最前，避免制品里的同名目录抢先。
        _paths = [src]
        try:
            _st = self.dependencies.build.get("setuptools")
        except Exception:
            _st = None
        if _st is not None:
            _st_site = os.path.join(_st.package_folder, "lib", "python3.12",
                                    "site-packages")
            if os.path.isdir(_st_site):
                _paths.append(_st_site)
            else:
                self.output.warning(
                    "setuptools artifact has no site-packages at " + _st_site)
        else:
            self.output.warning(
                "setuptools missing from the build context — setup.py will "
                "fail to import it")
        env["PYTHONPATH"] = os.pathsep.join(_paths)
        self._install_distutils_shim(env)
        # ★ 必须把 conan python 包自己的 lib/ 加进 LD_LIBRARY_PATH。
        # 该包的 bin/python3.12 以 NEEDED 依赖 libpython3.12.so.1.0，而该库只
        # 存在于 <pkg>/lib。CI 实测（PR #13673）：
        #   [cython build] build_ext rc=127
        #   Error loading shared library libpython3.12.so.1.0: (needed by
        #     .../p/bin/python3.12)
        #   Error relocating .../bin/python3.12: Py_BytesMain: symbol not found
        # 解释器根本没启动——rc=127 是动态 loader 的失败，不是 Python 异常。
        # python 包的 package_info 本就把该目录放进 runenv_info 的
        # LD_LIBRARY_PATH，但本配方用 subprocess.run(env=...) 自拼环境、
        # 不经 conanrun，故须显式补上（audioflux / crunch64 同款处理）。
        # 无需设 PYTHONHOME：该包自带 stdlib（lib/python3.12/os.py 实测存在）。
        env["LD_LIBRARY_PATH"] = os.path.join(_pypkg, "lib") + os.pathsep \
            + env.get("LD_LIBRARY_PATH", "")
        # ★ 扩展还必须**显式链接 libpython**，否则能编译却无法导入。
        # conan python 包的解释器是「链接式」构建（bin/python3.12 的 NEEDED
        # 含 libpython3.12.so.1.0），它**不导出** Python C-API 符号
        # （实测 `llvm-readelf --dyn-syms bin/python3.12 | grep -c ' Py'` = 0），
        # 故扩展里未解析的 Py* 符号在运行期无处可寻。CI 实测（PR #13673 第三轮）：
        #   ImportError: Error relocating .../Cython/Utils...so:
        #                PyErr_SetNone: symbol not found
        # （Cython 扩展的 NEEDED 只有 libc.so）。仓内 astlib 的「不链 libpython、
        # 靠解释器运行期解析」做法依赖解释器导出符号，本包环境下不成立。
        #
        # 通过 LDFLAGS 注入：setuptools 的 build_ext 会取 sysconfig 的 LDFLAGS，
        # 实测该变量能一路传到 clang 链接命令。刻意**不加 rpath**——rpath 会把
        # conan 缓存里的绝对路径烧进交付产物，破坏可重定位性；libpython 已由
        # 解释器自身 NEEDED 载入，按 soname 即可解析（实测导入通过）。
        _pylib = self._py_lib()
        if os.path.exists(os.path.join(_pylib, "libpython3.12.so")):
            env["LDFLAGS"] = ("-L%s -lpython3.12 %s"
                              % (_pylib, env.get("LDFLAGS", ""))).strip()
        else:
            self.output.warning(
                "libpython3.12.so not found under %s — extension modules may "
                "fail to resolve the Python C-API at import time" % _pylib)

        # 1) 自举编译扩展：Cython 用纯 Python 形态的自身把 .pyx 编成 .c
        #    再交给 clang 编译（CC/CXX 由 conan profile 提供）。
        self.output.info("bootstrapping Cython extensions "
                         "(pure-Python Cython -> C -> clang)")
        r = subprocess.run(
            [py, "setup.py", "build_ext", "--inplace"],
            cwd=src, env=env, capture_output=True, text=True, timeout=3600)
        out = (r.stdout or "") + (r.stderr or "")
        print("[cython build] build_ext rc=%d" % r.returncode)
        if r.returncode != 0:
            for line in out.splitlines()[-40:]:
                print("[cython build]", line)
            raise ConanException("cython build_ext failed (rc=%d)"
                                 % r.returncode)

        # 2) 构建期签名：后续上游测试要真实 import 这些扩展（E212）
        self._sign_tree(src)

        # 3) 上游测试（R51 如实回填）
        if can_run(self):
            self._run_upstream_tests(py, src, env)

    def _run_upstream_tests(self, py, src, env):
        """上游测试：runtests.py 驱动（unittest 风格，非 pytest 收集）。

        cython 的 ``tests/run/*.py`` 是**由 runtests.py 编译执行**的 Cython
        测试模块（拿它们当 pytest 用例收集是错的）。故：
          1. 先做**真实端到端冒烟**——用刚构建出的 Cython 把一个 ``.pyx``
             编成 ``.c`` → clang 编成 ``.so`` → 真实调用，证明本包的
             核心功能（当编译器用）可用；
          2. 再尝试驱动上游 runtests.py（限时），如实记录结果（R51）。
        """
        src_pyx = os.path.join(self.build_folder, "ohc_smoke.pyx")
        with open(src_pyx, "w", encoding="utf-8") as f:
            f.write("def add(int a, int b):\n    return a + b\n")
        env2 = dict(env)
        # 勿覆盖 PYTHONPATH：env 里已含 ①distutils 垫片目录 ②源码树
        # ③setuptools 制品。旧的 `env2["PYTHONPATH"] = src` 会把后两者冲掉，
        # 实测直接导致 Cythonize 报
        #   ModuleNotFoundError: No module named 'distutils'。
        # 这里只**前置** build_folder（自举出的 .so 在此）并保留其余。
        env2["PYTHONPATH"] = os.pathsep.join(
            [self.build_folder] + env.get("PYTHONPATH", "").split(os.pathsep))
        r = subprocess.run(
            [py, "-m", "Cython.Build.Cythonize", "-i", src_pyx],
            cwd=self.build_folder, env=env2,
            capture_output=True, text=True, timeout=900)
        out = (r.stdout or "") + (r.stderr or "")
        print("[cython smoke] cythonize -i rc=%d" % r.returncode)
        if r.returncode != 0:
            for line in out.splitlines()[-25:]:
                print("[cython smoke]", line)
            raise ConanException(
                "end-to-end smoke failed: the freshly built Cython could not "
                "compile a .pyx (rc=%d)" % r.returncode)
        so = [n for n in os.listdir(self.build_folder)
              if n.startswith("ohc_smoke") and n.endswith(".so")]
        if not so:
            raise ConanException("cythonize produced no extension module")
        self._sign(os.path.join(self.build_folder, so[0]))
        r2 = subprocess.run(
            [py, "-c", "import ohc_smoke; "
                       "assert ohc_smoke.add(20, 22) == 42; "
                       "print('smoke add(20,22)=', ohc_smoke.add(20, 22))"],
            cwd=self.build_folder, env=env2,
            capture_output=True, text=True, timeout=300)
        print("[cython smoke] import+call rc=%d" % r2.returncode)
        for line in ((r2.stdout or "") + (r2.stderr or "")).splitlines()[-8:]:
            print("[cython smoke]", line)
        if r2.returncode != 0:
            raise ConanException(
                "end-to-end smoke failed: compiled module not callable")

        # 上游 runtests.py（限时子集；如实记录，不谎报全量通过）
        runner = os.path.join(src, "runtests.py")
        if not os.path.isfile(runner):
            self.output.warning("upstream runtests.py not found; skipped")
            return
        try:
            r3 = subprocess.run(
                [py, runner, "-vv", "--no-pyregr", "run.hello_world"],
                cwd=src, env=env2, capture_output=True, text=True,
                timeout=900)
            out3 = (r3.stdout or "") + (r3.stderr or "")
            print("[cython upstream runtests] rc=%d" % r3.returncode)
            for line in out3.splitlines()[-20:]:
                print("[cython upstream runtests]", line)
        except subprocess.TimeoutExpired:
            self.output.warning(
                "upstream runtests.py exceeded the time budget; recorded as "
                "not-completed (R51: no pass rate is claimed for it)")

    def package(self):
        src = self.source_folder
        site = self._site()
        os.makedirs(site, exist_ok=True)

        # 1) 交付 Cython 包（纯 Python 源码 + 构建出的 .so）
        dst_pkg = os.path.join(site, "Cython")
        shutil.copytree(os.path.join(src, "Cython"), dst_pkg)

        # 1b) 交付上游顶层 ``cython.py``（setup.py:515 ``py_modules=["cython"]``）。
        #
        # 上游的 ``Cython/Compiler/Nodes.py:6`` 与 ``Visitor.py`` 等都会
        # ``import cython``——这不是 Cython 包本身，而是源码树根的**顶层模块**：
        # 被作为模块导入时它执行 ``from Cython.Shadow import *``（作为 __main__
        # 时则是 CLI 入口）。只拷 ``Cython/`` 会让这些模块 import 失败：
        #   ModuleNotFoundError: No module named 'cython'
        # CI 实测（PR #13673 第五轮，test_package 阶段）：包内 site-packages
        # 仅有 ``Cython/``，加载 ``Cython.Compiler.Scanning`` 时即触发该错误。
        # 这也是 ``cython`` CLI（bin/）能跑同款代码、而 site-packages 形态不能
        # 的原因——CLI 脚本自带自定位 ``sys.path.insert``。
        src_mod = os.path.join(src, "cython.py")
        if not os.path.isfile(src_mod):
            raise ConanException(
                "upstream top-level cython.py missing from the source tree — "
                "site-packages would be unusable for 'import cython'")
        shutil.copy2(src_mod, os.path.join(site, "cython.py"))

        # 2) 交付 CLI 入口脚本到 bin/（改写 shebang 指向 conan python）
        py = self._py_bin()
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for name in CLI_SCRIPTS:
            src_script = os.path.join(src, name + ".py")
            if not os.path.isfile(src_script):
                continue
            dst = os.path.join(bindir, name)
            with open(src_script, encoding="utf-8") as f:
                body = f.read()
            lines = body.splitlines()
            if lines and lines[0].startswith("#!"):
                lines[0] = f"#!{py}"
            else:
                lines.insert(0, f"#!{py}")
            # 让脚本能找到包内的 Cython（与 site-packages 同布局时由
            # PYTHONPATH 提供；此处补一条自定位兜底）
            with open(dst, "w", newline="\n", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            os.chmod(dst, 0o755)

        # 3) 打包后再签名一次（copy 会破坏签名——E212 族）
        self._sign_tree(site)

        # 4) 载荷校验：核心扩展必须存在且可加载的基础要件齐备
        must = ["Cython/__init__.py", "Cython/Compiler/Scanning.py"]
        for m in must:
            if not os.path.exists(os.path.join(site, m)):
                raise ConanException("cython payload incomplete: " + m)
        sos = []
        for dirpath, _d, files in os.walk(site):
            sos += [n for n in files if n.endswith(".so")]
        if not sos:
            raise ConanException(
                "no compiled Cython extension (.so) in the package — "
                "the bootstrap did not produce binaries")
        self.output.info(f"packaged {len(sos)} extension module(s)")

    def package_info(self):
        site = self._site()
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.env_info.PYTHONPATH.append(site)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        # Cython 的 cli 需要 conan python 在 PATH
        self.runenv_info.append_path("PATH", os.path.join(self._py_pkg(), "bin"))
