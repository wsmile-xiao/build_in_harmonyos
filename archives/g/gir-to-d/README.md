# gir-to-d

[gir-to-d](https://github.com/gtkd-developers/gir-to-d) — 从 GObject
Introspection（`.gir`）文件生成 **D 语言绑定源码**（gtk-d 生态的代码生成器）。

## 简介

GObject Introspection 用机器可读的 `.gir` XML 描述 C 库的 API（gtk、glib 等）。
gir-to-d 读取 `.gir` 加一份 `APILookup` 描述文件，输出对应的 D 语言绑定
（类包装、`extern(C)` 声明、类型定义）。产物是单个命令行可执行文件 `girtod`。

```bash
girtod -i <inputDir> -g <girDir> -o <outputDir>
```

- `-i` APILookup.txt 所在目录（同时是默认的相对路径基准）
- `-g` `.gir` 文件搜索目录（**必需**，不给会报 `Couldn't find the gir file`）
- `-o` 输出目录

输出的 D 绑定布局：

```
<outputDir>/<srcDir>/<Class>.d        # 类的 D 包装（继承自 ObjectG 等基类包装）
<outputDir>/<srcDir>/c/functions.d    # extern(C) 函数与 GType 声明
<outputDir>/<srcDir>/c/types.d        # 不透明结构与 c 类型再导出
```

`APILookup.txt` 的最小形态（`file:` 必须写在 `wrap:` **之后**）：

```text
outputRoot: /out
includeComments: false

wrap: test
srcDir: test
file: Test-1.0.gir
```

## OHOS 适配

- **本库不含任何库依赖**：`dub.json` 无 `dependencies` 键，源码只用 D 标准库
  （`std.*` / `core.*`）与自身模块；无 `pragma(lib)`、不链接 glib/gobject。
  源码中出现的 `gobject`/`gtkc` 字样是它**生成产物里的字符串**。
- **缺的是 D 工具链**（D 不在框架 `LANG_ENUM` 内，设备侧无任何 D 工具链）。
  本配方用 `tool_requires("ldc/1.42.0")` 取得，其运行期依赖 `libLLVM.so.20.1`
  由 `llvm/20.1.0` 提供（均为 ohpcd 制品，os=OHOS/arch=armv8）。
- **构建走 `GNUmakefile` 路径**：上游同时提供 `dub.json` / `meson.build` /
  `GNUmakefile`，其中只有 GNUmakefile **不需要 `dub`**（ohpcd 无该制品），
  且不依赖 `.git`（meson 路径用 `git describe` 取版本，tarball 无 `.git`）。

  ```makefile
  make -f GNUmakefile DC=ldc2 GIR_TO_D_VERSION=v0.23.3 \
    DCFLAGS="-O -I<ldc>/include/d" LDFLAGS="-L-L<ldc>/lib"
  ```

  `-I<ldc>/include/d` 与 `-L-L<ldc>/lib` 均为**实测必需**（ldc2 默认的
  import/链接路径在本制品上不可用）；`GIR_TO_D_VERSION` 用于修正版本号——
  tarball 无 `.git` 时 GNUmakefile 会回退到写死的 `v0.23.1`。

- **1 个补丁**：`patches/0001-opEquals-const-scope.patch` 把
  `LinkedHashMap.opEquals` 的 `inout typeof(this)` 改为现代 D 惯用的
  `scope const` 形式——LDC 1.42.0 的 DMD 前端（v2.112.1）拒绝前者
  （`core.internal.newaa` 以 const Key 实例化时报 *only parameters or
  stack-based variables can be `inout`*）。已实测该补丁**必需**：
  未打补丁的原始源码同样报同一错误。

- **产物**：`bin/girtod`（NEEDED 仅 `libc.so`，**无运行期动态库依赖**）、
  `licenses/COPYING`（GNU Lesser General Public License v3）。

## 依赖

| 类型 | 依赖 | 来源 |
|---|---|---|
| 运行期 | 无（仅 libc） | — |
| 构建工具链 | LDC 1.42.0（含 druntime + Phobos） | ohpcd `ldc/1.42.0`，作 `tool_requires` |
| 构建工具链 | LLVM 20.1.0（ldc2 运行期依赖） | ohpcd `llvm/20.1.0`（ldc recipe 自动引用） |
| 运行期（标准库） | `std.*` / `core.*`（随编译器） | ldc 包内 `include/d/` |

## 功能验证

```bash
# 配方验证（含 test_package，14 条断言，真实驱动 girtod 生成 D 绑定）
conan create archives/g/gir-to-d/0.23.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing

# 打包后的工具自报版本
<pkg>/bin/girtod --version
# → GIR to D v0.23.3
```

> **上游测试：D 语言惯例是源码内嵌 `unittest` 块**（不是独立 `t/` 目录），由
> D 生态标准的 `dub test` / `-unittest` 驱动。本包共 **4 个 `unittest` 块 / 12 条 assert**
> （`GirVersion.d:148` 8 条、`GirWrapper.d:826` 2 条、`GirWrapper.d:883` 1 条、
> `XMLReader.d:436` 1 条），实测 **10 通过 + 2 失败**——2 处失败均为**上游既有缺陷**
> （`stringToGtkD` 误改写参数里的 `string`；`ByChar.front` 对空 `data` 取 `[0]`），
> 与本配方无关。
>
> 上游**未把 `unittest` 接入任何构建路径**（`GNUmakefile` 无 test 目标、
> `meson.build` 无 `test()`、`dub.json` 无 `-unittest`），故本配方不把它作为门禁；
> 若计入，上游通过率为 **10/12**。详见 `archives/g/gir-to-d/0.23.3/notes.md`。

## 已知限制

- **带参数的方法会让 `girtod` 段错误**（上游既有行为）：`.gir` 中方法含
  `<parameters>` 时 `girtod` 报 `Signal 11`；参数less 方法正常。经验证与平台、
  工具链、本配方补丁均无关。本配方夹具因此只用参数less 方法，并在此如实记录。
- 测试夹具中的 `GObject-2.0.gir` 是**最小 stub**（真实文件需
  gobject-introspection 运行时，OHOS 侧不可得），仅含被测所需成员。

## 参考

- 仓库: https://github.com/gtkd-developers/gir-to-d
- 项目主页: https://gtkd.org
- APILookup 语法: 发行版内 `Readme_APILookup`
