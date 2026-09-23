# nativefiledialog-extended 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake（≥3.10）
- 编译日期: 2026-09-08
- 编译器: clang 15（aarch64-unknown-linux-ohos）
- 后端: GTK3（NFD_PORTAL=OFF，上游默认）
- 状态: built（conan create ohos-aarch64 exit=0，test_package OK 2 checks）

## 依赖
- gtk/3.24.38（制品仓配方名无加号；archives 目录名 gtk+ 带 +；配方声明 pkg_config_name=gtk+-3.0，PkgConfigDeps 生成 gtk+-3.0.pc 满足上游 pkg_check_modules 探测）

## 配方要点（复刻 agg 手法）
- 无 conandata.yml：源码 url/sha256 硬编码进 source()（规避 CI Pre-download BUILD_DIR 崩溃）
  - url: https://github.com/btzy/nativefiledialog-extended/archive/refs/tags/v1.3.0.tar.gz
  - sha256: 2fea19102cf4d5283a80fb87a784792166988e85bb92baa962d34f72b22dcc1a
- CMAKE_SYSTEM_NAME=Linux 映射（nanoflann E092 手法）；CMAKE_CXX_STANDARD=17 显式钉住
- NFD_BUILD_TESTS（21 个对话框交互测试）与 NFD_BUILD_SDL2_TESTS（1 个 SDL2 窗口测试）显式置 OFF（根项目构建时默认 ON，无头 CI 不可执行）
- generate()：PkgConfigDeps + PKG_CONFIG_PATH=generators_folder 注入（R49 build-folder 私有）
- package_info()：cpp_info.requires=["gtk"]（静态 libnfd.a 拖 GTK 符号）
- 无补丁：上游 `-nostdlib -fno-exceptions -fno-rtti`（COMPILER_GNU 分支，Clang 命中）为编译选项，nfd_gtk.cpp 无 STL/异常/RTTI，OHOS clang 15 直接编译通过

## 上游测试未移植归因（rule4，详见 test_package/MANIFEST.yml upstream_test_evidence）
- 上游 test/ 共 22 个测试程序（与审核方实测 N=22 一致）：21 个 NFD_BUILD_TESTS 对话框交互测试 + 1 个 NFD_BUILD_SDL2_TESTS SDL2 窗口测试
- 21 个对话框测试各自 main 调用 NFD_OpenDialog/SaveDialog/PickFolder 并阻塞等待用户交互；1 个 SDL2 窗口测试需窗口循环
- 当前无头 CI 环境无 display/broadwayd/交互会话；实测 NFD_Init→gtk_init_check 在无显示环境阻塞（GDK_BACKEND=broadway 亦然）——属 GUI 运行环境限制，不是可通过安装依赖解决的缺依赖问题
- 替代验证：test_package 无头 API 冒烟 2 断言（NFD_GetError 初始 NULL、NFD_ClearError 幂等）+ 静态 nfd 对 GTK3 全链链接/加载，CI #42559/#42882 全绿

## 验证结果
- conan create（ohos-aarch64）: exit=0
- test_package: "nativefiledialog-extended test_package: OK (2 checks)"
- AI 代码审查：未发现问题（2026-09-09 两轮）
- CI：#42559（L0/L1 通过）、#42882（L0/L1 通过）

## 踩坑记录
1. W0 依赖检查：conan list "gtk+/3.24.38" Recipe not found + download 报 "system acceleration policy not enabled"（cnb.cool 对不存在 recipe 的响应形态）；用 conan list "*gtk*" 通配查出真实配方名 gtk
2. test_package 首跑挂起：NFD_Init→gtk_init_check 无 display 阻塞（进程 S 态）；二分诊断（不调 Init 的最小版正常 exit=0）锁定根因，非签名/动态库问题
3. 表格分隔行、复选框加粗、上游 N 如实上报（22 个测试逐条列明）等 PR 模板细节照 nanoflann 通过版执行