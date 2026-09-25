# 下游 OCaml 生态包在 HarmonyOS 的字节码工具适配模式

> **状态**: DRAFT — 待人工/AI 复核后提升为正式 E 条目
> **来源**: findlib (ocamlfind) 1.9.8 适配（archives/f/findlib/1.9.8，2026-09-22）
> **关联**: E253（OCaml 工具链自身迁移）

## 一、问题范围

E253 覆盖 OCaml 工具链**自身**（`ocaml/4.14.1.1.4`）的迁移。本条目覆盖**下游包**
以 `tool_requires("ocaml/...")` 拉入工具链后在 OHOS 构建时的适配点。

findlib 1.9.8 适配过程中依次遇到 3 个真实错误，全部源于同一根因族：

```
configure → "cannot determine ocaml's standard library directory"
make all  → "Cannot load required shared library dllunix"
make install → "install: inaccessible or not found"
```

## 二、根因

### 1. 字节码工具的 shebang 指向失效的编译期路径

OCaml 字节码工具（`ocaml` 顶层、configure 期间构建出的 `extract_args`）是脚本，
shebang 形如：

```
#!<build-time-prefix>/bin/ocamlrun
```

conan 包 store 迁移（`…/.cache/conan2/p/b/X` → `…/.conan2/p/X`）后该绝对路径不存在，
直接执行报 `ENOENT`。即便路径存在，OHOS hmmac 也**拒绝执行 shebang 脚本**
（E253 同源限制：无论 shebang 指向 `/bin/sh` 还是 bash）。

### 2. stdlib 路径与 C stubs 搜索路径

- `ocamlc -where` 返回的 stdlib 路径同样是编译期嵌入常量，store 迁移后失效 →
  `[ ! -d "$ocaml_core_stdlib" ]` 判定失败。
- 字节码链接/运行需加载 `lib/ocaml/stublibs/dllunix.so` 等 C stubs，shebang 失效
  导致自动定位失败；该缺失还会使 configure 的 DLL/ppxopt 能力探测**误判**为不支持。

### 3. OHOS 无 GNU install(1)

toybox/BusyBox 环境无 `install`，而不少 configure 硬编码
`INSTALLDIR = install -d` / `INSTALLFILE = install -c`。

### 4. 附：`-custom` 产物的平台限制

OCaml `-custom`（字节码 + 链接 C 运行时）产物在 OHOS **无法独立执行**：hmmac 拦截，
重签名后 custom runtime 报 `no bytecode file specified`（runtime 在 musl aarch64 上
把自身 ELF 误当字节码参数）。这会使基于 `-custom` 的上游集成测试执行阶段失败
（平台限制，非被测包缺陷）。

## 三、可复用方案

### 配方侧（conanfile.py build()）

```python
ocaml_pkg    = self.dependencies.build["ocaml"].package_folder
ocaml_bin    = f"{ocaml_pkg}/bin"
ocaml_stdlib = f"{ocaml_pkg}/lib/ocaml"
env = (f"OCAMLRUN={ocaml_bin}/ocamlrun "
       f"OCAMLLIB={ocaml_stdlib} "
       f"CAML_LD_LIBRARY_PATH={ocaml_stdlib}/stublibs "
       f"PATH={ocaml_bin}:$PATH")
self.run(f"{env} /bin/sh ./configure ...", env="conanrun")
self.run(f"{env} make -j1 all", env="conanrun")
```

### 补丁侧（单个 configure 补丁）

以 `$OCAMLRUN` 为守卫（非 OHOS 不设置 → 行为与上游一致，**不引入 `__OHOS__` 宏**）：

```sh
# 1. 显式解释器调用
ocaml_run () {
    if test -n "$OCAMLRUN" ; then "$OCAMLRUN" "$@" ; else "$@" ; fi
}
# 替换所有直接调用点（本例 3 处：ocaml 顶层 ×2、extract_args ×1）
ocaml_run ocaml -I +unix unix.cma itest-aux/simple.ml ...
ocaml_run tools/extract_args/extract_args -o ...

# 2. stubs 搜索路径（stdlib 确定后立即执行，并写入 Makefile.config 供子 make 继承）
ocaml_setup_runenv () {
    if test -n "$OCAMLRUN" && test -d "$ocaml_core_stdlib/stublibs" ; then
        CAML_LD_LIBRARY_PATH="$ocaml_core_stdlib/stublibs${CAML_LD_LIBRARY_PATH:+:$CAML_LD_LIBRARY_PATH}"
        export CAML_LD_LIBRARY_PATH
    fi
}

# 3. install(1) 探测回退（与上游注释中 BSD 建议一致）
if in_path install ; then
    INSTALLDIR="install -d" ; INSTALLFILE="install -c"
else
    INSTALLDIR="mkdir -p" ; INSTALLFILE="cp"
fi
```

## 四、证据链（findlib 1.9.8 实测）

| 阶段 | 结果 | 日志 |
|------|------|------|
| configure | EXIT=0（修复后） | `reports/configure.log` |
| make all（字节码） | EXIT=0 | `reports/make-all.log` |
| make opt（原生） | EXIT=0 | `reports/make-opt.log` |
| make install | EXIT=0（48 文件） | `reports/make-install.log` |
| 上游 itest | 编译 4/4 通过；执行平台豁免 | `reports/itest.log` |
| 等价验证 | 4/4 通过 | `reports/equiv-verification.log` |

复现：

```sh
cd archives/f/findlib/1.9.8 && conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 五、禁止项（反例）

| 反模式 | 原因 | 后果 |
|--------|------|------|
| 重写 shebang 为绝对 ocamlrun 路径 | OHOS hmmac 拒绝执行 shebang 脚本 | 仍 Permission denied |
| 仅把 ocaml bin 加进 PATH | shebang 不查 PATH，内嵌绝对路径仍失效 | 仍 ENOENT |
| 补丁用 `__OHOS__` 宏守卫 | 违反 R8/PF5 | preflight 拦截，PR 无法合入 |

## 六、适用范围与限制

- **适用**：以 `tool_requires ocaml` 在 OHOS 构建、且构建期调用 OCaml 字节码工具的
  下游包（findlib/ocamlfind、opam/dune 生态工具、含 OCaml 脚本的 autoconf 项目）。
- **不影响最终产物**：findlib 的 `make install` 优先安装原生 `ocamlfind_opt`，无
  shebang 依赖；字节码问题仅出现在配置/构建/测试期。
- **须逐一核对调用点**：不同项目 configure 中的字节码调用点不同，遗漏会导致后续
  步骤再次报 shebang 错误。
- **`-custom` 限制无法绕过**：属 OCaml 运行时缺陷，依赖它的上游测试只能按
  `docs/TEST_QUALITY_SPEC.md §3.3` 豁免 + 等价验证（并保留原始日志，避免 R51 申报失真）。
