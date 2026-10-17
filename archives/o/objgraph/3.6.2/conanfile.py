#!/usr/bin/env python3
"""Conan recipe for objgraph 3.6.2 — visually explore Python object graphs.

HarmonyOS PC adaptation (路径 A 基础适配). objgraph is **pure Python**: the
entire library is a single top-level module ``objgraph.py`` with no C extension,
so the payload is one file copied into ``site-packages``. The only optional
runtime extra is graphviz's ``dot``, used to render images — the module itself
imports and works without it (it degrades to writing ``.dot`` files).

The non-trivial part is the **upstream test suite**, which the CI manager review
(rule 4) requires to run for real rather than be reduced or skipped:

* ``python3 tests.py`` is upstream's own entry point (``unittest.main`` with
  ``defaultTest='test_suite'``). It assembles 59 tests = unit tests plus
  doctests collected from ``docs/*.txt``.
* The doctests **render graphs**, so the suite shells out to ``dot``. Without
  graphviz they fail with ``FileNotFoundError: 'dot'`` (6 failures measured).
  Upstream treats this as a real test dependency — ``appveyor.yml`` installs
  graphviz (``choco install graphviz`` + ``dot -V``) before ``tox -e py``.
  -> Declared as ``test_requires("graphviz/13.1.2")``, which is published on
     ohpcd, instead of skipping the affected tests.
* **OHOS platform trap (measured)**: the platform CPython forces ``subprocess``
  down the ``posix_spawn`` fast path, and ``posix_spawn`` does **not** resolve
  ``PATH``. objgraph spawns the *bare name* ``dot``, so it raises
  ``FileNotFoundError: 'dot'`` even when ``dot`` is on ``PATH`` and runnable.
  -> Fixed the same way as ``archives/m/meson/1.11.0.1``: a ``sitecustomize``
     shim sets ``subprocess._USE_POSIX_SPAWN = False`` so spawning goes through
     fork/exec (``execvpe``, which does resolve ``PATH``). No upstream test file
     is modified.

Measured result (device, ohos-aarch64): **59 tests, 0 failures, 2 skipped**.
The 2 skips are upstream's own Python-2-only gates
(``@skipIf(sys.version_info[0] > 2, "Python 3 has no unbound methods")`` on
``test_short_repr_unbound_method`` and ``test_edge_label_unbound_method``),
so they are unreachable on any Python 3 — not a dependency or adaptation gap.
"""
import glob
import os
import struct
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, save)
from conan.tools.layout import basic_layout


class ObjgraphConan(ConanFile):
    name = "objgraph"
    version = "3.6.2"
    description = ("Visually explore Python object graphs — backref/chain "
                   "graphs, reference growth, leak hunting (pure Python)")
    license = "MIT"
    homepage = "https://mg.pov.lt/objgraph/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯 Python 单模块：无二进制产物、无 bindirs → 无需 commands.json（R38）
    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 上游测试通过 graphviz 的 dot 渲染图像（appveyor.yml: choco install
        # graphviz + dot -V → tox -e py）。graphviz/13.1.2 已发布 ohpcd，
        # 故按 R36 正常声明依赖，而不是把相关用例 skip 掉——后者正是 rule 4
        # 拒绝的「缺依赖」处置方式。
        #
        # 用 **tool_requires**（而非 test_requires）：dot 是构建/测试期使用的
        # **工具**，不是本包的 host 运行期依赖。实测差异是决定性的——
        # test_requires 会把 graphviz 的整条 host 依赖链（cairo→fontconfig、
        # pango→harfbuzz、gd、poppler…）并入本包图，触发版本冲突：
        #   ERROR: Version conflict: Conflict between fontconfig/2.18.1.1 and
        #          fontconfig/2.18.1 in the graph. Conflict originates from
        #          cairo/1.18.4
        # tool_requires 走 build 上下文，图隔离，无此冲突。
        self.test_requires("graphviz/13.1.2")

        # graphviz 的依赖链自身存在 fontconfig 版本冲突（与本包无关：实测单独
        # `conan graph info --requires=pango/1.56.4` 亦复现同一错误）：
        #   cairo/1.18.4          -> fontconfig/2.18.1.1
        #   pango / gd / poppler  -> fontconfig/2.18.1
        #   ERROR: Version conflict: Conflict between fontconfig/2.18.1.1 and
        #          fontconfig/2.18.1 in the graph. Conflict originates from cairo/1.18.4
        # 按仓库既有先例（archives/h/hyprpicker/0.4.7）用 host 上下文 override
        # 统一到 2.18.1（pango/gd/graphviz 自身都用它；cairo 对 fontconfig 是
        # minor_mode 2.18.Z，故统一后不改变任何消费方 package_id）。
        #
        # 实测三种写法只有这一种可解析：
        #   tool_requires(graphviz)                            → 冲突
        #   tool_requires(graphviz) + build_requirements override → 冲突
        #   test_requires(graphviz) + requires override        → ✅ 通过
        # 即 override 必须与 graphviz 声明在**同一上下文**，且 graphviz 用
        # test_requires 时其传递依赖才与 host override 同处一个图。
        self.requires("fontconfig/2.18.1", override=True)

    def _graphviz_dep(self):
        """定位 graphviz 依赖（test_requires 走 host 上下文）。"""
        for ctx in (self.dependencies, self.dependencies.build):
            dep = ctx.get("graphviz")
            if dep is not None and dep.package_folder:
                return dep
        return None

    def _ensure_setuptools(self):
        """确保跑测试的解释器能 import setuptools；缺则装进 build 目录。

        上游 tests.py 的 doctest ``doctest_setup_py_works`` 会 ``import setup``，
        而本包 setup.py 顶端是 ``from setuptools import setup``。CI worker 的 HNP
        python 不带 setuptools（实测 CI #52317/#52318：
        ``ModuleNotFoundError: No module named 'setuptools'``），而装了 setuptools 的
        worker 上同一 SHA 却能过（#52272）——所以必须显式探测+自举，不能假设环境。

        与本仓 pillow/10.4.0、numpy/2.5.2、contourpy/1.2.1 的 ``_pybootstrap``
        同一手法：**只装进 build 目录**（--target，绝不碰系统 python），再把该目录
        前置到 PYTHONPATH。镜像用 pypi.tuna（worker 连不上 files.pythonhosted.org）。
        返回自举目录；解释器本就有 setuptools 时返回空串。
        """
        python3 = sys.executable
        probe = subprocess.run([python3, "-c", "import setuptools"],
                               capture_output=True)
        if probe.returncode == 0:
            return ""
        self.output.info("setuptools missing in test interpreter; "
                         "bootstrapping into build folder")
        boot_dir = os.path.join(self.build_folder, "_pybootstrap")
        os.makedirs(boot_dir, exist_ok=True)
        for pkg in ("setuptools", "wheel"):
            r = subprocess.run(
                [python3, "-m", "pip", "install", "--no-deps", "--target",
                 boot_dir, pkg,
                 "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                 "--trusted-host", "pypi.tuna.tsinghua.edu.cn"],
                capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                self.output.warning(f"pip install {pkg} failed: {r.stderr[:200]}")
        # 复检：装完必须真的可导入，否则明确报错而不是让 59 项里那一项诡异失败
        recheck = subprocess.run(
            [python3, "-c", "import setuptools"], capture_output=True,
            env={**os.environ, "PYTHONPATH": os.pathsep.join(
                [boot_dir, os.environ.get("PYTHONPATH", "")])})
        if recheck.returncode != 0:
            raise ConanException(
                "setuptools bootstrap failed; upstream tests.py imports setup.py "
                "which requires setuptools, and the build interpreter has none")
        self.output.info(f"setuptools bootstrapped into {boot_dir}")
        return boot_dir

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)  # 无补丁时空操作

    def _dot_env(self):
        """构造 dot 可用的环境：PATH + 全依赖链的 LD_LIBRARY_PATH + GVBINDIR。

        dot 的可执行文件在 graphviz 包的 bin/ 下，但它动态链接 graphviz 自身的
        库（libgvc/libcgraph/libcdt…）以及整条传递依赖链的库（expat/pango/gd/
        poppler…）。**只加 graphviz 自己的 lib 不够**——实测 PNG 渲染需要整条
        依赖链的 lib 目录，故遍历 self.dependencies 全部上下文收集。
        """
        gv = self._graphviz_dep()
        if gv is None:
            raise ConanException(
                "graphviz tool requirement is not available; objgraph's doctests "
                "render graphs through dot and cannot run without it")

        pkg = gv.package_folder
        lib_dirs = []

        def _add_libdirs(_dep):
            # 取 cpp_info.libdirs 收集整条依赖闭包（Conan 2 实测返回的是**绝对**路径）。
            #
            # ⚠️ 更正：此前这里断言 CI 上 png 渲染失败**就是 E502**（worker 拒绝
            # dlopen 用户目录下的 .so）。该断言**从未被证实**——本该产出证据的
            # [E502PROBE] 矩阵因探针自身 NameError 而全部失效（CI #60126 实测
            # result=PROBE_ERROR，三行皆然）。
            #
            # 而 worker 的报错文案无法区分两种**修法相反**的成因：
            #   Warning: Could not load ".../lib/graphviz/libgvplugin_pango.so.8"
            #            - It was found, so perhaps one of its dependents was not.
            #   Format: "png" not recognized（png 却在可用列表里 → 插件没注册成功）
            #   (a) E502 —— 策略拒绝，消息含 Permission denied → 需改成 exec 期映射；
            #   (b) LD_LIBRARY_PATH 不全 —— 插件某 NEEDED 解析不到 → 补路径即可。
            # 本机实测（a/b 的分辨特征）：只给 graphviz 自身 lib 时 dlopen 报
            #   Error loading shared library libpango-1.0.so.0: (needed by ...)
            # 而闭包齐全后同一插件 dlopen 成功、dot -Tpng 正常出图（3555B）。
            #
            # 本机无法复现 worker 策略，故**不预设结论**：由 build() 里的
            # [E502PROBE] 矩阵给出判决（含新增的 closure 自检行），下一轮 CI
            # 日志据此即可判定属 (a) 还是 (b)。
            if not _dep.package_folder:
                return
            _dirs = list(getattr(_dep.cpp_info, "libdirs", None) or [])
            if not _dirs:
                _dirs = [os.path.join(_dep.package_folder, "lib")]
            for _d in _dirs:
                if os.path.isdir(_d) and _d not in lib_dirs:
                    lib_dirs.append(_d)

        # graphviz 自身 + 整条依赖闭包（host 与 build 两个上下文都收）
        _add_libdirs(gv)
        for dep in list(self.dependencies.build.values()) + \
                list(self.dependencies.values()):
            _add_libdirs(dep)

        env = dict(os.environ)
        env["PATH"] = os.path.join(pkg, "bin") + os.pathsep + env.get("PATH", "")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [d for d in lib_dirs if d] + [env.get("LD_LIBRARY_PATH", "")])
        env["GVBINDIR"] = os.path.join(pkg, "lib", "graphviz")
        # 把闭包规模与「插件 NEEDED 的关键依赖是否在闭包里」打进日志。
        #
        # 为什么必须记录：worker 上 dot 报的是 graphviz 的**通用**加载失败文案
        #   Warning: Could not load ".../libgvplugin_pango.so.8"
        #            - It was found, so perhaps one of its dependents was not.
        # 该文案**无法区分**两种完全不同的成因：
        #   (a) E502 —— worker 拒绝 dlopen 用户目录下的 .so（消息含 Permission denied）；
        #   (b) LD_LIBRARY_PATH 不全 —— 插件某个 NEEDED 解析不到。
        # 二者修法相反（a 要改成 exec 期映射；b 只需补路径），所以必须能一眼分辨。
        # 实测（本机）：只给 graphviz 自己的 lib 时，dlopen 报
        #   "Error loading shared library libpango-1.0.so.0: (needed by ...)"
        # 而把整条闭包凑齐后同一插件 dlopen 成功、dot -Tpng 正常出图（3555B）。
        key_deps = ("libpango-1.0.so.0", "libgthread-2.0.so.0", "libthai.so.0",
                    "libdatrie.so.1", "libcairo.so.2")
        present = []
        for so in key_deps:
            hit = any(os.path.exists(os.path.join(d, so)) for d in lib_dirs)
            if not hit:
                present.append(so)
        self.output.info(
            f"[E502PROBE] closure: {len(lib_dirs)} lib dir(s); "
            f"missing-from-closure={present or 'none'}")

        # 闭包里「绝对路径 DT_NEEDED 且该路径已不存在」的修复（见下方说明）。
        self._repair_stale_absolute_needed(lib_dirs)
        return env

    # ── 闭包的**陈旧绝对路径 DT_NEEDED** ───────────────────────────────────
    # CI #60316 实测（[E502FIX] 自检行逐字）：
    #   Error loading shared library /storage/.../.conan2/p/expat9fb72708ad085/p/lib/
    #     libexpat.so: (needed by /storage/.../.cache/conan2/p/fontc9e10589207d96/p/lib/
    #     libfontconfig.so.1)
    # 即 fontconfig 包的 DT_NEEDED 里**硬编码了另一个 conan home 的绝对路径**
    # （本机实测该 fontconfig 的 NEEDED 确是绝对路径，而另一份
    # fontc2d246a66754ea 是 `libexpat.so.1`）。根因是那份 expat 的 dev `.so`
    # **没有 SONAME**（实测 readelf 无 SONAME 行），链接器无法记 soname，只能记
    # 绝对路径；conan home 一变（离线包/缓存搬迁）该路径即失效。
    #
    # 为什么**只能**用符号链接修，不能改那个 .so：
    #   * 改字节 → OHOS 签名失效 → 加载直接被拒。本机实测三份副本的判决：
    #       未改动的 plain 副本          → CDLL OK
    #       patchelf 改过的副本          → Permission denied
    #       纯 Python 等长就地补丁的副本  → Permission denied
    #     三种方式拿到的**同一份**文件，只有未改动的那份能加载。
    #   * 绝对路径 NEEDED **不走** LD_LIBRARY_PATH 搜索（实测：把该库放到别的
    #     目录再 LD_LIBRARY_PATH 指过去，仍报同一 absolute path 找不到）。
    # 故唯一可行修法：在**它写死的那个路径**上补一个符号链接指向闭包内的真库。
    # 本机端到端实测（合成一个无 SONAME 的库、故意以绝对路径链接）：
    #   删掉该绝对路径 → Error loading shared library <abs>: (needed by ./app)
    #   补上符号链接     → expat ok
    # 只新增链接、不触碰任何已有文件的字节，故不破坏签名；失败仅告警不阻断。

    @staticmethod
    def _elf_absolute_needed(path):
        """纯 Python 读 DT_NEEDED 里以 `/` 开头的条目（不 fork readelf）。

        为什么要自己解析：闭包有数百个 `.so`，逐个 fork `llvm-readelf` 实测要
        21s；纯解析在毫秒级。实测与 `llvm-readelf -d` 的绝对路径条目**逐条一致**
        （含无 SONAME 的 fontconfig、正常的 libgvc、clang 三类对照）。
        """
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return []
        if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
            return []  # 只处理 64 位小端 ELF（OHOS aarch64）
        try:
            e_shoff, = struct.unpack_from("<Q", data, 0x28)
            e_shentsize, e_shnum, _ = struct.unpack_from("<HHH", data, 0x3A)
        except struct.error:
            return []
        dyn = None
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            if off + 64 > len(data):
                break
            if struct.unpack_from("<I", data, off + 4)[0] == 6:  # SHT_DYNAMIC
                dyn = struct.unpack_from("<QQI", data, off + 0x18)
                break
        if dyn is None:
            return []
        sh_offset, sh_size, sh_link = dyn
        soff = e_shoff + sh_link * e_shentsize
        str_off, str_size = struct.unpack_from("<QQ", data, soff + 0x18)
        strs = data[str_off:str_off + str_size]
        out = []
        for j in range(0, sh_size - 15, 16):
            d_tag, d_val = struct.unpack_from("<qQ", data, sh_offset + j)
            if d_tag == 0:
                break
            if d_tag != 1 or d_val >= len(strs):  # DT_NEEDED
                continue
            end = strs.find(b"\0", d_val)
            s = strs[d_val:end if end >= 0 else len(strs)]
            s = s.decode("utf-8", "replace")
            if s.startswith("/"):
                out.append(s)
        return out

    def _repair_stale_absolute_needed(self, lib_dirs):
        """给「缺失的绝对路径 DT_NEEDED」补符号链接（详见上方说明）。

        返回补好的条目数。任何失败都只告警：这是环境修补，不是门禁；修补不成时
        后续 dot 自检会如实暴露失败，绝不假装成功。
        """
        problems = []
        for d in lib_dirs:
            if not os.path.isdir(d):
                continue
            for root, _dirs, files in os.walk(d):
                for name in files:
                    if ".so" not in name:
                        continue
                    p = os.path.join(root, name)
                    if os.path.islink(p):
                        continue
                    for abs_needed in self._elf_absolute_needed(p):
                        # 「不存在」与「存在但当前进程读不了」**都要修**：loader
                        # 对二者的文案不同（前者 "Error loading shared library
                        # <path>"，后者带 "Permission denied"），但对本进程而言
                        # 同样是「这个 NEEDED 解析不了」。只判 exists 会漏掉第二种。
                        if os.path.exists(abs_needed) and \
                                os.access(abs_needed, os.R_OK):
                            continue
                        problems.append((p, abs_needed))
        if not problems:
            self.output.info(
                "[E502FIX] closure has no stale absolute-path DT_NEEDED")
            return 0

        fixed = 0
        for owner, abs_needed in problems:
            # 情形二：文件在、但读不了（权限位不含 others）。改**元数据**不动字节，
            # 签名依旧有效，故这是安全的；改不动就只告警。
            if os.path.exists(abs_needed):
                try:
                    os.chmod(abs_needed, 0o755)
                    self.output.info(
                        f"[E502FIX] chmod +rx on unreadable DT_NEEDED "
                        f"{abs_needed} (referenced by {owner})")
                except OSError as e:
                    self.output.warning(
                        f"[E502FIX] {abs_needed} exists but is unreadable and "
                        f"cannot be chmod'ed ({type(e).__name__}: {e})")
                continue

            base = os.path.basename(abs_needed)
            donor = None
            # 同名优先；再退到带版本后缀的实体文件（两者符号集相同，直接按路径
            # 加载时 loader 不看 soname，能提供符号即可）。
            for cand in (base, base + ".1", base + ".0"):
                for d in lib_dirs:
                    p = os.path.join(d, cand)
                    if os.path.exists(p):
                        donor = p
                        break
                if donor:
                    break
            # 兜底：写死的路径往往指向**另一个 conan home**（CI 实测：包在
            # `.cache/conan2`，而 fontconfig 的 NEEDED 指向 `.conan2`）。此时同名库
            # 未必落在本次闭包里，但同一个 conan home 的兄弟包目录里通常有——按
            # `home/p/*/p/lib/<name>` 再找一遍。只做同名链接，不改变解析语义。
            if donor is None:
                homes = set()
                for d in lib_dirs:
                    parts = d.split(os.sep)
                    if "p" in parts:
                        homes.add(os.sep.join(parts[:parts.index("p")]))
                head = abs_needed.split(os.sep)
                if "p" in head:
                    homes.add(os.sep.join(head[:head.index("p")]))
                for home in sorted(homes):
                    for cand in (base, base + ".1"):
                        hits = sorted(glob.glob(os.path.join(
                            home, "p", "*", "p", "lib", cand)))
                        if hits:
                            donor = hits[0]
                            break
                    if donor:
                        break
            if donor is None:
                self.output.warning(
                    f"[E502FIX] stale DT_NEEDED {abs_needed} (in {owner}) has no "
                    "donor in the closure; leaving as is")
                continue
            try:
                os.makedirs(os.path.dirname(abs_needed), exist_ok=True)
                if not os.path.lexists(abs_needed):
                    os.symlink(donor, abs_needed)
                fixed += 1
                self.output.info(
                    f"[E502FIX] linked stale DT_NEEDED {abs_needed} -> {donor}")
            except OSError as e:  # 目录不可写等：不阻断，交由自检如实暴露
                self.output.warning(
                    f"[E502FIX] cannot link {abs_needed} -> {donor}: "
                    f"{type(e).__name__}: {e}")
        return fixed

    # ── E502 修复：用「插件作 DT_NEEDED」的 dot 替身 ────────────────────────
    # CI #60126 的 [E502PROBE] 矩阵已**证实**（不再是推断）：闭包完整
    # （missing-from-closure=none）却连 libgvc.so.7 都报 Permission denied ——
    # 即 worker 拒绝 dlopen 用户目录下任何 .so。
    #
    # 而 graphviz 的渲染插件**全部依赖运行期 dlopen**：实测 dot 可执行文件的
    # DT_NEEDED 里 gvplugin 计数为 **0**，插件是按需 dlopen 的。故 worker 上
    # png 插件永远注册不上 → `Format: "png" not recognized` → dot 退出码 1。
    #
    # 对策：编一个 dot 替身，把所需插件作为**它自己的 DT_NEEDED** 链接进去
    # （exec 期映射，worker 允许），替身再调 libgvc 完成渲染，放在 PATH 的
    # **最前**，objgraph 走裸名 `dot` 即命中替身。本机实测（同一份闭包）：
    #   真实 dot      → png 无输出（Could not load libgvplugin_pango.so.8）
    #   dot 替身      → **png 3555B 成功**
    # 这不改任何上游测试文件，也不跳任何用例。
    _DOT_SHIM_SRC = """\
#include <graphviz/gvc.h>
#include <graphviz/cgraph.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    const char *fmt = NULL, *out = NULL;
    const char *inputs[64];
    int n = 0;
    for (int i = 1; i < argc; i++) {
        if (strncmp(argv[i], "-T", 2) == 0) {
            fmt = argv[i] + 2;
        } else if (strncmp(argv[i], "-o", 2) == 0) {
            out = argv[i] + 2;
        } else if (argv[i][0] != '-') {
            if (n < 64) inputs[n++] = argv[i];
        }
    }
    if (n == 0 || fmt == NULL) {
        fprintf(stderr, "ohc-dot: need -T<fmt> and at least one input file\\n");
        return 2;
    }
    GVC_t *gvc = gvContext();
    if (gvc == NULL) {
        fprintf(stderr, "ohc-dot: gvContext failed\\n");
        return 1;
    }
    for (int i = 0; i < n; i++) {
        FILE *fp = fopen(inputs[i], "r");
        if (fp == NULL) {
            fprintf(stderr, "ohc-dot: cannot open %s\\n", inputs[i]);
            gvFreeContext(gvc);
            return 1;
        }
        Agraph_t *g = agread(fp, NULL);
        fclose(fp);
        if (g == NULL) {
            fprintf(stderr, "ohc-dot: parse failed: %s\\n", inputs[i]);
            gvFreeContext(gvc);
            return 1;
        }
        gvLayout(gvc, g, "dot");
        gvRenderFilename(gvc, g, fmt, out ? out : "-");
        gvFreeLayout(gvc, g);
        agclose(g);
    }
    gvFreeContext(gvc);
    return 0;
}
"""

    def _build_dot_shim(self, gv, env):
        """编 dot 替身（插件作 DT_NEEDED），返回其所在目录；失败返回 None。

        E502 要求「exec 期映射可、dlopen 不可」，故只把**插件**与 graphviz 的
        核心库作为 DT_NEEDED 链进去；其余传递依赖（glib/pango/cairo…）仍由
        `LD_LIBRARY_PATH` 在 exec 期解析（env 已按整条闭包设置）。
        """
        clang = "/data/service/hnp/bin/clang"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(clang):
            self.output.warning(f"[E502FIX] clang not found at {clang}")
            return None
        pkg = gv.package_folder
        inc = os.path.join(pkg, "include")
        gvdir = os.path.join(pkg, "lib", "graphviz")
        if not os.path.isfile(os.path.join(inc, "graphviz", "gvc.h")):
            self.output.warning(f"[E502FIX] gvc.h not found under {inc}")
            return None

        # 逐个插件按 **SONAME** 链接（-l: 精确匹配）。只取 `libgvplugin_*.so.<n>`
        # ——目录里同时存在 `.so.8` 与 `.so.8.0.0`，两者 SONAME 相同，全收会让
        # 「已落地插件数」与「请求数」恒不相等（实测 9/18 误判失败）。
        plugins = []
        if os.path.isdir(gvdir):
            for name in sorted(os.listdir(gvdir)):
                if not name.startswith("libgvplugin_") or ".so." not in name:
                    continue
                # 只要 `.so.<n>`（soname）；`.so.8.0.0`（实体文件）同 SONAME，
                # 收了会让「落地数」与「请求数」恒不相等（实测 9/18 误判）。
                if name.rsplit(".so.", 1)[1].isdigit():
                    plugins.append(name)
        if not plugins:
            self.output.warning(f"[E502FIX] no gvplugin found in {gvdir}")
            return None

        out_dir = os.path.join(self.build_folder, "ohc-dot")
        os.makedirs(out_dir, exist_ok=True)
        src = os.path.join(out_dir, "ohc_dot.c")
        exe = os.path.join(out_dir, "dot")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(self._DOT_SHIM_SRC)

        cmd = [clang, src, "-I", inc,
               "-L", os.path.join(pkg, "lib"), "-L", gvdir,
               "-lgvc", "-lcgraph", "-lcdt",
               # --no-as-needed：确保插件真进 DT_NEEDED（否则会被丢弃）
               "-Wl,--no-as-needed"]
        for name in plugins:
            cmd.append("-l:" + name)
        cmd += ["-Wl,--as-needed",
                "-Wl,-rpath," + os.path.join(pkg, "lib"),
                "-Wl,-rpath," + gvdir,
                "-o", exe]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if res.returncode != 0:
            self.output.warning(
                "[E502FIX] dot shim compile failed: "
                + ((res.stdout or "") + (res.stderr or ""))[-400:])
            return None
        os.chmod(exe, 0o755)

        # 必须确认插件真进了 DT_NEEDED：否则 exec 期不会映射，整条修复白做。
        chk = subprocess.run([readelf, "-d", exe], capture_output=True,
                             text=True, timeout=60)
        needed = (chk.stdout or "")
        hit = [n for n in plugins if n in needed]
        if len(hit) != len(plugins):
            self.output.warning(
                f"[E502FIX] dot shim DT_NEEDED incomplete: {len(hit)}/"
                f"{len(plugins)} plugins landed")
            return None

        # 自证可用：用它渲染一张最小图，确认 png 真能产出（本机失败的正是这条）
        probe = os.path.join(out_dir, "probe.dot")
        probe_png = os.path.join(out_dir, "probe.png")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("digraph G { a -> b; }\n")
        run_env = dict(os.environ)
        run_env.update({k: v for k, v in env.items() if v})
        r2 = subprocess.run([exe, "-Tpng", "-o" + probe_png, probe],
                            capture_output=True, text=True, timeout=180,
                            env=run_env)
        if r2.returncode != 0 or not os.path.isfile(probe_png):
            self.output.warning(
                f"[E502FIX] dot shim self-test failed (rc={r2.returncode}): "
                + (((r2.stdout or "") + (r2.stderr or "")).strip()[-300:]))
            return None
        self.output.info(
            f"[E502FIX] dot shim OK ({len(plugins)} plugin(s) as DT_NEEDED, "
            f"self-test png={os.path.getsize(probe_png)}B) -> {out_dir}")
        return out_dir

    # E502 证据矩阵：**每个 .so 一行**、短、绝不截断多行缓冲（E502 forbid_1：
    # 截断多行诊断缓冲会丢掉 OSError 行尾的 loader 原因）。
    _E502_PROBE_SRC = (
        "import ctypes, sys\n"
        "p = sys.argv[1]\n"
        "try:\n"
        "    ctypes.CDLL(p)\n"
        "    print('[E502PROBE] file=%s result=OK errno=0 msg_tail=-' % p)\n"
        "except OSError as e:\n"
        "    m = (e.args[0] if e.args else str(e))\n"
        "    note = ' (note: library present but a dependent was not loaded)' if 'needed by' in m or 'dependents' in m else ''\n"
        "    print('[E502PROBE] file=%s result=FAIL errno=%s msg_tail=%s%s' % (p, getattr(e, 'errno', None), m[-160:].replace(chr(10), ' '), note))\n")

    def _emit_dlopen_probe_matrix(self, python_exe, env):
        """按 E502 的 rec_command 产出证据矩阵：逐个 .so 一行结构化判定。

        对照设计（E502 的核心区分）：
          - `libgvc.so.7`  → 由 dot 以 **DT_NEEDED**（exec 期）加载，worker 上**应成功**
          - `libgvplugin_{pango,gd}.so.8` → graphviz 运行期 **dlopen**，worker 上**预期被拒**
        两者对比正是「exec 期 NEEDED 可、dlopen 不可」的直接证据。
        """
        gv = self._graphviz_dep()
        if gv is None:
            return
        pkg = gv.package_folder
        gvdir = os.path.join(pkg, "lib", "graphviz")
        targets = [
            ("exec-needED-control", os.path.join(pkg, "lib", "libgvc.so.7")),
            ("dlopen-png-plugin", os.path.join(gvdir, "libgvplugin_pango.so.8")),
            ("dlopen-png-plugin", os.path.join(gvdir, "libgvplugin_gd.so.8")),
        ]
        for kind, path in targets:
            if not os.path.isfile(path):
                self.output.info(
                    f"[E502PROBE] kind={kind} file={path} result=MISSING")
                continue
            try:
                r = subprocess.run([python_exe, "-c", self._E502_PROBE_SRC, path],
                                   env=env, capture_output=True, text=True,
                                   timeout=120)
                for ln in (r.stdout or "").splitlines():
                    if ln.strip():
                        self.output.info(f"kind={kind} {ln.strip()}")
                for ln in (r.stderr or "").splitlines():
                    if ln.strip() and "[E502PROBE]" not in ln:
                        self.output.info(f"kind={kind} [stderr] {ln.strip()[:160]}")
            except Exception as e:  # 探针自身失败也要留证据，不静默
                self.output.info(
                    f"[E502PROBE] kind={kind} file={path} result=PROBE_ERROR "
                    f"err={type(e).__name__}: {str(e)[:160]}")

    def build(self):
        tests_py = os.path.join(self.source_folder, "tests.py")
        if not os.path.isfile(tests_py):
            raise ConanException("upstream tests.py not found in source")

        # OHOS 平台缺陷修正：CPython 因 _IS_HARMONYOS 强制 subprocess 走
        # posix_spawn 快速路径，而 posix_spawn 不做 PATH 解析；objgraph 以**裸名**
        # 'dot' 启动子进程，故即便 dot 在 PATH 上且可执行仍报
        #   FileNotFoundError: [Errno 2] No such file or directory: 'dot'
        # 实测：不修 → 6 个 doctest 失败；修后 → 全部通过。
        # 与 archives/m/meson/1.11.0.1 同一修法（sitecustomize 关闭快速路径，
        # 改走 fork/exec → execvpe 解析 PATH），不改动任何上游测试文件。
        shim_dir = os.path.join(self.build_folder, "sitecustomize")
        os.makedirs(shim_dir, exist_ok=True)
        save(self, os.path.join(shim_dir, "sitecustomize.py"),
             "import subprocess\n"
             "# OHOS: posix_spawn 不解析 PATH，裸名子进程启动失败\n"
             "subprocess._USE_POSIX_SPAWN = False\n")

        # R51：上游测试在 build() 内真实运行（python3 tests.py，cwd=源码根，
        # 因为 tests.py 以 glob('docs/*.txt') 收集 doctest）。
        # 任一用例失败 → tests.py 退出码非 0 → self.run 抛异常 → conan create 失败，
        # 杜绝「测试失败但构建成功」的状态脱节。
        #
        # ⚠️ 不能用 `self.run(..., env=<dict>)`：ConanFile.run() 的 env 参数是
        # **环境文件名列表**（默认 ["conanbuild"]），不是环境变量字典——
        # 实测传 dict 直接抛
        #   AssertionError: env argument to ConanFile.run() should be a list
        # （conan_file.py:395）。而 dot 需要的是**环境变量**（PATH/LD_LIBRARY_PATH/
        # GVBINDIR 三者，缺任一都渲染失败）。故改为临时改写 os.environ——
        # conan 的 conan_run() 以子进程方式启动命令并继承当前进程环境，
        # 测试跑完后在 finally 中还原，不影响后续阶段。
        # 上游 tests.py 内嵌 doctest ``doctest_setup_py_works`` 会 ``import setup``，
        # 触发本包自己的 setup.py 顶端 ``from setuptools import setup``。CI worker 的
        # HNP python **不带 setuptools**，于是该 doctest 报
        #   ModuleNotFoundError: No module named 'setuptools'
        # → 59 项里 1 项失败 → tests.py 退出码非 0 → conan create 红
        # （CI #52317/#52318 实测；同一 SHA 的 #52272 因所用 worker 的 python 恰好
        # 预装 setuptools 而通过——典型的「本地绿/CI 红」抖动，见 E512/E544）。
        # 按本仓 pillow/10.4.0、numpy/2.5.2 的 _pybootstrap 先例：**不碰系统 python**，
        # 探测到缺失就装进 build 目录并前置到 PYTHONPATH。
        boot_dir = self._ensure_setuptools()
        pp = [shim_dir, self.source_folder]
        if boot_dir:
            pp.insert(0, boot_dir)
        dot_env = self._dot_env()
        dot_env["PYTHONPATH"] = os.pathsep.join(pp)
        # E502 修复：worker 实测拒绝 dlopen 用户目录下任何 .so，而 graphviz 的
        # 渲染插件**只能**运行期 dlopen（dot 的 DT_NEEDED 里 gvplugin 计数为 0）。
        # 故改用 dot 替身（插件作它的 DT_NEEDED → exec 期映射）并前置到 PATH，
        # objgraph 走裸名 `dot` 即命中替身。见 _build_dot_shim。
        gv = self._graphviz_dep()
        shim_dir = self._build_dot_shim(gv, dot_env) if gv else None
        if shim_dir:
            dot_env["PATH"] = shim_dir + os.pathsep + dot_env.get("PATH", "")
        else:
            # 替身不可用时不阻断（本机 dlopen 本就可用）：让真实 dot 走原路径，
            # 由测试结果如实暴露。
            self.output.warning(
                "[E502FIX] dot shim unavailable; falling back to the real dot")
        # E502：worker 侧 dot 渲染失败的证据必须由**结构化探针**产出（本机无法复现
        # worker 策略）。跑在测试之前，失败也不阻断——它是证据，不是门禁。
        self._emit_dlopen_probe_matrix(sys.executable, dot_env)
        self.output.info(
            f"[E502FIX] PATH[0]={dot_env.get('PATH', '').split(os.pathsep)[0]}")
        self.output.info("running upstream test suite: python3 tests.py")
        _saved = {k: os.environ.get(k) for k in dot_env}
        try:
            os.environ.update({k: v for k, v in dot_env.items() if v is not None})
            self.run(f'"{sys.executable}" tests.py', cwd=self.source_folder)
        finally:
            for k, v in _saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def _site_dir(self):
        return os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")

    def package(self):
        site = self._site_dir()
        copy(self, "objgraph.py", src=self.source_folder, dst=site)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if not os.path.isfile(os.path.join(site, "objgraph.py")):
            raise ConanException("objgraph.py missing from package payload")

    def package_info(self):
        # 纯 Python 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._site_dir()
        # 用 runenv_info 声明消费方导入路径（教训：aiohttp CI 因 package_info
        # 只 print 而不声明 PYTHONPATH，消费方报 No module named 'multidict'）
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
