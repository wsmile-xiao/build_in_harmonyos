# Test Report — povray 3.7.0.10

## 编译验证
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS 原生工具链)
- 构建系统: Autotools（GitHub tag 无预生成 configure，unix/prebuild.sh 生成）
- 编译状态: ✅ 成功（探索树 154 对象 0 error；配方构建见 G2）
- C++ 标准: -std=gnu++11（2013 年代码 auto_ptr/register/throw() 在 C++17 下报错，
  gnu++11 下 deprecated-but-available，零源码补丁）
- 最终 flags: -pipe -Wno-multichar -Wno-write-strings -O3 -ffast-math -std=gnu++11

## 平台补丁
无（零源码补丁）。E129 umask 修复在配方 build() 内联完成（对生成 configure 的
文本替换，不属源码补丁）。

## 平台修复
| 问题 | 修复方式 |
|------|----------|
| GitHub tag 无预生成 configure（unix/prebuild.sh 需 aclocal/automake/autoheader，CI worker 缺） | 配方 tool_requires automake/1.18 + build() 先跑 unix/prebuild.sh |
| 宿主 automake 安装损坏（@am_AUTOM4TE@ 占位符） | AUTOCONF/AUTOHEADER/AUTOM4TE/SED 显式指向 PATH 实际工具 |
| E129：autoconf 2.72 configure 内 `umask 077 && mktemp`，HMDFS setgid 使临时目录不可写（config.status 的 subs1.awk Permission denied） | build() 内联替换：去掉 umask 077（polyglot/pdfio/abiword 同款） |
| 2013 年 C++ 代码与 profile cppstd=17 冲突 | configure 参数 CXXFLAGS=-std=gnu++11（povray 把用户 CXXFLAGS 追加在自检 flags 后） |
| ohpcd boost 版本二选一矛盾（1.84.0 无 libboost_thread；1.91.0 头文件缺 flyweight） | 定案 boost/1.90.0.4（308 头含 flyweight + 12 静态库含 thread） |
| libjpeg/libtiff 未发布 ohpcd | NON_REDISTRIBUTABLE_BUILD=yes + --with-libjpeg=no --with-libtiff=no 干净降级；--without-openexr |
| E074: HMDFS jobserver fifo | make -j1 |
| install-data-local 污染 $HOME/.povray | make install 时重定向 HOME 到 build 目录 scratch |

## 依赖（最小依赖图 R1）
- boost/1.90.0.4（AX_BOOST_BASE + AX_BOOST_THREAD 硬性要求，thread/atomic/chrono/
  container/filesystem/program_options/regex/serialization/timer/wserialization 静态库）
- libpng/1.6.39（PNG 输出必需）
- zlib/1.3.1（png 隐含）
- 工具链: automake/1.18（tool_requires，仅构建期）
- 禁用: jpeg/tiff/openexr/X11 显示（OHOS 无 X，文件渲染不受影响）

## 上游测试说明
POV-Ray 3.7 Unix 构建系统只有【一个】check 目标：渲染 scenes/advanced/biscuit.pov
（320x240 多线程光追），make check 退出码 0 即通过。已在配方 build() 集成执行
（L1 上游测试）。无单元测试框架。

探索树实测：CHECK_RC=0，Trace Time 0.186s（20 线程），"POV-Ray finished"。

## Conan Verify (G0-G4)
| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | ✅ PASS |
| G1 配方完整性 | ✅ PASS |
| G2 conan create | ✅ PASS（干净构建：154 对象 0 error；make check 上游渲染测试通过；test_package 全断言通过） |
| G3 系统同名库隔离 | ✅ PASS（纯可执行包，无 lib/ 目录，R26 通过） |
| G4 产物完整性 | ✅ PASS |

报告: reports/conan-verify-report.md（Verdict: PASS，2026-09-03 20:46-21:04 两次验证，
首次 G2 因 test_package shutil.copy SameFileError 失败——test_type=explicit 下 test()
工作目录即 test_package/ 源目录，复制到自身报错；修复为临时目录输出后全绿）

## W3/CI 说明
- conan create 全流程证据：prebuild.sh 生成 configure → configure（E129 修复生效）→
  make -j1 154 对象 0 error → make check（biscuit.pov 320x240 渲染，Trace Time 0.192s，
  "POV-Ray finished"）→ make install（HOME 重定向）→ test_package 12 项断言全过
- test_package 快速复验（conan test，缓存包）：banner OK + 64x64 PNG (2591 bytes) RGB8
  + 场景库 colors.inc 从包内 share/povray-3.7/include 解析 OK

## test_package (R34)
- banner：povray --version 输出含 "Persistence of Vision" + "3.7.0.10"
- 真实渲染：test.pov（相机+光源+棋盘格平面+红球，#include colors.inc）→ 64x64 PNG；
  断言退出码 0（解析失败实测 RC=1）、PNG 魔数、IHDR 64x64、bit_depth=8、color_type=2(RGB)、
  渲染统计行 "Trace Time"、包内场景库布局（share/povray-3.7/include/colors.inc）
- 断言总数：12

## 交付物
- 产物: bin/povray（ELF arm64 musl 动态链接，仅依赖系统 libc++_shared.so/libc.so，
  boost/png/zlib 全静态打入）+ share/povray-3.7/{include,ini,scenes,scripts} +
  etc/povray/3.7/{povray.conf,povray.ini} + share/man/man1/povray.1
