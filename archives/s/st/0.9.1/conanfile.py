#!/usr/bin/env python3
"""st 0.9.1 — suckless simple terminal（纯 Makefile，无 configure）。

首稿由 `ohc-run.py conan-init` 模板生成，随后按实测改三处（收尾-5 2026-09-29）：
  ① `package_type`: library → **application**（产物是 `st` 可执行，R38 要求软件级 commands.json）
  ② Autotools → **显式 `make`**：st 无 configure；`config.mk` 把 `PREFIX`/`X11INC`/`X11LIB`
     烧死成 `/usr/local` 与 `/usr/X11R6/*`（本机 `/usr/X11R6/include` 不存在），
     且 `INCS`/`LIBS` 走 `pkg-config --cflags/--libs fontconfig,freetype2`
     ⇒ 只覆盖 `CC` / `INCS` / `LIBS` 三个 make 变量，路径全交 pkg-config 解析。
  ③ `requirements()` 由 `pass` 填成实测四依赖（freetype2/fontconfig/x11/xft 四个 pkg-config 缺失）。
  ④ `build()` 不再 exec `pkg-config` 二进制，改纯 Python 解析 `.pc`（返修-1 2026-09-30）：
     CI worker 的进程 PATH 没有 `pkg-config`（本地有 ⇒ 只在 CI 暴露），详见 `_pc_query`。

CC 的来源：`.POSIX` 目标下 make 的默认 `CC=c99`，而本机 `command -v c99` 为空（`Error 127`），
故显式取 profile 的 `tools.build:compiler_executables["c"]`。
"""
import os
import re
import shlex

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import PkgConfigDeps


# ═════════ 纯 Python 的 pkg-config 等价实现（只吃 PkgConfigDeps 生成的 .pc）═════════
# 返修-1 根因（CI build #65601 真首错 `FileNotFoundError: 'pkg-config'`）：
#   原 build() 用 `subprocess.check_output(["pkg-config", ...], env=os.environ)` —— 走的是
#   **conan 客户端进程自己的 PATH**。CI worker env dump 实测 PATH=
#   /data/app/bin:/system/bin:/system/sbin:/vendor/bin:~/.local/bin，**没有**
#   /data/service/hnp/bin（pkg-config 实际所在；本机交互 shell 有它 ⇒ 本地 W3 绿、CI 红）。
#   profile 的 `[buildenv] PATH=+(path)/data/service/hnp/bin` 只写进 conanbuild.sh，
#   只有 `self.run(env="conanbuild")` 的子进程看得到，救不了 Python 侧的 exec。
# 两条已否决的替代路线：
#   · 给 _env 手工补 hnp/bin 等绝对路径 ⇒ 把「本机恰好有」写死进配方，换台机就碎；
#   · `tool_requires("pkgconf/...")` ⇒ 同样只进 conanbuild.sh 的 PATH，os.environ 依然没有，
#     除非再手工接线，收益为零还多一份构建图依赖。
# 故改为直接解析 `.pc`（纯文本 `key: value`），口径与 pkg-config **不带 --static** 完全一致：
#   只用 Cflags / Libs / Requires（Cflags.private / Libs.private / Requires.private 一律不取）。

_PC_VAR_RE = re.compile(r"\$\{([A-Za-z0-9_.]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
_PC_OPS = (">=", "<=", "!=", "==", ">", "<", "=")


def _pc_expand(text, variables, depth=0):
    """展开 .pc 的 ${var} / $var 引用；自引用封顶 20 层防死循环。"""
    if depth > 20:
        return text

    def _sub(match):
        key = match.group(1) or match.group(2)
        if key in variables:
            return _pc_expand(variables[key], variables, depth + 1)
        return match.group(0)

    return _PC_VAR_RE.sub(_sub, text)


def _pc_read(pcdir, name):
    """解析 `<pcdir>/<name>.pc` → (fields, variables)。

    找不到文件即硬错（pkg-config 同款行为）：四个根包的 Requires 闭包必须都在
    PkgConfigDeps 的输出目录里，缺了就是生成阶段出了问题，要红在第一条真实错误上。
    """
    path = os.path.join(pcdir, name + ".pc")
    if not os.path.isfile(path):
        raise RuntimeError("pkg-config 等价解析：找不到 %s（PkgConfigDeps 生成不全）" % path)
    with open(path, encoding="utf-8") as handle:
        raw = handle.read()
    raw = re.sub(r"\\\n", "", raw)  # 行尾续行
    variables = {"pcfiledir": pcdir}  # pkg-config 内置变量
    fields = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        eq, colon = line.find("="), line.find(":")
        if eq != -1 and (colon == -1 or eq < colon):
            variables[line[:eq].strip()] = line[eq + 1:].strip()   # 变量赋值 key=value
        elif colon != -1:
            fields[line[:colon].strip()] = line[colon + 1:].strip()  # 字段 Key: value
    return fields, variables


def _pc_requires(text, variables):
    """`Requires:` 字段 → 包名列表（容忍逗号与「操作符 版本」；Conan 生成的一般是纯包名）。"""
    tokens = [t for t in re.split(r"[\s,]+", _pc_expand(text, variables).strip()) if t]
    names, i = [], 0
    while i < len(tokens):
        if tokens[i] in _PC_OPS:
            i += 2  # 跳过操作符后的版本号
            continue
        names.append(tokens[i])
        i += 1
    return names


def _pc_query(pcdir, flag, packages):
    """pkg-config `--cflags` / `--libs` 的等价实现（非 static 口径）。

    排序：**被依赖者排在依赖者后面**（Kahn 拓扑序，静态链接也安全）；`--libs` 把所有
    `-L` 统一前置（pkg-config 同款），同名 flag 去重。全程无外部二进制。
    """
    if flag not in ("--cflags", "--libs"):
        raise ValueError("unsupported pkg-config flag: %s" % flag)
    key = "Cflags" if flag == "--cflags" else "Libs"
    parsed = {}
    order = []

    def _load(name):
        if name in parsed:
            return
        parsed[name] = _pc_read(pcdir, name)
        order.append(name)
        fields, variables = parsed[name]
        for req in _pc_requires(fields.get("Requires", ""), variables):
            _load(req)

    for pkg in packages:
        _load(pkg)

    dependents = {name: set() for name in order}
    for name in order:
        fields, variables = parsed[name]
        for req in _pc_requires(fields.get("Requires", ""), variables):
            dependents[req].add(name)

    tokens, seen, done, pending = [], set(), set(), list(order)
    while pending:
        ready = [n for n in pending if dependents[n] <= done]
        if not ready:
            ready = pending[:1]  # .pc 依赖本应无环；万一有环按发现序推进，绝不死等
        for name in ready:
            fields, variables = parsed[name]
            for token in shlex.split(_pc_expand(fields.get(key, ""), variables)):
                if token not in seen:
                    seen.add(token)
                    tokens.append(token)
            done.add(name)
            pending.remove(name)

    if flag == "--libs":
        tokens = [t for t in tokens if t.startswith("-L")] + \
                 [t for t in tokens if not t.startswith("-L")]
    return " ".join(tokens)


class StConan(ConanFile):
    name = "st"
    version = "0.9.1"
    description = "st — simple terminal for X (suckless.org)"
    license = "MIT"
    homepage = "https://st.suckless.org/"
    url = "https://dl.suckless.org/st/st-0.9.1.tar.gz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 四个 pkg-config 实测缺失项（freetype2 / fontconfig / x11 / xft）；版本对齐传递依赖，
        # 版本取自本仓 archives/ 已归档版本，W0 preflight 再核是否已发布。
        self.requires("freetype/2.14.3")   # 与 fontconfig/2.18.3 的要求一致（2.14.3.1 会 Version conflict）
        self.requires("fontconfig/2.18.3")
        self.requires("libx11/1.8.13")
        self.requires("libxft/2.3.9")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 与本仓同类配方同款：PkgConfigDeps 生成 *.pc（freetype 的 pc 名为
        # `freetype2.pc`，由依赖配方的 pkg_config_name 属性决定），VirtualBuildEnv
        # 把 PKG_CONFIG_PATH 与 tool_requires 的 bin 注入 conanbuild 环境。
        PkgConfigDeps(self).generate()
        # 实测：只靠 PkgConfigDeps 不会把 .pc 目录放进 conanbuild 的 PKG_CONFIG_PATH
        # （g2 轮报 "No package 'x11' / 'freetype2' found"）⇒ 显式 append_path，
        # 且**必须在 VirtualBuildEnv.generate() 之前**（环境文件先生成则注入不生效）。
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # CC：显式给编译器（profile conf；.POSIX 下 make 默认 c99，本机没有 c99）
        executables = self.conf.get("tools.build:compiler_executables") or {}
        cc = executables.get("c") or "clang"
        # INCS / LIBS：config.mk 用 X11INC/X11LIB 烧死路径 + `$(PKG_CONFIG) --cflags fontconfig`
        # 反引号；这里整体覆盖成四个 .pc 的全量解析（.pc 由 PkgConfigDeps 生成），
        # 避免写死任何本机绝对路径。
        # ⚠ 坑一（r3–r6 四轮实测）：`PKG_CONFIG_PATH="..." make INCS="`pkg-config ...`"`
        # 这种写法里，**同一条命令的反引号在赋值生效之前就被 shell 展开**（POSIX：
        # 待定赋值不参与本命令其它词的展开）⇒ pkg-config 拿不到 .pc 目录、返回空。
        # 故必须在 Python 侧算好 INCS/LIBS 再拼进 make 命令，完全不依赖 shell 展开顺序。
        # ⚠ 坑二（返修-1，CI build #65601 真首错）：Python 侧直调 `pkg-config` 也不行 ——
        # subprocess 用的是 conan 客户端进程的 PATH，CI worker 上没有该二进制
        # （FileNotFoundError）。改为纯 Python 解析，见文件头 `_pc_query` 说明。
        pcdir = None
        for _root, _dirs, _files in os.walk(self.build_folder):
            if "x11.pc" in _files:
                pcdir = _root
                break
        if pcdir is None:
            raise RuntimeError("PkgConfigDeps 未生成 x11.pc（生成阶段失败或路径变更）")
        pkgs = ("x11", "fontconfig", "freetype2", "xft")
        incs = _pc_query(pcdir, "--cflags", pkgs)
        libs = "-lm -lrt -lutil " + _pc_query(pcdir, "--libs", pkgs)
        self.run(
            'make CC="%s" INCS="%s" LIBS="%s"' % (cc, incs, libs),
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package(self):
        # 产物只有 st 可执行（无库）
        copy(self, "st", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # R38：可执行产物 ⇒ 软件级 commands.json（归档流程提供）
