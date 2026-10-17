# pdftoipe 7.2.29.2 适配说明

## 1. 软件与源码

- **软件**：pdftoipe（PDF → Ipe 绘图 XML 转换命令行工具）
- **上游版本**：7.2.29.2（ipe-tools tag `v7.2.29.2`，commit `cff4b05e03edd0064dbf771f2276e275d67e67dc`）
- **上游仓库**：https://github.com/otfried/ipe-tools
- **源码位置**：pdftoipe **没有独立仓库**，源码位于 ipe-tools 单仓的 `pdftoipe/` 子目录
  （`pdftoipe.cpp` 193 行、`xmloutputdev.cpp` 673 行、`xmloutputdev.h`、`parseargs.cc/h`、`pdftoipe.1`）
- **tarball**：`https://github.com/otfried/ipe-tools/archive/refs/tags/v7.2.29.2.tar.gz`
  sha256 `c8de0dc7eb8fa959c96539fb19ebfb8e16f459e9b4ef9259aeb30b76072cd083`
- **许可证**：GPL-2.0-or-later

## 2. 上游构建方式与适配结论

上游 `pdftoipe/Makefile` 只有 `all` / `clean` 两个目标：

```make
POPPLER_CFLAGS ?= $(shell pkg-config --cflags poppler)
POPPLER_LIBS   ?= $(shell pkg-config --libs poppler)
CPPFLAGS += $(POPPLER_CFLAGS)
LIBS     += $(POPPLER_LIBS)
CXXFLAGS += -Wno-write-strings -std=c++20
```

**源码零补丁。** OHOS 交叉编译所需的全部差异都能通过 make 命令行变量注入：

| 障碍 | 上游默认 | OHOS 实际 | 处置（配方内） |
|------|----------|-----------|----------------|
| 编译器 | `CXX` 缺省 = `g++` | OHOS 无 g++ | 命令行传 `CXX=<clang++>`（取自 `tools.build:compiler_executables` 的 `cpp`） |
| poppler 头 | `pkg-config --cflags poppler` | 无系统 poppler.pc | 命令行传 `CPPFLAGS=-I<poppler>/include/poppler` |
| poppler 库 | `pkg-config --libs poppler` | 同上 | 命令行传 `LIBS=-L<poppler>/lib -L<freetype>/lib -lpoppler` |
| C++ 标准 | `CXXFLAGS += -std=c++20` | — | 命令行覆盖 `+=`，须显式补齐 `-O2 -fPIC -std=c++20 -Wno-write-strings` |

> **关键点**：make 命令行变量会整条覆盖 makefile 内的 `+=`，因此一旦从命令行传
> `CPPFLAGS` / `LIBS`，上游的 `POPPLER_CFLAGS` / `POPPLER_LIBS` 钩子即失效
> （`$(shell pkg-config ...)` 也不会被求值，构建反而更确定）。反之若只传
> `POPPLER_*`，则 `CPPFLAGS`/`LIBS` 会保留宿主环境变量，构建不确定。
> 本配方选择前者，并显式列出被覆盖掉的 `CXXFLAGS` 内容。

### 依赖：poppler 的 C++ 私有头

pdftoipe 直接 include poppler 的私有头：

```
goo/GooString.h   goo/gmem.h   Object.h   Stream.h   Array.h   Dict.h
XRef.h   Catalog.h   Page.h   PDFDoc.h   Error.h   GlobalParams.h
OutputDev.h   GfxState.h   GfxFont.h   Gfx.h   cpp/poppler-version.h
```

它们物理位于 `<poppler 包>/include/poppler`（与 `poppler.pc` 的 `Cflags: -I${includedir}/poppler`
一致），**用 poppler-cpp 公共头（`include/poppler/cpp/*.h`）无法编译**。制品仓
`poppler/25.12.0` 完整交付了这些头（含 `goo/` 与 `cpp/` 子目录），故依赖成立。

依赖图：`poppler/25.12.0 → freetype/2.14.3, zlib/1.3.1.1`。
链接期需要 freetype 的 `-L`（libpoppler.so 的 `DT_NEEDED` 含 `libfreetype.so.6`），
运行期由 conanrun 环境提供 `LD_LIBRARY_PATH`。

### 链接签名

OHOS SDK 的 clang 在链接可执行文件时会自动写入 `.codesign` 段，本包为源码直连链接
（不经 `cmake install` / `meson install`），签名没有被破坏 —— 已由 test_package C1 断言锁定。

## 3. 上游测试实况（rule4 计数实测）

**上游可执行测试用例数 = 0**，实测证据：

| 检查 | 命令 | 结果 |
|------|------|------|
| 组件 Makefile 目标 | `grep -E "^[A-Za-z0-9_.-]+:" pdftoipe/Makefile` | 只有 `all` / `clean` |
| 上游测试目标 | `make -n check` / `make -n test` | `No rule to make target 'check'/'test'`（rc=2） |
| 组件测试文件 | `find pdftoipe -iname "*test*" -o -iname "*check*"` | 无输出 |
| 全仓 test 文件归属 | `find . -iname "*test*"` 按顶层组件归类 | 仅 ipepython(1) / matplotlib(6) / svgtoipe(1)，**与 pdftoipe 无关** |

全仓命中的测试属其它组件（matplotlib backend 的绘图 demo、ipepython 的 Python 扩展
测试），执行它们需要 matplotlib 与 Ipe 自身的 Python 模块（非本包依赖），且与
pdftoipe 的转换功能无覆盖关系。

因此：**未修改任何上游测试用例**；适配后以 test_package 补全消费者与平台验证。

## 4. 适配后测试（11/11 全绿）

`test_package/test.sh` 现场合成单页 PDF（200×200；红色斜线描边 + 绿色矩形填充 +
24pt 蓝字 "Hi"，纯 ASCII、xref 偏移固定、无尾随空格，不引入二进制夹具），
在临时目录内执行，不在工作区留残留。

| 组 | 项 | 断言 |
|----|----|------|
| A 消费者用例 | A1 | `-h` 打印 `pdftoipe version 2024/11/15` + `Usage:`，退出码 1 |
| | A2 | 无参数调用退出码 1 |
| | A3 | 端到端转换：默认输出名 `<name>.ipe`，退出码 0 |
| | A4 | `<?xml version="1.0"?>` + `<ipe version="70000" creator="pdftoipe 2024/11/15">` + `<page>` |
| | A5 | 图形保真：`stroke="1.000000 0.000000 0.000000" pen="1"`、`fill="0.000000 1.000000 0.000000"`、坐标 `10 10 m`/`190 190 l`/`50 50 m`/`150 150 l` |
| | A6 | 文字保真 `size="24"` + `matrix="1 0 0 1 40 120"` + `>Hi</text>`；`-notext` 后无 `<text>` |
| | A7 | 包 `bin/` 经 VirtualRunEnv 导出到消费者 PATH |
| B 鸿蒙特有 | B1 | `DT_NEEDED` 含 `libc.so`（musl）与 `libc++_shared.so`（OHOS libc++），**不含** glibc 的 `libc.so.6` |
| | B2 | 目标数据模型：`ELF64` / `2's complement, little endian` / `AArch64` |
| C PC 特有 | C1 | 含鸿蒙 PC 加载期必需的 ELF 代码签名段 `.codesign` |
| | C2 | 产物为 PIE（`DYN (Position-Independent Executable file)`）且具备可执行权限 |

`test_package/conanfile.py` **不使用 `can_run()` 门控**：本侧
`tools.build.cross_building:can_run=False` 会让 `can_run()` 恒为 False，
`test()` 被静默跳过而 `conan create` 仍返回 0（假绿陷阱）。

## 5. 本地验证

```
conan create archives/p/pdftoipe/7.2.29.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="pdftoipe/*"
```

结果：`rc=0`；`test_package` 输出 `PDFTOIPE_TEST_PACKAGE_RESULT=consumer=7/7 ohos=2/2 pc=2/2 total=11/11`；
包内产物 `bin/pdftoipe`（68 KB）+ `share/man/man1/pdftoipe.1` + `licenses/gpl.txt`。

## 6. CI 门禁结果（本地以 `ci/conan/build_and_test.sh` 预演）

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | PASS | 根目录白名单检查 |
| L0 | PASS | 结构/命名 slug/`conanfile.name` 一致/`commands.json`/`settings` 四项/MANIFEST/patch 格式 全过 |
| L1 | PASS | `test_package` 被真实执行（L1a/L1b），`test()` 非空壳 |
| L2 | **SKIP（非阻塞）** | 见下 |
| L4 | PASS | 无 `patches/`，无需补丁安全扫描 |
| L5 | PASS | `bin/` 有内容（`pdftoipe` + man page + license） |
| JC | PASS | 增量模式 10 文件，无杂项/无隐藏文件/单软件原子性 |
| 整体 | Success 1/1 | |

### 6.1 平台 CI 实测（PR #11671）

| 时间（+08:00） | 构建 | Worker | 平台结论 |
|----------------|------|--------|----------|
| 2026-09-21 20:45 | #54491 | CI-029 | **CI 校验通过** —— Conan test_package 通过 / L0 门禁通过 / L1 门禁通过，worker_preparation→cleanup 各步全 ✅ |
| 2026-09-21 21:56 | #54542 | CI-031 | **CI 校验通过**（同上，全套步骤 ✅） |
| 2026-09-21 23:28 | #54608 | CI-030 | **CI 校验通过**（同上，全套步骤 ✅） |

即平台侧 `conan create` + test_package + L0/L1 均已实测通过；下文本机预演中被标 SKIP 的 L2 属**非阻塞项**。

**L2 为何 SKIP（非失败）**：L2 冒烟要求 `<bin> --version` 或 `<bin> --help` **退出码为 0**。
pdftoipe 没有 `--version` 选项；`-h` / `-help` / `--help` / `-?` 均走上游 usage 分支并以
**退出码 1** 结束（`pdftoipe.cpp` main 中 `if (!ok || argc < 2 || argc > 3 || printHelp) { … return 1; }`）。
若要让 L2 变绿，必须给上游新增 `--version` 参数或改其退出码 —— 属于改变上游 CLI 行为，
与"源码零补丁、不改上游行为"的适配原则冲突，故不做。CI 脚本对该分支本身标注为
`non-blocking`（`[warn] … (non-blocking)`），不影响构建结论（同款情况见 poppler 软件级
manifest 的 `L2: SKIP (11 tools version/help failed - OHOS platform limitation, non-blocking)`）。
该行为已由 test_package 的 A1/A2 断言锁定（`-h` 与无参数均应为退出码 1）。

## 7. 已知限制

- 运行期 `libpoppler.so` / `libfreetype.so.6` 需由 conanrun 环境（`LD_LIBRARY_PATH`）提供；
  依赖位于其它 Conan 包目录，故**不写死 RPATH**（写死会把包缓存绝对路径烤进产物）。
- `-opw` / `-upw`（加密 PDF 口令）路径未做专门用例；上游实现直接透传 poppler，
  平台无关，风险低。
- 无头环境下 pdftoipe 不依赖任何显示系统（纯文件 IO），无需图形环境验证。
