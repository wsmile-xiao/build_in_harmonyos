# DRAFT-E683-sc-im-0.8.5-pkgconfig-libdir-optional-feature-off：可选功能靠 pkg-config 探测时，依赖不在制品仓怎么「禁得干净、禁得可证」

> Contributor: 任务卡 10412（sc-im 0.8.5）| Status: Draft | Updated: 2026-09-23
> 触发场景：任务卡「xlsxio 不在档必须禁 xlsx」——处置过程里发现真正的坑不是「禁」，而是**禁得不确定**
> 对应：`knowledge/drafts/DRAFT-E683-sc-im-0.8.5-pkgconfig-libdir-optional-feature-off.kv`

## 问题

sc-im 的 `src/Makefile` 用四条**带失败分支**的条件决定功能面：

```makefile
ifneq ($(shell pkg-config --exists ncursesw || echo 'no'),no)        # 必需
  CFLAGS += $(shell pkg-config --cflags ncursesw)
ifneq ($(shell pkg-config --exists libxls || echo 'no'),no)          # xls 导入
  CFLAGS += -DXLS ...
ifneq ($(shell pkg-config --exists libzip libxml-2.0 || echo 'no'),no)  # xlsx/ods 导入
  CFLAGS += -DODS -DXLSX ...
ifneq ($(shell pkg-config --exists xlsxwriter || echo 'no'),no)      # xlsx 导出
  CFLAGS += -DXLSX_EXPORT ...
```

制品仓实测：

```text
$ conan list "xlsxio*" -r=ohpcd        → Found 0 pkg/version recipes
$ conan list "libxlsxwriter*" -r=ohpcd → Found 0 pkg/version recipes
```

→ 按 W0：xlsx 族**必须禁用**（且 PF4 依赖闸禁止捎带适配依赖）。

但「不声明 requires」只是**必要条件**：pkg-config 的探测面是
`PKG_CONFIG_PATH` **∪ 系统默认 pc 路径**。配方不写 `PKG_CONFIG_LIBDIR` 时，
默认路径照样可达——设备上它指向不存在的宿主目录（`pkg-config --variable pc_path`
实测是一条本机没有的路径，裸探测 ncursesw/libxml-2.0/libzip/xlsxwriter 全部 not found，
看起来「天然安全」），**换一个 worker 镜像就未必**。后果是同一份配方在不同机器编出
功能面不同的二进制：最典型的形态是「设备全绿、CI 链接期炸」，而且是最难查的一类。

## 处置（配方定式）

### 1. W0 先定性，再决定禁不禁

| 情形 | 判据 | 动作 |
|---|---|---|
| 在档 | `conan list` 有版本，且 `conan install --build=missing`（`-pr:h`/`-pr:b` 双传）组合可解 | 声明 requires |
| 不在档，探测**有失败分支** | Makefile/configure 的 `--exists … || echo no` / `AC_CHECK_*` 可失败 | **缺省禁用**（不算止损，但禁用事实+开关名+受影响测试项必须进 notes 与 PR 正文） |
| 不在档，探测**无失败分支** | `PKG_CHECK_MODULES` 无失败分支、头文件无条件 include 之类 | **W0-2 止损**，附证据不写配方 |

`conan list` 在档 ≠ 组合可解——组合验证必须真跑（sollya/gmp force 冲突先例）。

### 2. PATH + LIBDIR 双钉（核心）

```python
pcdir = self.generators_folder                 # PkgConfigDeps 的 .pc 落在这里
os.environ["PKG_CONFIG_PATH"]  = pcdir         # 已声明依赖可见
os.environ["PKG_CONFIG_LIBDIR"] = pcdir        # ← 关键：系统默认 pc 搜索路径整体排除
# 两者都要在 self.run(..., env="conanbuild") 之前写进 os.environ：
# conanbuild 只前置它自己声明的 PKG_CONFIG_PATH，LIBDIR 原样保留。
self.run(f'make -C src CC="{cc}" YACC="bison -y" prefix="{self.package_folder}" -j1',
         cwd=self.source_folder, env="conanbuild")
```

`PKG_CONFIG_LIBDIR` 是 pkg-config 的「默认目录」变量，赋值后 `/usr/lib/pkgconfig`
等系统目录一律不参与查找 ⇒ 未声明依赖的 `--exists` 在**任何**机器上都是 false，
功能面与镜像解耦。

### 3. 让产物自证（回归锚点）

sc-im 的 `--version` 会打印全部编译宏，于是禁用从「注释里的一句话」变成一条 CI 每轮复跑的断言：

```text
$ sc-im --version | grep -E -- "-DXLSX|-DODS|-DXLSX_EXPORT"   # 期望无输出（test_package 断言 4）
$ sc-im --version | grep -- "-DXLS"                            # 期望命中（在档依赖仍接通）
```

build() 冒烟也直接用它（`src/sc-im --version`，rc=0）。将来谁给配方补了 xlsx requires，
test_package 当场变红——这正是想要的性质。被测程序不自报开关时，退而对二进制做
符号/字符串断言（`readelf -p .rodata`、对 `.o` 反查宏）。

### 4. 记录三件套（notes + PR 正文）

1. **禁用事实**：依赖名 + `conan list … -r=ohpcd` 的命令与 0 条输出；
2. **开关名/机制**：本例不是 configure 开关，而是 `pkg-config --exists` 条件分支 +
   `PKG_CONFIG_PATH`/`PKG_CONFIG_LIBDIR` 环境钉扎（写清楚，别让人去找不存在的 `--disable-xlsx`）；
3. **受影响的测试项**：哪些上游用例/断言因此 NOT_RUN 或 SKIP，逐条归因。

## 结果（sc-im 0.8.5 实测）

- 构建面：`-DNCURSES -DXLS` 有，`-DXLSX -DODS -DXLSX_EXPORT` 无（`--version` 自证）；
- 依赖面：`ncurses/6.6 + libxls/1.6.3 (+ tool_requires bison/3.8.2)` 组合 `conan install --build=missing` rc=0；
- 可复现性：设备与 worker 的探测面同为「生成目录」，与系统 pc 路径无关。

## 禁止

- 不在档就 `tool_requires`/`requires` 硬加（PF4 直接拦）；
- 只钉 PATH 不钉 LIBDIR 就宣称「系统没有所以安全」；
- 无失败分支的硬依赖不走 W0-2 止损，而是改源码硬绕（= 未披露的功能缺失）。
