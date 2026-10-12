# bart-view 0.3.00 — HarmonyOS PC (OHOS aarch64) 适配笔记

## 这个包是什么

`bart-view`（上游 [mrirecon/view](https://github.com/mrirecon/view)）是 BART
（Berkeley Advanced Reconstruction Toolbox，MRI 重建工具箱）的配套图像查看器。
上游仓库极小（v0.3.00 共 15 个文件）：

```
.gitignore  .gitlab-ci.yml  LICENSE  Makefile  README.md  genctags  viewer.png
src/cfl2png.c  src/colormaps.inc  src/draw.c  src/draw.h
src/main.c  src/view.c  src/view.h  src/viewer.ui
```

`make all` 产出两个可执行文件：

- `view`    — GTK3 多维图像查看器（`src/main.c` + `src/view.c` + `src/draw.c`）；
- `cfl2png` — 把 BART 的 CFL 数据集（`.hdr` + `.cfl`）导出为 PNG
  （`src/cfl2png.c` + `src/draw.c`）。

构建系统是**裸 Makefile**（不是 autotools）：`all: view cfl2png`，没有
`configure`，也没有任何测试目标。

`LICENSE` 是 BSD-3-Clause（`Copyright (c) 2015-2023. Martin Uecker. /
AG Uecker, University Medical Center Göttingen`）。

## 上游测试入口（R51）

**上游没有任何自动化测试。** 取证：

```
$ find . -type f | sort            # 全仓 15 个文件，无 tests/ 目录
$ grep -nE '^[a-zA-Z0-9_.-]+:' Makefile
80:all: view cfl2png
85:view:	...
88:cfl2png:	...
91:install:
96:clean:
$ grep -nE 'test|check' Makefile    # 无匹配
```

上游 `.gitlab-ci.yml` 只执行 `make all`（debian:bookworm 镜像，装
`libgtk-3-dev`/`libbart-dev`，把 `view`/`cfl2png` 作为 artifact 上传），
没有任何测试步骤。因此 `test_package/MANIFEST.yml` 的 `upstream_tests` 为空，
`upstream_check_command` 记为 `make all`（真实构建入口）。

`make all` 在本任务中已实际执行（即 recipe build() 调用的 make 默认目标），
通过与失败证据见 `reports/test-report.md`。

## 依赖结构

bart-view 的 Makefile 有三个外部依赖来源：

1. **GTK3** — `pkg-config --cflags/--libs gtk+-3.0`（拉入 cairo/pango/
   gdk-pixbuf/atk/glib 整条链）；
2. **libpng** — `LDFLAGS += -lpng`（BART `misc/png.c` 的 PNG 写出）；
3. **BART 工具箱静态库** — 经 `BART_TOOLBOX_PATH`：

```
TOOLBOX_INC=$(BART_TOOLBOX_PATH)/src/
TOOLBOX_LIB=$(BART_TOOLBOX_PATH)/lib/
# link: libmisc.a libgeom.a libnum.a
```

若未设置 `BART_TOOLBOX_PATH`，Makefile 回落到 `/usr/include/bart` 与
`/usr/lib/bart`（Debian `libbart-dev` 的布局）。也就是说，**上游把 BART 当成
一份源码/开发树依赖**，而不是一个已安装的库包。

## 关键决策：BART 工具箱 vendored

制品仓里 `bart/1.0.00` 存在，但它是 `package_type = "application"`，
`package_folder` 下只有：

```
bart/1.0.00/p/bin/bart
```

没有任何头文件、也没有 `lib/libmisc.a` 等静态库（见 bart recipe 的
`package_info(): bindirs = ["bin"]`）。`bart-view` 需要的是 BART 的**工具箱
（源码头文件 + 3 个静态库）**，与已发布的 `bart` 应用包不是同一个交付物。

仓库对"依赖未以 Conan 包发布"有既有先例（`flann` vendor lz4、`deltarpm`
vendor bzip2/zstd、`laundrify-aio` vendor pyjwt），因此本 recipe 采用同一模式：
在 `conandata.yml` 的 `vendored:` 段声明 BART v1.0.00 官方源码，`source()` 里
解到 `<source_folder>/bart-toolbox/`，`build()` 里就地构建
`lib/libmisc.a lib/libgeom.a lib/libnum.a`，再用它作为 `BART_TOOLBOX_PATH`。

BART 版本（1.0.00）与制品仓已发布的 `bart/1.0.00` 对齐，保持生态一致。

> 备选方案与取舍：也可以先发布一个 `bart-toolbox` 类型的库包再让 bart-view
> `requires` 它，但那就变成"依赖项"任务（需要单独 PR 与发布）；本任务是
> **目标库 bart-view 适配**，vendored 是保持单包原子性的可行路径。

## BART 源码侧适配（vendored 构建内）

这些修改只作用于**构建期下载的 BART 源码**，不进入本仓库、不属于 bart-view
自身源码。除第 1 项外均与 `archives/b/bart/1.0.00` recipe 一致。

### 1. 恢复 `UNUSED` 宏（BART 1.0.00 的 API 回归）

`view.c` / `draw.c` 大量使用 `UNUSED(x);`，该宏由 BART 的 `misc/misc.h`
提供。核对 BART 版本：

```
$ git show v0.9.00:src/misc/misc.h | grep UNUSED
27:#define UNUSED(x) (void)(x)
$ git show v1.0.00:src/misc/misc.h | grep UNUSED   # 无输出
```

即 **BART 1.0.00 删除了 `UNUSED` 宏**，而 bart-view 0.3.00 仍依赖它（README
声称只需要 BART >= 0.8.00）。直接编译会在链接期报
`ld.lld: error: undefined symbol: UNUSED`（clang 把 `UNUSED(x)` 当作隐式声明的
函数）。修复：在 vendored BART 的 `src/misc/misc.h` 中恢复
`#define UNUSED(x) (void)(x)`（位置与 0.9.00 一致，MIN/MAX 之前）。

### 2. clang 15 严格性修复（同 bart recipe）

GCC 宽松、clang 15 严格，BART 源码需要以下精确文本修复（只触及
`misc/`、`num/`、`geom/` 三目录；bart-view 只编译这三个库）：

- **label at end of compound statement**：`default:` / `case X:` / goto 标签后
  （可含空行）直接 `}` 而无语句 → 补空语句 `;`；
- **case 后带初始化器声明**：clang 要求块作用域 → 给 `case X:` 加 `{`，并在该
  分支最后一个 `break;` 后补 `}`；
- **`misc/opts.c`**：外层 switch 三组 `case OPT_(FLOAT|DOUBLE)?_VEC*` 的声明补块
  作用域；C23 属性 `[[fallthrough]]` 在 gnu17 下报 `expected expression` → 改写为
  注释；内层 switch 的 `OPT_*_VECN` 补块，并为被块作用域隔离的 `count` 补声明；
- **`misc/mmio.c`**：`case FILE_TYPE_CFL:` 后的 `char name_bdy[1024]` 补块作用域。

（`simu/simulation.c` 有多处同名 fall-through case，通用修复易误伤；bart-view
不编译 `src/simu`，直接跳过。）

### 3. blocks 运行时 stub

BART 的 `src/misc/nested.h` 用 clang blocks 实现嵌套函数：

```c
#define NESTED(RET, NAME, ARGS)  RET (^NAME)ARGS = ^ARGS
#define CLOSURE_TYPE(x) (^x)
```

于是编译需要 `-fblocks`，链接需要 libBlocksRuntime 的
`_NSConcreteStackBlock` / `_Block_object_assign` / `_Block_object_dispose` 等
符号。鸿蒙没有 libBlocksRuntime；BART 的 blocks 都是栈上立即调用
（`NESTED_CALL`），不跨作用域复制，因此 `compat/blocks_runtime_stub.c`
（随配方 `export_sources` 传递）提供最小实现即可。该文件与
`bart/1.0.00` recipe 的 compat 文件一致。

### 4. 构建期对 BART Makefile / 脚本的修补

- `rules/*.sh`、`ar_lock.sh`、`git-version.sh` 等 shebang 为 `#!/bin/bash`，
  而鸿蒙 bash 在 `/data/service/hnp/bin`（无 `/bin/bash`）→ 统一改 `#!/bin/sh`
  （脚本均为 sh 兼容）；
- `Makefile` 第 234 行 `$(shell gcc --version)` 硬编码 gcc（鸿蒙无 gcc）→ 改
  `$(CC) --version`；
- `LDFLAGS += -Wl,-no-warn-execstack`（lld 不识别）与 `LDFLAGS += -lBlocksRuntime`
  （鸿蒙无该库）→ 移除；
- `ar_lock.sh` 的 `flock ... -c`（鸿蒙 flock 不支持 `-c`）→ 直接调 `ar`
  （构建固定 `-j1` 串行）。

## bart-view 自身源码侧适配

只有一处：`src/cfl2png.c:133`

```c
char* ext = rindex(out_prefix, '.');   // 原：musl 未在 strings.h 声明 rindex
char* ext = strrchr(out_prefix, '.');  // 改：标准等价
```

clang 15 把未声明的 `rindex` 当隐式函数（返回 `int`），触发
`-Wint-conversion` **错误**（不仅是警告）。`rindex` 是 BSD 遗留接口，musl 的
`strings.h` 完全不声明它；`strrchr` 是 C 标准库等价物，语义一致。

## 构建与链接

`build()` 里 vendor 构建后用命令行变量覆盖 bart-view Makefile（GNU make 中
命令行变量优先于 Makefile 内的 `+=`，因此可屏蔽其追加的 `-lBlocksRuntime`
与硬编码 `-lpng`）：

```
make -j1 CC=<clang> BART_TOOLBOX_PATH=<bart-toolbox> \
  CFLAGS='-O2 -std=c11 -fopenmp -fblocks -Wall' \
  CPPFLAGS='-I{fftw3f,openblas,libpng,zlib}/include' \
  LDFLAGS='-L... -Wl,-rpath,... -lm -lpng16 -lz -lrt -lopenblas -lfftw3f -lomp -lpthread <blocks_stub.o>'
```

几点说明：

- GTK 的 cflags/libs 由 Makefile 内的 `` `pkg-config gtk+-3.0` `` 提供，
  recipe 通过 `generate()` 里的 `Environment` 显式把 PkgConfigDeps 生成目录写进
  `PKG_CONFIG_PATH`（PkgConfigDeps 自身不会设置该变量）；
- conan 的 libpng 提供 `libpng16.so`，故链接用 `-lpng16`（上游写 `-lpng`）；
- BART 的 `num/` 用 OpenBLAS 的 `cblas.h`/`lapacke.h`（`BLAS_BASE` 指向
  openblas 包），因此**不需要** `lapack` 包，也不需要 BART 自带 lapacke；
- `-ffp-contract=off`：与 `bart/1.0.00` recipe 一致，使 vendored BART 库的数值
  行为对齐上游 x86-64 CI（aarch64 clang 默认 `-ffp-contract=fast`）；
- CI 沙箱中 lld 加载 `libxml2.so.16` 失败的问题，沿用 bart 的方案：把 clang 所在
  SDK 的 `llvm/lib` 前置进 `LD_LIBRARY_PATH`。

## 测试

`test_package/`：

- `test.c` — L0c 测试源文件载体（application 包无库 API，编译验证消费者工具链）；
- `test_cfl2png.py` — **鸿蒙特有测试**（23 项命名检查 + 1283 次逐像素真值比较）。
  它不是"文件存在/大小合理"这类弱断言，而是**验证输出内容**：测试自带一个
  PNG 解码器（解析 chunk、校验 CRC、zlib 解压、反滤波），读出 `cfl2png` 真正
  写出的像素，与**独立推算的真值**逐点比对。真值来自上游算法
  （`cfl2png.c`/`draw.c`）：MAGN 灰度为
  `trunc(255 * clamp((scale*|v| - winlow)/(winhigh - winlow), 0, 1))`，
  `scale = 1/max`（相对窗口）或 `1`（`-A` 绝对窗口）。

  覆盖的功能路径（均真实执行被测二进制）：

  1. `-A -z 1`，数据集 `v = n/256`（`n = x + 16y`）→ 真值
     `trunc(255n/256)` 在浮点下逐位精确 → **256 像素零容差**比对
     （同时验证 x/y 方向、windowing、magnitude 映射、PNG 编码、解码器）；
  2. 默认相对窗口（自动求 `max`），数据集 `v = n/255`（`max=1.0`）→
     `|像素 - n| <= 1`、单调非减、端点 0/255；
  3. `-FZ`（XY 翻转）→ 零容差比对 `out(x,y) = src(15-x, 15-y)`；
  4. `-CV`（viridis 色图）→ 低端精确等于 viridis 起点色 `(68,1,84,255)`，
     高端匹配参考色（±4）；
  5. 全零数据集 → 覆盖 `max==0 → max=1` 分支，应输出全黑不透明；
  6. 缩放：默认 `-z 2` → 32×32，`-z 1` → 16×16；
  7. 确定性：同输入两次输出逐字节一致；
  8. CLI 校验：非法窗口 `-l 0.9 -u 0.5` 必须非零退出（实测 134/SIGABRT）；
  9. `view`（GTK3）在无 DISPLAY 下端到端加载依赖栈——GTK 报
     `cannot open display` 属预期（无图形环境），但**不得**出现
     `Error loading shared library`（证明 OHOS 链接与 ELF 签名正确）。

实测：23/23 命名检查 + 1283/1283 像素比较通过（100%），详见
`reports/test-report.md`。

`view` 是交互式 GUI；本环境无 X/图形显示，无法做窗口级功能验证，因此只做依赖
栈加载验证。`cfl2png` 是纯计算+文件输出，可完整端到端验证。

## 已知限制

1. `view` 需要图形显示环境（DISPLAY），无头环境下只能验证依赖栈加载；
2. BART 工具箱以 vendored 源码方式随本包构建；若后续发布独立的 BART
   toolbox/toolbox-dev 包，应改为 `requires` 并移除 vendored 段；
3. 上游 `install` 目标把 `view` 安装到 `$(DESTDIR)/usr/lib/bart/commands/`。
   本包按 OHOS 约定安装到 `bin/`（`view`/`cfl2png` 可直接执行），未做与
   `bart` 命令目录的联动。

## 复现

```bash
conan create archives/b/bart-view/0.3.00 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
```

`conanfile.py` 修改后先 `conan remove bart-view -c`，否则缓存中的旧 binary 会让
`conan create` 直接复用（"全绿"只是关于旧配方的证据）。

## 环境备注（仅本地验证，不影响仓库）

本地执行 `conan-verify` 时框架会把 GitHub URL 临时改写成 `ghfast.top` 镜像；
本机该镜像不可达（read timeout）。为避免误判，本地验证时把上游 tarball 预置进
conan 的下载缓存（sha256 校验通过）后重跑，`conan-verify` G0–G4 全绿；CI 侧由
`build_and_test.sh` 的镜像列表（gh-proxy → 直连 GitHub）自动兜底。
---

**编译结束**: 2026-10-10 13:30
**最终状态**: built
