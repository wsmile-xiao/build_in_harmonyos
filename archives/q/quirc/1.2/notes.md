# quirc 1.2 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-09-12
- 编译器: clang（OHOS aarch64，/data/service/hnp/bin/clang，profile 提供）
- 状态: built（conan-verify 通过）
- 任务: 平台任务号 7316；分支 feat/quirc-1.2；worktree ~/qzy/GLM-14-quirc-1.2
- 上游: https://github.com/dlbeer/quirc tag v1.2
  SHA256=73c12ea33d337ec38fb81218c7674f57dba7ec0570bddd5c7f7a977c0deb64c5
  （codeload.github.com 与 github.com/archive 两个官方端点字节一致，实测）

## 编译步骤

配方（conanfile.py）在 build() 中直接调用上游 Makefile：

```bash
make libquirc.a [libquirc.so.1.2] -j1 \
    CC=<conf:tools.build:compiler_executables:c> AR=llvm-ar RANLIB=llvm-ranlib \
    SDL_CFLAGS= SDL_LIBS= OPENCV_CFLAGS= OPENCV_LIBS= \
    CFLAGS="-O2 -fPIC" LDFLAGS=""
```

- 只构建库目标（libquirc.a / libquirc.so.1.2），不构建默认目标 all（含需
  libjpeg/libpng 的 qrtest 与需 SDL 的 demo）。
- `package()` 手工 copy（上游 install 目标依赖 SDL demo，不可用）：
  lib/quirc.h → include/，libquirc.a / libquirc.so.1.2 → lib/；
  shared 时额外复制一份 libquirc.so（HMDFS 下用复制不用符号链接），
  供 -lquirc 链接解析，运行时 SONAME 仍为 libquirc.so.1.2。
- cpp_info.libs = ["quirc"]，os in ("Linux","OHOS") 时 system_libs=["m"]（R32）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 SDL 环境下 make 报 `/bin/sh: no closing quote`，编译命令行被注入大段 pkg-config 报错文本 | 上游 Makefile `SDL_CFLAGS := $(shell pkg-config --cflags sdl 2>&1)` 把 stderr（"Package sdl was not found..."）拼进 QUIRC_CFLAGS（C 编译行被污染；`--std=c++17` 属 QUIRC_CXXFLAGS 只影响 .cxx）（上游已知缺陷，pkg-config 输出重定向 2>&1） | 不打补丁，make 命令行显式传空变量 `SDL_CFLAGS= SDL_LIBS= OPENCV_CFLAGS= OPENCV_LIBS=`（命令行变量优先级高于文件内 `:=` 赋值） |
| 2 | qrtest（上游测试工具）需 libjpeg/libpng 与测试图片 | 上游 tests/ 是手动工具集，仓库不带任何测试图片素材 | 用制品仓已发布的 libjpeg-turbo/3.0.4 + libpng/1.6.39（+zlib/1.3.1）部署私有 prefix 构建 qrtest；测试图片用自研 QR 编码器生成（见下） |

## 上游测试清点与执行（R51 三步法）

**清点证据（N_static=0）**：
- `make -n check` → 无 check 目标；
- 源码树无 TEST_CASE()/add_test()/ctest/pytest 等任何测试注册宏（grep 清点 0 条）；
- tests/ 目录 = 3 个手动工具：qrtest.c（309 行，目录扫描解码器）、inspect.c（需 SDL+SDL_gfx 交互显示）、inspect_opencv.cxx（需 OpenCV）；
- 上游仓库不带任何测试图片素材。

**四维账本**：
- N_static = 0（无测试框架，静态清点 0 条注册用例）；
- N_registered = 0（无注册机制）；
- N_executed = 0（框架口径；无框架可执行）；
- 分类未执行说明：qrtest 本体已在设备**真实构建并运行**（见下），作为上游工具级补充证据，不计入框架口径；inspect.c/inspect_opencv.cxx 未执行——技术上依赖 SDL/SDL_gfx/OpenCV 交互图形环境，OHOS 无头构建环境不可用，且二者是可视化调试器不是测试断言程序；
- N_consumer = 1（test_package/test_quirc，18 条 API 断言）。

**qrtest 工具级实测（设备原生 OHOS aarch64）**：
- 依赖来自制品仓：libjpeg-turbo/3.0.4、libpng/1.6.39、zlib/1.3.1（conan install --build=never 全部命中预编译包）；
- 测试图片：上游不带素材，用自研 QR 编码器（Python，ISO/IEC 18004 byte 模式，
  RS 生成多项式经 ISO 18004 附录标准向量比对一致）生成 3 张 8-bit 灰度 PNG
  （v1-L/mask0 "quirc-1.2-ohos"、v1-M/mask1 "OHOS-QR-42"、v1-L/mask4 "HELLO-QUIRC-2026"）；
- 结果：`qrtest` 报 `3 files, 3 codes, 3 decoded (0 failures), 100% success rate`。

## 消费者测试（test_package）

test.c 以库使用者身份：内嵌 21x21 已知 QR 矩阵（v1/L/mask0，payload
"quirc-1.2-ohos"），按 4px/模块 + 4 模块静区渲染灰度图，经公开 API
quirc_new → quirc_resize → quirc_begin → quirc_end → quirc_count →
quirc_extract → quirc_decode 解码，断言：退出码 SUCCESS、payload 长度 14、
内容逐字节一致、version=1、ecc_level=L、mask=0、data_type=BYTE、网格 21、
quirc_strerror 非 NULL；另做全新实例全白图 → quirc_count==0 的行为测试
（quirc 实例跨 quirc_end 累积已识别码，负向测试须用新实例）；共 18 条断言，
失败退出码 1。conanfile.py 的 test() 用 bash 包裹执行（OHOS mksh
不能直接 exec ELF，沿用仓库 zlib 惯例），依赖 self.tested_reference_str。

## 源码修改

无补丁（patches 为空）。未修改任何上游文件；SDL 注入问题用 make 命令行
变量覆盖解决（见问题 #1）。

## 依赖版本

无（库本体零依赖；qrtest 工具级实测依赖 libjpeg-turbo/3.0.4、libpng/1.6.39、
zlib/1.3.1，均来自制品仓，不进入配方 requires）。

## 验证结果

```bash
# W3（conan create，OHOS aarch64 原生）
python3 scripts/ohc-run.py conan-verify quirc 1.2   # G0-G4/L2/L4/L5 全过
python3 scripts/ohc-run.py finish quirc 1.2 built
# qrtest（设备实测，工具级）
./qrtest <3 张生成 PNG 目录>  →  3 files, 3 codes, 3 decoded, 100%
```

## 注意事项

- 上游 Makefile 的 install 目标依赖 quirc-demo/quirc-scanner（SDL/v4l2），
  配方不可用 install，必须手工 copy。
- shared=True 时包内同时有 libquirc.so.1.2 与其副本 libquirc.so（无 SONAME
  冲突：编译未显式传 -Wl,-soname，SONAME 取自输出文件名 libquirc.so.1.2）。
- 库版本字符串：`version_db.c` 由上游生成脚本从 git describe 生成，tag 包内
  固化为 "Library version: 1.0"（qrtest 启动横幅所示），非适配问题。
- 本任务可复用知识（供路径 B 判断）：见 notes 同目录报告/主理收口的知识草稿主题
  「纯解码库（encoder-only upstream 缺失）如何构造真实消费者测试：自研最小 QR
  编码器 + ISO 标准向量校验 + 设备端 round-trip 定位」。
---

**编译结束**: 2026-09-12 04:30
**最终状态**: built
