# libbgcode 0.0-git20260521.6f4ad7c 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，需 CMake >= 3.12，C++17）
- 上游提交: prusa3d/libbgcode @ 6f4ad7c（2026-05-21，Fix MeatPack dropping comment lines with leading whitespace）
- 编译器: clang/clang++ 15（ohos-aarch64 profile，libc++，Release）
- 状态: built（配方完整；真机预检待 HMBS 回填）

## 编译步骤

conanfile.py 流程（conan create 在真机执行）：
1. `source()` 下载官方快照 tarball 并校验 sha256，同时下载 vendored 的 heatshrink 与 Catch2 上游 tarball 到子目录。
2. `generate()`：CMakeDeps 生成 boost/zlib 依赖配置（zlib 名称映射为 ZLIB::ZLIB，leptonica 同法）；heatshrink/Catch2 无 conan 节点，heatshrink_DIR/Catch2_DIR 指向 build() 内 vendor 构建的私有前缀；CMakeToolchain 打开上游测试、关闭 bgcode CLI、静态构建。
3. `build()`：apply 补丁 → 以自带 Makefile（conf 编译器，无 cmake）构建安装 vendored heatshrink 到私有前缀 → 以同一 conan_toolchain.cmake + 系统 cmake 构建安装 vendored Catch2 到私有前缀 → cmake configure → cmake build → `ctest --output-on-failure` 运行上游 8 个测试，仅解析 Testing/Temporary/LastTest.log 输出 HMBS_UPSTREAM_TEST_RESULT。
4. `package()`：cmake install 安装 3 个静态库与头文件（含生成的 export.h），并把 vendored heatshrink 档案与头文件一并装入本包（消费者经 heatshrink_dynamic/static 组件链接）。
5. test_package：两个消费者可执行文件同样走 ctest，输出 HMBS_TEST_PACKAGE_RESULT。

## 上游测试盘点（与官方一致口径 ctest_entries）

| 套件 | TEST_CASE | ctest 条目 |
|------|-----------|-----------|
| tests/core/core_tests.cpp | File transversal；Search for GCode blocks | 2 |
| tests/binarize/binarize_tests.cpp | MeatPackComments preserves indented comments；MeatPack removes indented comments when Flag_RemoveComments set | 2 |
| tests/convert/convert_tests.cpp | binary->ascii；ascii->binary；PS 2.8.1 binary->ascii；PS 2.8.1 ascii->binary | 4 |
| 合计 | 8 | 8 |

`upstream_test_total: 8`，`upstream_test_count_method: ctest_entries` 已写入 test_package/MANIFEST.yml。
测试数据（tests/data 内 6 个文件，随源码包发布，非空，转换测试含参照文件逐行比对与往返一致校验，不存在空文件比空文件式假绿）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | binarize 链接 heatshrink::heatshrink_dynalloc 失败 | 该目标名来自上游自带 deps/heatshrink 构建；registry heatshrink 只导出 heatshrink::dynamic/static | 补丁映射为 heatshrink::dynamic（HEATSHRINK_DYNAMIC_ALLOC=1，完全等价），见 0001；第 11 条起该目标改由本包内嵌的 vendored heatshrink 组件提供 |
| 2 | convert 链接 Boost::boost | 早期 conancenter boost 包目标名差异 | 仓库内 boost/1.90.0.4 原生导出 Boost::boost（含 nowide 头文件全树），convert 无需映射，保持原样，见 0001 |
| 3 | tests 要求 Boost COMPONENTS nowide 失败 | registry boost 均不编译 nowide 组件；测试仅用 boost::nowide::fopen，在 POSIX/OHOS 为头文件直通 | 去掉 COMPONENTS 请求，改链 Boost::boost；测试逻辑零修改，见 0001 |
| 4 | include(Catch)/catch_discover_tests 离线解析 | 上游纯 find_package(Catch2)，CI 沙箱禁网 | Catch2 v3.8.1 随配方 vendor（conandata catch2_source，build() 内构建安装到私有前缀，Catch2_DIR 指向该前缀；图中无 catch2 conan 节点），不改上游（见第 10 条） |
| 5 | 计数口径 | 禁止 stdout 正则数数与算术修补 | 上游与 test_package 计数唯一来源均为各自 LastTest.log；缺失或格式异常直接失败并给出 reason，不凑数字。2026-09-20 预检：stdout 显示 8/8 通过但 `_parse_ctest_log` 用 stdout 格式 `^N/M Test #K:` 正则去扫 LastTest.log（该文件只有 `N/M Testing:` 头与 `Test Passed.`/`***Test Failed.`  verdict 行，从无 `Test #K:` 行），误报 discovered=0；已改按头分母 `N/M Testing:` 取总数、verdict 短语计数（libwmime 同法，四短语单遍互斥相加、无回退覆盖），另补多根 LastTest.log 搜索与失败标记必带 reason（原先非全绿无 reason 会触发 KeyError）。本地合成日志自测 5 用例通过 |
| 6 | 真机预检在依赖阶段失败：boost 无二进制，bzip2/1.0.8 源码构建报 CMAKE_SYSTEM_NAME=HarmonyOS 未知 | conancenter boost 在 ohpcd 无本 profile（clang15/cppstd17/OHOS6.0/armv8）兼容二进制（1.85.0 与 1.84.0 两轮均复现），conan 回退源码构建 boost，连带构建 bzip2；bzip2 的 CMakeToolchain 默认映射 HarmonyOS，CMake 4.x 不认。只换版本号不能解决问题 | 已被第 8 条替代：放弃 conancenter boost 线，改用仓库内 boost/1.90.0（见第 8 条）；header_only 强制已移除 |
| 7 | 真机预检失败点前移：cmake/3.31.12 build() line 35 KeyError 'OHOS' | header-only 后 boost/bzip2 边已消除，但裸 zlib/1.3.1 仍解析到 conancenter 配方（预检 remote 顺序 conancenter 在前），其 tool_requires("cmake/[>=3.16 <4]") 拉入 cmake/3.31.12，该配方按 OS 键取预编译包，OHOS 无键；fceux/libcoverart/libgsf/c10t 同款已知模式 | 依赖改为仓库独有 zlib/1.3.1.1（与上游 1.3.1 同 tarball 的 -fPIC 静态重建，conancenter 无同版本，自动落 ohpcd autotools 配方，零 tool_requires，原生导出 ZLIB::ZLIB）；catch2/3.8.1 保持裸版本（mcfp/1.4.2 同款用法已合入）。但本轮复检发现 zlib 切换后 cmake 边仍在：conancenter boost/1.84.0 自身的 tool_requires cmake 是无条件的，header_only 无法消除，故需第 8 条换供方 |
| 8 | 同一 KeyError 'OHOS' 在 zlib/1.3.1.1 已就位后依然复现 | 上一周期假设 cmake 边来自 zlib 是错的：zlib/1.3.1.1 已就位但 cmake/3.31.12 仍被拉起；conancenter boost/1.84.0 的 tool_requires cmake 无条件存在，header_only 删不掉该边；且 i2pd 注释证实 boost/1.84.0 在 ohpcd 无发布 | 换供方路线：boost 改仓库内 boost/1.90.0（直编 Boost.Test、全量头文件、零 tool_requires），补丁改 Boost::nowide->Boost::boost，删除 header_only 强制；zlib/heatshrink/catch2 保持仓库内版本，依赖图无 conancenter 包 |
| 9 | 裸 boost/1.90.0 仍解析到 conancenter 并连带 bzip2/1.0.8 在 HarmonyOS 上 CMake 失败 | 上轮换供方方向正确但版本号选错：裸 1.90.0 在 conancenter 同样存在，预检按 remote 顺序优先命中 conancenter 配方（日志明示 Downloaded recipe revision cd8d66），其源码构建拉起 bzip2/1.0.8，而 bzip2 的 CMake 在 Platform/HarmonyOS 上直接配置失败；仓库内真正独有的 Boost 是带后缀的 1.90.0.4（b2 全树、零 tool_requires、导出 Boost::boost），只有后缀版本能像 zlib/1.3.1.1 一样强制落 ohpcd | 改为 boost/1.90.0.4：conanfile/manifest/README/notes 同步；补丁保持 Boost::nowide->Boost::boost 不变（1.90.0.4 同样导出 Boost::boost 且全树含 nowide）；configure() 注释同步 |
| 10 | 同一 KeyError 'OHOS'（cmake/3.31.12 build() line 35）在 boost/1.90.0.4 + zlib/1.3.1.1 已就位后依然复现 | 上一周期连续三轮换供方版本号（boost 1.84.0→1.90.0→1.90.0.4、zlib 1.3.1→1.3.1.1）均未收敛，按第 3 策略周期规则不得再换版本；重读源码与 CCI 配方原文确认被忽略的向量：裸 catch2/3.8.1 双远端共存且 CCI 配方含 build_requirements() tool_requires("cmake/[>=3.16]")，预检 conancenter 优先即命中 CCI 并拖入无 OHOS 条目的 cmake 工具包；heatshrink/0.4.1 虽也双远端但 CCI 配方无 tool_requires，故非本轮阻塞点 | 删边路线（非换版本）：删除 test_requires("catch2/3.8.1")，图中不再有 catch2 conan 节点；conandata 新增 catch2_source（URL/sha256 一字不差复用本仓 archives/c/catch2/3.8.1 条目的官方 GitHub 源），source() 解到 catch2-src 子目录，build() 先以同一 conan_toolchain.cmake + 系统 cmake（HMBS 注入 user.hmbs:cmake_path/HMBS_CMAKE，PATH 回退）配置构建安装到 build 内私有前缀（静态 + PIC + BUILD_TESTING=OFF + extras ON），generate() 的 Catch2_DIR 改指该私有前缀；上游 find_package(Catch2 3.8)/include(Catch)/catch_discover_tests 零修改，8 个上游用例与 test_package 2 检查保持全量 |
| 11 | 上轮 Catch2 删边生效（cmake KeyError 消失），失败指纹前移到 heatshrink/0.4.1 自身构建：`System is unknown to cmake, Platform/HarmonyOS` + `build() line 75 cmake.configure()` | 前次 vendor-Catch2 对其目标有效（本轮日志已无 cmake 工具包段，直接进入 heatshrink 构建）；新失败点是裸 heatshrink/0.4.1 双远端被预检解析到 CCI 配方——本地 0.4.1 配方用 basic_layout + 自带 Makefile 直接 make（无 line 75、无 cmake.configure 调用），而失败栈正是 CCI 配方（含 exports_sources CMakeLists.txt 的 cmake 封装），其 CMakeToolchain 默认映射 HarmonyOS，系统 cmake 4.4.3 无该平台模块；与 ayatana-ido 第十四轮"任一 CCI 节点源码构建必挂"同机制 | 删边路线延续到第二节点（与上轮换版本无关，是新证据驱动的新目标）：删除 requires("heatshrink/0.4.1")，图中仅剩 boost/zlib 两个仓库独有 conan 节点；conandata 新增 heatshrink_source（URL/sha256 一字不差复用本仓 archives/h/heatshrink/0.4.1 条目官方 GitHub 源），source() 解到 heatshrink-src，build() 以 conf 编译器（R33，不用环境 CC/AR）跑上游自带 Makefile `all`（零 cmake），产物装入私有前缀并手写 heatshrink-config（含 version 文件，声明 0.4.1）提供 heatshrink::dynamic/static，generate() 的 heatshrink_DIR 改指该前缀；package() 把档案与头文件装入本包，package_info 新增 heatshrink_dynamic/static 组件（cmake 目标名保持 heatshrink::dynamic/static），binarize 改 requires 内嵌组件；补丁 0001 映射行不变（目标名恰好一致）；8 上游用例 + test_package 2 检查全量 |
| 12 | 真机 `conan create` 在上游 8/8 通过后死于 `package_info(): The direct dependency 'boost' is not used` | 上游 convert 库以 PRIVATE 链接 Boost::boost（convert.cpp 含 boost/beast base64 头），但 package_info 的 convert 组件 requires 只写了 binarize+core，直连依赖 boost 无任何组件消费，Conan 组件校验直接报错 | convert 组件 requires 追加 `boost::boost`（boost/1.90.0.4 暴露的正是 Boost::boost 组件，与 zlib::zlib 同法；binarize 保持 core+heatshrink_dynamic+zlib::zlib 不变）；上游 CMake 与测试逻辑零改动 |
| 13 | test_package convert_contract 编译死于 convert/export.h file not found（上游 8/8 已过，package_info boost 修复已生效，失败前移到 test_package build） | 上游公头用引号兄弟包含（convert.hpp->convert/export.h、binarize.hpp->binarize/export.h+core/core.hpp）；安装布局为 include/LibBGCode/<comp>/ 下，INSTALL_INTERFACE 只给 -I include，quoted 形式既不命中头文件相对目录也不命中 -I include，需 -I include/LibBGCode 才可解；属上游安装接口原生形态，非本配方安装漏文件（package 已装 3 hpp + 3 export.h + 4 heatshrink） | 纯配方修复：core/binarize/convert 三组件 includedirs 均设为 [include, include/LibBGCode]（<LibBGCode/...> 走前者，quoted 兄弟包含走后者）；不改上游头文件与补丁 |
| 14 | 真机 test_package 2/2 失败：convert_contract 三 CHECK 全 FAIL（ascii_to_binary 起），core_contract append_gcode FAIL 而 initialize 通过；同期上游 8/8 全过 | 两个自建契约误用了上游 API（源码级确认）：① convert::from_ascii_to_binary 在无 "; generated by PrusaSlicer" producer 行时直接返回 InvalidAsciiGCodeFile（convert.cpp producer_found 门），自建样本仅 "; sample comment" 故首步即失败；② Binarizer 默认 m_enabled=false，initialize() 未使能时是空操作（不捕获 FILE* 即返回 Success），随后 append_gcode() 在空文件句柄上返回 WriteError（binarize.cpp），自建 core 测试未调用 set_enabled(true)；且使能后 initialize() 还要求 printer/print/slicer 三类元数据非空（Missing*），自建 core 测试未预置 | 只改 test_package（配方/补丁不动）：convert_contract 改用最小 PrusaSlicer 格式样本（producer 头 + printer/print/slicer 各至少一条，与 mini_cube_a.gcode 同构）并采用上游同款压缩组合（slicer Deflate + gcode Heatshrink_12_4 + MeatPackComments）以覆盖 vendored 边；core_contract 在 initialize 前 set_enabled(true) 并预置三类元数据各一条；双文件各加 DIAG 行打印 translate_result 以便下轮日志定位；CHECK 数保持 5/6 不变 |

## 源码修改

- patches/0001-conan-deps-target-mapping.patch：3 处 CMake 目标名映射（binarize 库 + 2 个测试 CMakeLists；convert 沿用上游 Boost::boost 无需映射），无平台宏，无测试逻辑修改。

## 依赖版本

- boost/1.90.0.4（仓库内 b2 全量头文件配方、零 tool_requires；原生导出 Boost::boost 且含 nowide 头文件）
- zlib/1.3.1.1（静态；与上游 1.3.1 同 tarball 的 -fPIC 重建，仓库独有版本，自动走 ohpcd，无 cmake tool 边）
- heatshrink v0.4.1 随配方 vendor（上游 Makefile 直编，静态双档案随本包发布；内嵌组件重导出 heatshrink::dynamic/static）
- catch2 v3.8.1 随配方 vendor（conandata catch2_source 官方 GitHub 源；build() 内以同一 conan_toolchain.cmake + 系统 cmake 构建安装到私有前缀，不进交付包）

## 验证结果

待 HMBS 真机预检回填（conan create 日志中的 ctest 输出与两行 JSON 标记）。

## 注意事项

- 本配方为纯库（package_type=library，bin/ 无产物），按 R38 不需要软件级 commands.json。
- 上游测试会向 tests/data（源码树内）写入转换产物（mini_cube_b.gcode 等），与上游 CI 行为一致；conan source 目录可写。
- 版本号沿用任务指定的 git 快照格式（jxrlib 同类先例：1.2-git20170615.f752187）。
