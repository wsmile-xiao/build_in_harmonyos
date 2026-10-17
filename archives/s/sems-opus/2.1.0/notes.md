# sems-opus 2.1.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 2.1.0 已全量迁移 CMake）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15（OHOS SDK 26.0.0.18, aarch64-linux-ohos）
- 状态: published

## 编译步骤

1. W0 依赖检查：opus/1.5.2 ✅、libevent/2.1.12 ✅ 均已在 ohpcd 制品仓发布（conan download 实测）
2. 上游 tarball 含 CodeQL 残留自引用软链 `_codeql_detected_source_root -> .`（符号链接循环），
   解压复制时 shutil.copytree 崩溃——剔除该软链后作为源码输入
3. conan create（裁剪策略：EXCLUDE_APP_MODULES 全排除 app 层，仅构建
   sems_core/sems_sip 静态库 + sems_opus 插件；SEMS_USE_ILBC/MONITORING/PYTHON=OFF）
4. test_package 消费者测试：dlopen 加载 opus.so + 校验 amci_exports 导出契约
   （模块名 / payload / codec 条目）+ 真实执行 init/encode/decode

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 tarball 符号链接循环 | CodeQL 分析残留 `_codeql_detected_source_root -> .` | 剔除软链后打包 |
| 2 | opus/opus.h not found | 上游 core/plug-in/opus/CMakeLists.txt 缺 include_directories(${OPUS_INCLUDE_DIR})（gsm 模块有、opus 模块漏了） | patches/0001 注入 conan 依赖 include 路径 |
| 3 | FindOpus/FindLibevent2 不识别 conan 路径 | 上游 Find 模块用变量探测，不感知 CMakeDeps | conanfile generate() 注入 OPUS_*/LIBEVENT2_* 变量 |
| 4 | pthread_cancel undeclared | 部分 libc（含 OHOS musl）未实现 pthread_cancel | patches/0002 改为 CMake 编译期能力探测（`check_symbol_exists(pthread_cancel)` → `HAVE_PTHREAD_CANCEL`）：有符号走原 pthread_cancel，无符号退化为 `on_stop()` 协作式停止且不置 stopped；补丁不含任何平台条件宏（R8），能力探测对所有 libc 通用 |
| 5 | dlopen 重定位 run_log_hooks 失败 | SEMS 插件由 -rdynamic 的宿主加载，插件引用宿主日志符号 | test_package 宿主内联提供 4 个符号（llvm-nm 实测：run_log_hooks/log_level/log_level2str/log_stderr）+ -rdynamic |
| 6 | 插件产物名非 sems_opus.so | 上游 OUTPUT_NAME=${sems_module_name}=opus 且无前缀 | package() 收集 opus.so |

## 上游测试用例申报表（R51 三步法 + rule4 真实执行）

- 上游测试清点：core/tests/ 共 **11** 个 suite 源文件（fct.h 框架），由 sems_tests.cpp 的
  FCTMF_SUITE_CALL() 注册，编译为单体可执行程序 sems_tests（ctest 注册 1 项，内部
  **204** 个断言级子测试）。各 suite 用例数（FCT_TEST_BGN 静态计数）：

  | suite | 用例数 | suite | 用例数 |
  |---|---|---|---|
  | test_rfc3261_musts | 88 | test_replaces | 5 |
  | test_rfc3261_parser | 25 | test_parser | 13 |
  | test_uriparser | 15 | test_auth | 11 |
  | test_amconfig | 14 | test_headers | 10 |
  | test_jsonarg | 13 | test_extensions | 8 |
  | test_sdp | 2 | **合计** | **204** |

  > 更正：此前 PR 正文与本笔记登记的「10 个测试源文件」漏计 test_extensions.cpp，实为 11 个；
  > 静态计数合计 204 与运行输出 204/204 完全一致。
- 真实执行：配方 cmake.build(target="sems_tests") 构建并随包分发（bin/sems_tests），
  test_package test() 第一步真实运行，实测 **`PASSED (204/204 tests in 0.014899s)`**、
  退出码 0、日志 626 行且零 FAIL；本机复核（`cd <pkg>/bin && env -u LD_LIBRARY_PATH ./sems_tests`）
  结果一致（同一二进制，11 suite 全 PASS、无 skipped / 无 excluded）
- 补全测试：上游无 opus 插件级测试 → 鸿蒙特有消费者测试（test_package/test.c，N=1 ≥1）：
  按 SEMS 插件加载模型 dlopen 插件，dlsym 取上游 `amci_exports` 导出结构（直接使用
  core/amci/amci.h 的真实 ABI），校验模块名、payload 条目（`codec_id == CODEC_OPUS`）
  与 codecs 表中的编解码器条目，再以消费者方式 `init()` 取句柄并**真实执行**一次
  `encode()`（PCM16→opus）与 `decode()`（opus→PCM16），断言句柄、编码字节数、
  解码字节数（须等于 20ms 帧长）与解码 PCM 能量（非静音）；共 12 项断言，
  任一步失败即非 0 退出，无“仅验符号存在即成功”的降级分支。ctest 用例
  `test_sems-opus` 由 configure 阶段注入的 `SEMS_OPUS_PLUGIN` 环境属性驱动，可直接运行。

## 源码修改

- core/plug-in/opus/CMakeLists.txt（patches/0001：补 include 目录）
- core/AmThread.cpp（patches/0002：pthread_cancel 编译期能力探测，无该符号的 libc 走 on_stop() 协作式停止）
---

**编译结束**: 2026-09-29 23:35
**最终状态**: built
