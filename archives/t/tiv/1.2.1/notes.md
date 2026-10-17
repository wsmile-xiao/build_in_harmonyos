# tiv 1.2.1 适配笔记

## 编译环境

- 构建系统: makefile（上游手写 Makefile，无 configure 脚本）
- 编译日期: 2026-10-05
- 编译器: clang 15（aarch64-unknown-linux-ohos，OHOS libc++）
- 状态: built

## 这是什么库

tiv = Terminal Image Viewer（Stefan Haustein / Aaron Liu），用 24-bit RGB ANSI 转义序列配合
Unicode 半块字符（每个字符格 4x8 像素）在现代终端里渲染图片。2024-02-01 上游开始把源码
拆成无依赖的库文件，本包对应的 tag v1.2.1 仍是单文件 `src/tiv.cpp` 的形态。

- 上游仓库: https://github.com/stefanhaustein/TerminalImageViewer
- 许可证: Apache-2.0 OR GPL-3.0-or-later（上游 LICENSE 明确双许可）
- 硬依赖: CImg（图像 IO 与像素运算），tiv.cpp 第 46-47 行 `#define cimg_display 0` 后 `#include "CImg.h"`

## 编译步骤

上游 tarball 结构：`LICENSE README.md snapcraft.yaml terminalimageviewer.rb src/{Makefile,tiv.cpp,CImg.h} src/java/ .github/`

配方在 `build()` 里做的事：

```bash
# 1) 用制品仓 cimg/3.6.6 的头文件覆盖 tarball 自带的 CImg.h 3.3.1
#    （上游 Makefile 的 `tiv.o: CImg.h` 规则要求头文件与源码同目录）
cp <cimg/3.6.6 include>/CImg.h <source_folder>/src/

# 2) 在 src/ 目录里调 make（R33：从 Conan conf 取 CXX，-j1）
make -j1 CXX="/data/service/hnp/bin/clang++" CXXFLAGS="-O2"
# => /opt/lpk-fixed/clang++ -O2 -std=c++2a -Wall -fexceptions   -c -o tiv.o tiv.cpp
# => /opt/lpk-fixed/clang++ -pthread tiv.o -o tiv

# 3) 打包
cp src/tiv <package_folder>/bin/tiv
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make: *** No targets specified and no makefile found` | Makefile 在 `src/` 子目录里，tarball 顶层没有 makefile | `build()` 的 cwd 指向 `os.path.join(self.source_folder, "src")`，`package()` 的 copy 源同样指到 `src/` |
| 2 | `No rule to make target 'CImg.h', needed by 'tiv.o'` | Makefile 里 `tiv.o: CImg.h` 是显式依赖，要求头文件与 .cpp 同目录 | 从 `self.dependencies["cimg"].cpp_info.includedirs[0]` 取头文件（不 glob conan 缓存），`copy()` 进 `src/` 覆盖 tarball 自带的 3.3.1 版本 |
| 3 | CImg 3.3.1 vs 制品仓 3.6.6 版本不一致 | 上游 tarball 打包了自己的 CImg.h 快照（`cimg_version 331`），落后制品仓两个小版本 | 用制品仓 3.6.6（`cimg_version 366`）替换。上游只用 `CImg<T>` 基础类型与 `draw_image`，API 在 3.x 内稳定，实测编译与运行均正常 |
| 4 | `-fpermissive` 是 GCC 专有选项 | Makefile 里 `CXXFLAGS ?= -O2 -fpermissive`，clang 不认这个 flag | 命令行传 `CXXFLAGS="-O2"` 覆盖 `?=` 的默认值。Makefile 里 `override CXXFLAGS += -std=c++2a -Wall -fexceptions` 仍会追加，所以最终是 `-O2 -std=c++2a -Wall -fexceptions` |
| 5 | `-std=c++2a` 与 profile 的 `cppstd=17` 不一致 | Makefile 硬编码 `-std=c++2a`（= C++20），profile 是 17 | 不改。tiv.cpp 用了 `std::filesystem`，C++17 已足够；`-std=c++2a` 由上游 Makefile 决定，属于上游行为，编译与运行均实测通过 |
| 6 | 编译有一条 `-Wunused-const-variable` 警告（`FLAG_24BIT`） | 上游定义了 `FLAG_24BIT` 但没在代码里用 | 仅告警，不影响构建，未改上游源码 |

## 源码修改

无补丁（patches_applied: []）。上游 `src/tiv.cpp`、`src/Makefile` 一字未改，唯一被替换的是
tarball 里那份自带的 CImg.h（换成制品仓 cimg/3.6.6 的副本，属于依赖引用而非源码补丁）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| cimg/3.6.6 | header-only | revision `c8ddfaeae3061d6a04d0d5d0bee97908`，OHOS arm64 二进制 `6b129b068851896169fae42d399fa922d239ce8a`（`conan list 'cimg/3.6.6:*' -r=ohpcd` 实测确认存在） |

CImg 是唯一硬依赖。tiv.cpp 顶部自带 `#define cimg_display 0`，所以不需要 X11，也不需要
在配方里注入任何宏。未定义 `cimg_use_png` / `cimg_use_jpeg`，因此 PNG/JPEG 解码未启用
（上游 README 说依赖 ImageMagick，但 v1.2.1 的源码里已经没有 ImageMagick 调用，实测
`grep -i magick src/tiv.cpp` 无命中）；PPM/PNM 是 CImg 内建格式，实测可正常渲染。

## 验证结果

`conan create`（本地 WSL 交叉编译到 OHOS arm64，profile `ohos-aarch64-lkyz`）退出码 0。

### 编译

```
tiv/1.2.1: RUN: make -j1 CXX="/opt/lpk-fixed/clang++" CXXFLAGS="-O2"
tiv/1.2.1: Calling build()
...
Package tiv/1.2.1:c574b31ea991644ad0d18aa188c67ebe62ecfc9e
```

### 产物

```
$ file <package_folder>/bin/tiv
ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked,
interpreter /lib/ld-linux-aarch64.so.1, with debug_info, not stripped

$ readelf -d bin/tiv | grep -E 'NEEDED|RUNPATH'
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
$ ls -l bin/tiv
5865496 bytes
$ sha256sum bin/tiv
0863a9fe863dd7ebaa1a6b513d80c75e3036a3eca2e1ad243f9582670c20609f
```

### 消费者测试（test_package/test.sh）

CI worker 是原生 aarch64 OHOS 设备，二进制直接执行（不用 qemu）。本地用同一份打包产物
（`/root/.conan2/p/b/tiv213042a553074/p`，binfmt/qemu 执行）做行为取证，行为一致。

2026-10-11 复核轮**重新实跑**的完整输出（34 条断言，逐条列出）：

```
[ok] tiv 在 PATH 中可执行: /root/.conan2/p/b/tiv213042a553074/p/bin/tiv
[ok] PATH 上的 tiv 就是依赖包 bin/ 里的文件 (/root/.conan2/p/b/tiv213042a553074/p/bin)
[ok] --help 有输出 (738 字节)
[ok] --help 打印版本横幅 v1.2.1
[ok] --help 打印 usage 行
[ok] --help 退出码 0 (= 0)
[ok] 无参数时打印 usage
[ok] 未知选项退出码 64 (EX_USAGE) (= 64)
[ok] 文件不存在退出码 66 (EX_NOINPUT) (= 66)
[ok] 24-bit 渲染有输出 (5079 字节)
[ok] 输出含 24-bit 背景色转义序列 (ESC[48;2;r;g;b)
[ok] 输出含 24-bit 前景色转义序列 (ESC[38;2;r;g;b)
[ok] 输出以 ESC[0m 复位颜色
[ok] 输出含 Unicode 下半块字符 U+2584 (e2 96 84)
[ok] -h 4 输出 4 行 (= 4)
[ok] -h 8 输出 8 行 (= 8)
[ok] -w 10 与 -w 20 输出字节数不同（缩放生效: 1995 vs 5080）
[ok] --256 渲染有输出 (3103 字节)
[ok] --256 输出含 256 色背景序列 (ESC[48;5;N)
[ok] --256 输出含 256 色前景序列 (ESC[38;5;N)
[ok] --256 模式不再使用 24-bit 序列
[ok] 条纹图默认模式渲染有输出 (63 字节)
[ok] -0 模式渲染有输出 (66 字节)
[ok] 条纹图默认模式选中最佳块字符 U+2582
[ok] -0 模式不选最佳块字符
[ok] -0 模式固定用 U+2584 (e2 96 84)
[ok] -0 模式仍输出 24-bit 序列
[ok] 条纹图默认模式未退化成固定 U+2584
[ok] 灰度图渲染有输出 (80 字节)
[ok] 灰度图前景色三通道相等 (R=40 G=40 B=40)，spectrum==1 → 3 通道复制生效
[ok] 灰度图背景色三通道相等 (R=72 G=72 B=72)
[ok] dir 模式渲染 gallery 退出码 0 (= 0)
[ok] dir 模式渲染有输出 (6076 字节)
[ok] dir 模式输出含 24-bit 序列
--- 结果: 34 passed, 0 failed
```

> ⚠️ **本节在 2026-10-11 前是 26 条**。2026-10-11 03:13 的提交 `4b22339c30`
> （「堵住 test_package 的 6 条真空转绿断言」）新增了 7 条 `assert_nonempty` 输出非空
> 守卫与 1 条 `TIV_PKG_DIR` 来源比对（合计 +8），但**没有同步更新本节**，
> 于是 notes.md 长期挂在 26，而 `test_package/MANIFEST.yml`（`assertion_count: 34`）
> 与 PR 描述（34）都已是 34 —— 三处不自洽。本轮已改正。

### 断言分组（按 test.sh 行号逐条点算，与 34 自洽）

| 组 | 条数 | 行号 |
|----|------|------|
| A 来源与启动 | 2 | 113, 126 |
| B 版本与用法 | 4 | 134, 135, 139, 143 |
| C 错误路径 | 2 | 147, 150 |
| D 24-bit 渲染 | 4 | 156, 157, 158, 159 |
| E 缩放与行数 | 3 | 164, 165, 171 |
| F 色彩模式与块字符 | 8 | 180, 181, 182, 215, 216, 217, 218, 219 |
| G 灰度与 dir | 4 | 232, 242, 258, 261 |
| H 反假绿守卫（`assert_nonempty`） | 7 | 133, 155, 179, 213, 214, 225, 260 |
| **合计** | **34** | |

分组必须**互斥**才能相加。H 组是独立的一组（7 条非空守卫），不能既算进 A/D/F/G
又单列一遍 —— 那样合计会虚增到 40。

### 空壳测试自检（L1e 对抗）

两道互相独立的反证：

**(a) 门禁自带 L1e（移走 `bin/` 后 `conan test` 必失败）**

```
[ok] L1e: Negative test confirmed — test genuinely depends on tiv
```

**(b) 五段式反向破坏实验**（2026-10-11 复核轮在 head `4b22339c30` 上重跑，
每段复原后校验原件 sha256 逐字节一致）

原件：`size=5865496 sha256=8a6aed48c7ba25c062dcbcaec09ee68cece8083efc2402607428928c9b40abb0`

| 轮次 | 破坏动作 | rc | 结果 |
|------|----------|----|------|
| 1 基线 | — | 0 | `34 passed, 0 failed` |
| 2 **0 字节桩** | `: > bin/tiv`（`[ -f ]`/`[ -x ]`/PATH 守卫全部仍为真） | 1 | `7 passed, 26 failed` |
| 3 复原 | 拷回原件 | 0 | `34 passed, 0 failed`，sha256 与原件一致 |
| 4 **架构破坏** | ELF `e_machine` `b700`(aarch64) → `3e00`(x86-64) | 1 | `6 passed, 27 failed` |
| 5 复原 | 拷回原件 | 0 | `34 passed, 0 failed`，sha256 与原件一致 |

> `7 + 26 = 33 ≠ 34` 不是算错：灰度段是 `if [ -n "$FG" ]` 分支，命中时产出
> 2 条断言（前景三通道 + 背景三通道），未命中时只产出 1 条
> （`灰度图渲染输出里找不到 24-bit 前景色序列`）。破坏轮走到的是后者，
> 故当轮实跑 33 条。`6 + 27 = 33` 同理。

破坏轮仍 PASS 的断言（0 字节桩轮 7 条），恰好全是**无法验证执行行为**的那几类：

```
[ok] tiv 在 PATH 中可执行                    ← 定位守卫（0 字节仍 [ -x ]）
[ok] PATH 上的 tiv 就是依赖包 bin/ 里的文件    ← 来源守卫（只比路径，不执行）
[ok] --help 退出码 0 (= 0)                   ← 0 字节文件被当空 shell 脚本执行，返回 0
[ok] --256 模式不再使用 24-bit 序列           ← 反向断言（空串不含 needle）
[ok] -0 模式不选最佳块字符                    ← 反向断言
[ok] 条纹图默认模式未退化成固定 U+2584         ← 反向断言
[ok] dir 模式渲染 gallery 退出码 0 (= 0)      ← 同 --help 退出码
```

它们各自紧邻的输出非空守卫在**同一次运行里已经全部转红**（`--help 有输出:
捕获到的输出是空的` / `24-bit 渲染有输出: 捕获到的输出是空的` 等），
所以这 7 条的 PASS 不构成空壳。

## 上游测试用例盘点（R51）

- 上游 tag 归档里**没有** `tests/` 目录，`src/Makefile` 只有 `all` / `install` / `clean`
  三个目标，没有 `check` / `test`。
- 因此上游自动化测试用例数 = **0**，如实声明，不虚报。
- 适配后测试用例数 = **34** 条断言（全部为消费者侧补全），见上表。
- 34 项断言里没有一条是靠"环境不具备"跳过的；`MANIFEST.yml` 里
  `upstream_test_in_build: false` 对应的原因是上游无测试可跑，不是环境问题。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/tiv | 终端图像查看器可执行文件（5.6 MB，OHOS arm64 PIE） |

## 注意事项

- tiv 用 `ioctl(STDOUT_FILENO, TIOCGWINSZ)` 取终端尺寸。输出被重定向到文件/管道时
  ioctl 失败，会回退到 80x24 并往 stderr 打一行 `Warning: failed to determine most
  reasonable size, defaulting to 80x24`。这是上游设计，测试里据此用 `-w`/`-h` 显式指定尺寸。
- 未启用 `cimg_use_png` / `cimg_use_jpeg`，**PNG/JPEG 文件打不开**（会抛 CImgIOException）。
  PPM/PNM 系列可用。如果后续要在 OHOS 上支持 PNG，需要给 cimg 加 libpng/libjpeg 依赖并
  在配方里加编译宏，本轮不做（属于功能扩展，不是适配缺口）。
- 打包产物带 debug_info（上游 Makefile 没加 `-g`，但 clang 默认在 `-O2` 下仍生成部分调试信息）。
  体积 5.6 MB 对命令行工具偏大，但删 strip 属于超出适配范围的行为改变，未做。
- Makefile 里 `INSTALL ?= install`，OHOS 上没有 coreutils `install`，所以配方没用
  `make install`，改为在 `package()` 里直接 `copy()` 二进制（与 archives/a/aa3d 一致）。
- `exports_sources` 声明了 `patches/*` 但 `patches/` 目录不存在且 `conandata.yml` 里
  `patches: []` 为空列表 —— 这是 L0q 门禁要求的字面量，实际不导出任何补丁。

---

## 2026-10-11 复核轮（回应行级意见「⚠ test_package 需复核」）

### 根因

该意见指向 2026-10-11 10:48 的平台审查结论（`VERDICT=FAIL`，只剩 rule6 / rule7）。
逐条对照后，**代码层面本轮复核没有发现新的空壳断言**——head `4b22339c30` 的
`test.sh` 已堵住上一轮的 6 条真空转绿断言。但复核过程中查出**两处文档口径不自洽**，
正是「需复核」这条意见会反复被提出来的原因：

| # | 位置 | 症状 | 根因 | 处置 |
|---|------|------|------|------|
| 1 | 本文件「消费者测试」小节 + 「上游测试用例盘点」 | 长期写 **26** 条断言、贴 26 行 `[ok]` 输出 | 03:13 的提交 `4b22339c30` 把断言从 26 加到 34（+7 条 `assert_nonempty`、+1 条 `TIV_PKG_DIR` 来源比对），**只改了 test.sh 和 MANIFEST.yml，漏改 notes.md** | 本轮按实跑输出整段重写为 34 条，并补上互斥分组表 |
| 2 | PR 描述「34 条断言分七组」表 | A~H 八行相加 = **40**，与同段声明的总数 34 矛盾；且 H 组写「6 份捕获输出」 | H 组（`assert_nonempty` 守卫）既被算进 A/D/F/G 的条数里、又单列一次，重复计数；`assert_nonempty` 调用点实为 **7** 处（`--help` / 24-bit / `--256` / 条纹默认 / 条纹 `-0` / 灰度 / dir），PR 正文写 6 | PR 描述改为互斥分组 A=2 B=4 C=2 D=4 E=3 F=8 G=4 H=7，合计 34 |

> 教训：**加断言时必须同步三处计数**——`test_package/MANIFEST.yml` 的
> `assertion_count`、PR 描述的分组表、本文件的验证小节。上一轮只改了前两处。

### 本轮验证证据（全部为本地实跑，非引用历史结论）

环境：WSL 原生盘 `/root/wt-tiv-gate`（detached worktree @ `4b22339c305beb...`，
不在 `/mnt/*` 上），`zsh ci/conan/build_and_test.sh`，profile `ohos-aarch64-lkyz`。

**门禁全绿**：

```
[ok] v1.2.1.tar.gz (525KB) via mirror 1
--- 结果: 34 passed, 0 failed
[ok] tiv/1.2.1 — conan create passed
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[ok] L5: bin/ has content
[ok] L1e: Negative test confirmed — test genuinely depends on tiv
[ok] L2: tiv --help OK
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: tiv --help OK
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
  Failed:  0
  Pass rate: 100.0% (1/1)
[step] All packages built and tested successfully ✅
```

**五段式反向破坏实验**（原件 `sha256=8a6aed48c7ba25c062dcbcaec09ee68cece8083efc2402607428928c9b40abb0`）：

```
[base]    rc=0 | 34 passed, 0 failed
[zero]    rc=1 | 7 passed, 26 failed     # : > bin/tiv
[restore1] rc=0 | 34 passed, 0 failed    # sha256 与原件一致
[arch]    rc=1 | 6 passed, 27 failed     # e_machine b700 -> 3e00
[restore2] rc=0 | 34 passed, 0 failed    # sha256 与原件一致
SHA256_MATCH=yes
```

> 破坏轮的失败原因指向被破坏的产物本身（`捕获到的输出是空的` /
> `输出里找不到 'ESC[48;2;'` / `期望 '64', 实际 '0'`），
> 不是 `Conanfile not found` 之类无关错误。

### 本轮改动

- `archives/t/tiv/1.2.1/notes.md`：本文件（26 → 34，补分组表与破坏实验）。
- **配方 / test.sh / MANIFEST.yml / conanfile.py 一行未改** —— 复核结论是代码侧无新缺陷。

---

**编译结束**: 2026-10-05
**最后复核**: 2026-10-11（门禁 L0/L1/L2/L4/L5 全绿，34/34，五段式反向破坏复现）
**最终状态**: built