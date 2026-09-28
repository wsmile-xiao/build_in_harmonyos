# freetype 2.14.3.2.1 适配笔记（HarmonyOS PC）

> 真机验证在 2.14.3.2 命名下完成；2.14.3.2.1 仅版本号递增（规避与
> #12614 同版本任务撞车），配方/补丁/探针内容逐字节一致。


## 版本说明（R37）

main 已有 `2.14.3`（2026-07-07）与 `2.14.3.1`（2026-08-22）两版归档且均已合入 main，
制品仓已有同名版本 → 本版递增为 **2.14.3.2.1**。上游源码仍为 freetype 2.14.3 发行包
（Debian sid 官方再打包 orig 归档，sha256 与 .dsc PGP 签名记录核对一致）。

## 编译环境

- 构建系统: autotools（configure + make）
- 编译器: clang（/data/service/hnp/bin 工具链）
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 构建策略: **make -j1 串行**（真机 GNU Make 4.4.1 并行编译会静默失败，无诊断退出）

## 构建步骤

autotools；禁全部可选依赖（zlib/bzip2/png/brotli/harfbuzz——harfbuzz 与 freetype
循环依赖，须先建无 hb 版）→ 零外部依赖干净节点。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 临时目录创建失败 | HMDFS umask 077 目录不可写（E011 类） | patches/0001：configure 临时目录改用 `${TMPDIR-/tmp}` + umask 022 |
| 2 | configure: error: cannot guess build type | 设备 uname -s=HarmonyOS，config.guess 不认 | patches/0002/0003：E007 官方补丁，config.guess 识别 HarmonyOS 输出 aarch64-unknown-linux-ohos，config.sub 接受 ohos-linux |
| 3 | builds/unix/detect.mk 用默认 cc 而非 clang（CI #29062 Error 77 先例） | freetype autotools 工具检测逻辑 | generate() 注入 CC/CXX/LD/AR/RANLIB/STRIP/NM + SHELL/CONFIG_SHELL 环境变量（libxext 先例） |
| 4 | 消费方(fontconfig/cairo) freetype2 版本判 2.14.3.2.1 < 21.0.15 失败 | freetype2.pc 的 Version 是 libtool 号 26.6.20（version_info=26:6:20），conan 默认写 recipe 版本 | cpp_info.set_property("system_package_version","26.6.20") |
| 5 | 旧版探针仅 dlopen 空壳，无 API 功能验证 | — | 重写消费者探针：真实链接 libfreetype.so + 嵌入微型 TTF 全链路渲染验证（18 断言） |
| 6 | savannah/sourceforge 直连下载易截断、CI 可达性无保证 | 网络环境 | 源改用 Debian sid orig 归档（USTC + deb.debian.org 双镜像，CI 已实证可达） |
| 7 | 真机 configure: Permission denied / Error 126 | HMDFS 用户存储禁止直接 exec shebang 脚本（与 x 位无关、chmod 不生效 E046 同源，实测 `sh 脚本` 可用） | 全链路解释器调用：配方 build() 改为 `sh configure` 显式调用（复刻 conan Autotools 默认参数）；0004 detect.mk 两条 configure 调用改 `$(SHELL)` 前缀；0005 LIBTOOL 改 `$(SHELL) $(FT_LIBTOOL_DIR)/libtool`（libtool 官方标准形式，上游 aclocal 本就如此）；INSTALL 用 toybox ELF（PATH 加 /system/bin，避免 install-sh 脚本）。config.guess/config.sub/config.status 上游本身经 $SHELL 调用，无需改 |

## 源码修改

patches/ 共 5 个（全部 portability 类型，均已在本地对发行包树 `git apply --check` 验证干净）：

- 0001-builds-unix-configure.patch — configure 临时目录 TMPDIR + umask 022
- 0002-builds-unix-config.guess.patch — config.guess 识别 HarmonyOS（E007）
- 0003-builds-unix-config.sub.patch — config.sub 接受 ohos-linux（E007）
- 0004-builds-unix-detect-mk-shell-configure.patch — detect.mk 两条 configure 调用经 $(SHELL)（HMDFS 禁直接 exec 脚本）
- 0005-builds-unix-libtool-shell.patch — LIBTOOL 用 $(SHELL) 前缀（与 libtool 官方标准形式一致），DISTCLEAN 同步改裸路径

## 依赖版本

- 无 conan 依赖（零外部依赖叶子）

## 上游测试清点与执行情况

上游发行包 `tests/` 目录共 4 个文件：
`issue-1063/main.c`（回归测试）、`meson.build`（测试声明）、`README.md`、
`scripts/download-test-fonts.py`（测试字体下载脚本）。

- 可执行测试 = **1 个**（issue-1063，加载 As.I.Lay.Dying.ttf 对码位 59..170 逐字形 FT_Load_Glyph）
- 无法执行原因（环境限制）：
  1. 测试数据字体 `tests/data/` 不在发行包内，需 `download-test-fonts.py` 联网下载；
  2. 该测试仅 meson 集成，本配方走 autotools；
  3. 离线构建环境。
- 等价覆盖：消费者探针以嵌入字体执行同语义码位循环（59..170 全量 FT_Get_Char_Index +
  FT_Load_Glyph 无错误），见 test_package/test.c 断言 16。
- 另注：`src/tools/test_afm.c / test_bbox.c / test_trig.c` 为内部工具程序（引用 internal 头，
  autotools 默认不构建），不计入测试套件。

## 验证结果

真机（HarmonyOS PC，aarch64，ohos 原生构建）2026-09-26 实测：

- conan create . --build=missing -pr:h ~/.conan2/profiles/ohos-aarch64 ✅ 全流程通过
- 消费者探针 18/18 全绿：初始化 → 版本一致（2.14.3 == 编译期宏）→ 内存加载嵌入 TTF
  → 字形/编码映射（'A'==1、未映射 'Q'==0）→ Load/Render 光栅化出墨（>50 非零像素）
  → advance.x>0 → issue-1063 等价码位循环（59..170 零错误）→ 资源释放
- 包结构核对：include/freetype2/ft2build.h、lib/libfreetype.so{,.6,.6.20.6}、
  lib/pkgconfig/freetype2.pc 均落位正确
- 上游 issue-1063: 环境限制不执行（数据字体包外+仅 meson 集成，等价覆盖见上）
- 注：首轮真机失败两例均已修复（HMDFS 脚本 exec 被拒 → sh 全链路；prefix 与
  DESTDIR 叠加路径翻倍 → 改回 conan 默认 --prefix=/）

## 软件级文件

- 版本索引 manifest.yaml 已新增 2.14.3.2.1 条目
