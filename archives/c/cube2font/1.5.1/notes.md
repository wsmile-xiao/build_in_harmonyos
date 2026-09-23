# cube2font 1.5.1 适配笔记

## 编译环境

- 构建系统: makefile（上游 `src/Makefile` 的 `cube2font` 目标）
- 编译日期: 2026-09-11
- 编译器: clang 15.0.4 / `/data/service/hnp/bin/clang++`（target `aarch64-unknown-linux-ohos`）
- profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0、arch=armv8、cppstd=17、Release）
- 状态: built

## 源码与版本

cube2font 没有独立发行版：它以 `src/shared/cube2font.c`（556 行、19 KB、单翻译单元、无自带头文件）的形式随 Red Eclipse（Cube Engine 2）引擎仓库发布。因此源码取上游 tag：

| 项 | 值 |
|---|---|
| URL | `https://github.com/red-eclipse/base/archive/refs/tags/v1.5.1.tar.gz` |
| sha256 | `a33168040ff9cfbf501f0ee742a4d1f708d4781a643501a5507ba128d0e58ee3` |
| 大小 / 顶层 | 10840549 B / `base-1.5.1` |
| 构建输入 | `src/shared/cube2font.c`（默认 `all` 目标会连带 SDL/X11 客户端与 enet 服务端，本包不构建） |

版本锚定证据：Debian 源包 `cube2font 1.5.1-1` 的 `orig.tar.xz` 即由该 tag 重打包，
`cmp` 实测 `src/shared/cube2font.c` 与 `src/Makefile` 与官方 tarball **逐字节一致**
（`cube2font.c` sha256 `1b8ab7593e90182e5bfdd73fc1ba8e20ba135b4b9efef08655efae6ed321b308`），
且 Debian `debian/watch` 指向同一 GitHub 仓库，故 1.5.1 是唯一权威版本点。

## 编译步骤

配方 `build()` 实际执行的命令（`reports/conan-create.log` 中 `RUN:` 行原文）：

```text
make -j1 cube2font PLATFORM=aarch64-unknown-linux-ohos \
  CXX=/data/service/hnp/bin/clang++ \
  PKG_CONFIG=/data/service/hnp/bin/pkg-config \
  CXXFLAGS="$(/data/service/hnp/bin/pkg-config --cflags zlib) -O3 -fomit-frame-pointer -ffast-math" \
  LDFLAGS="$(/data/service/hnp/bin/pkg-config --libs zlib)"
```

工作目录 `<source_folder>/src`；`.pc` 由配方 `generators = "PkgConfigDeps"` 生成，
`PKG_CONFIG_PATH` 指向 `self.generators_folder`（`conanbuild` 环境下执行）。
`CXXFLAGS` 在命令行上重述上游 `-O3 -fomit-frame-pointer -ffast-math`：命令行赋值会覆盖
`src/Makefile` 第 6 行，不重述就会丢掉上游优化档（Debug 构建用 `-O0 -g`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `freetype-config: inaccessible or not found` → `shared/cube2font.c:7:10: fatal error: 'ft2build.h' file not found`（**第一条真实错误**） | `src/Makefile:235/238` 用 `freetype-config` 反引号探测 FreeType 编译/链接参数；该脚本自 FreeType 2.9.1 起被上游删除，Conan 发行包也不提供 | 补丁 `0001-makefile-use-pkg-config-for-freetype.patch` 把两条规则改为 `$(PKG_CONFIG) --cflags/--libs freetype2`，`.pc` 用消费方 `PkgConfigDeps` 生成（**不可**指向依赖包自带 `.pc`，其 `prefix=/`） |
| 2 | 每次展开 `PLATFORM` 都打印 `gcc: No such file or directory` | `src/Makefile:9` 的 `PLATFORM= $(shell gcc -dumpmachine)`，OHOS 工具链无 gcc | 配方在 make 命令行传 `PLATFORM=aarch64-unknown-linux-ohos`；命令行变量优先于文件内赋值，探测完全不执行（无补丁） |
| 3 | `-lz` 找不到 zlib 头与库 | 上游链接行硬编码 `-lz` 无 `-L`；OHOS zlib 包是静态库（只有 `libz.a`） | 配方把 `pkg-config --cflags zlib` / `--libs zlib` 注入 `CXXFLAGS` / `LDFLAGS`（`-L` 与规则尾部的 `-lz` 配合完成链接） |
| 4 | 测试字体全部字形为空时转换「成功」但没有任何 PNG | 打包启发式 `if(rh > 0) numtex++`：整页无 ink 时 `numtex` 保持 0，只写 `.cfg` | 测试字体把**每个**码位都映射到带真实轮廓的字形（`make_test_font.py` 的 `GLYPH_A`），并在断言里核对像素数与字符框 |

第一条真实错误的原始输出（探索期在未打补丁的上游树上设备实测复现）：

```text
/bin/sh: freetype-config: inaccessible or not found
shared/cube2font.c:7:10: fatal error: 'ft2build.h' file not found
    7 | #include <ft2build.h>
make: *** [Makefile:235: shared/cube2font.o] Error 1
```

## 源码修改

`patches/0001-makefile-use-pkg-config-for-freetype.patch`（802 B，patch_ng strip=1 实测应用成功）：

1. 新增 `PKG_CONFIG?= pkg-config`（可用命令行变量覆盖，配方传绝对路径）
2. `shared/cube2font.o` 编译规则：`` `freetype-config --cflags` `` → `` `$(PKG_CONFIG) --cflags freetype2` ``
3. `cube2font` 链接规则：`` `freetype-config --libs` `` → `` `$(PKG_CONFIG) --libs freetype2` ``

未改动 SDL 客户端规则（Debian 同名补丁中的 `sdl-config → pkg-config sdl` 两行）：本包不构建
客户端目标，改动无实测依据。未改上游测试（上游无测试）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| freetype | 2.14.3 | 运行时动态链接 `libfreetype.so.6`（ohpcd 发行二进制） |
| zlib | 1.3.1 | 静态链接 `libz.a`（OHOS 包为静态库，满足 R26 系统同名库静态要求） |

能力边界：ohpcd 的 freetype 未启用 zlib/bzip2/png 后端（`readelf -d libfreetype.so.6` 的
`DT_NEEDED` 只有 `libc.so`），因此 FreeType 读不了 WOFF/gzip 压缩字体容器；未压缩 TTF/OTF
不受影响，本包全部验证均使用未压缩 TTF。

## 验证结果

采信轮：`python3 scripts/ohc-run.py conan-verify cube2font 1.5.1`。该轮的干净构建日志由工具写入
`reports/conan-create.log`，但**收尾阶段 `finish` 内嵌重跑会用缓存命中轮覆盖它**（已知行为）：
覆盖后只剩 test_package 段，不再含 `Calling build()` 与 `RUN: make`，行数明显少于采信轮。
采信轮原件（**184 行 / 13453 B**，含 `Calling build()`、`RUN: make` 与上游构建段）已按 workflow 第 7.2 节
在 `conan-verify` 之后、`finish` 之前留存副本（该副本不再被任何后续轮次改写，故按哈希引用）：

- 副本 sha256（两次独立采信轮，除 conan 缓存目录名与时间戳的 12 行外逐行相同；均为 13453 B / 184 行，记录日志，任务私有目录，不入库）：
  `58828bd4803ee98c4fc00744d4d6542728afcb4c504cdba60d8373270d8e0e19`（4fbf3a0 轮）、
  `5bea0f40c5002620f2a33d86547f0e56401ddcb0f5fe4fdef366eba0b4c07bd3`（本 SHA 轮）
- 仓库内可核对的长日志：`reports/w3-local-ci.log`（本地 CI 模拟，同为干净构建，含 `RUN: make` 与
  test_package 实测段），按可搜索标记定位结论：`L0_RESULT=pass: all checks passed`、`KC_ERRORS=0`、
  `JC_RESULT=pass`、`✅ cube2font test_package PASSED`；该文件每轮 W3 都会重写，字节级 sha256
  随轮次变化，故不按哈希引用

采信轮与 W3 的关键行（两份日志的 `RUN: make` 行逐字符相同）：

```text
G1 PASS / G2 PASS（conan create 干净构建）/ G3 PASS
G4 与 L2/L4/L5 工具因缓存布局不匹配跳过 → 人工补测见 reports/conan-verify-supplement.md
test_package：ASSERTIONS: 11 / ASSERTIONS: 26 + test.sh 3 项 = 40/40 PASS
plain    : 249 字符 → 1 张 256x256 PNG，19173/19173 字符框内像素全部有 ink（逐点吻合）
bordered : 249 字符 → 3 张 512x512 PNG（99/99/51），257964/258960 落在字符框内（描边圆角）
✅ cube2font test_package PASSED
```

上述计数在覆盖后的 `reports/conan-create.log`（仅 test_package 段）中同样可复核：该文件的 test_package
段与采信轮逐行相同（`ASSERTIONS: 11` / `ASSERTIONS: 26`、像素计数一致）——两轮 test_package 结果一致，
正是构建输入未变的旁证。

产物安全属性（人工补测，标注 `readelf` 实测）：`DYN (PIE)`、`GNU_STACK RW`（NX）、
`GNU_RELRO`、`FLAGS BIND_NOW`、`FLAGS_1 NOW PIE`，无 RPATH/RUNPATH。

## 交付物

| 文件 | sha256 | 说明 |
|------|--------|------|
| `bin/cube2font` | `9c21a22d10322ceae203eda2b225ab89dc59e291845a45369631d7630c615391` | 命令行工具本体 |
| `share/man/man1/cube2font.1` | `b2f780e0fbde0544c7ba4899d19bd813fc9b33a303429dc196df34ce383cde48` | 上游 man 页 |
| `licenses/license.txt` | `874a7f04aa896b89addf4105eb691bae3bc96c7706cb9aaa97b213c322666fce` | Red Eclipse / Cube 2 的 ZLIB 许可 |

两轮独立 `conan create`（裸 ref 与 `@ohpcd/stable`）产出的 `conanmanifest.txt` 中
`bin/cube2font` 摘要相同（`0d0cdaba6a94e848827bd42ce6ef5e06`），构建可复现。

## 注意事项

- 上游没有测试套件（`src/Makefile` 无 `test`/`check` 目标、源码树无 `test/`、Debian 源包无
  autopkgtest），因此本包的上游用例数为 0；`test_package` 的 3 个用例是本包新增的真实转换测试，
  计数与上游分栏统计。
- `src/shared/cube2font.c` 是 C 文件，但上游用 `$(CXX)` 编译（clang++ 会给出
  `treating 'c' input as 'c++'` 弃用警告后正常编译）；任务卡语言为 C++，保持一致，未改成 C 编译。
- 依赖包自带 `.pc` 的 `prefix=/` 陷阱与修复模式已沉淀为知识库草稿 `E572`。
