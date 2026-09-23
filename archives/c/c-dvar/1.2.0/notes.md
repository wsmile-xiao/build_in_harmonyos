# c-dvar 1.2.0 适配笔记

## 任务与上游
- 任务号: #6158（activity: 开源鸿蒙PC专项积分赛；claimer: wanderlust_0823；changeType: feat）
- 分支: feat/c-dvar-1.2.0（worktree ~/qzy/c-dvar）
- 上游仓库: https://github.com/c-util/c-dvar
- 上游版本: v1.2.0（tag tarball）
- 源 URL: https://github.com/c-util/c-dvar/archive/refs/tags/v1.2.0.tar.gz
- SHA256: e4b0661e29611eccccbca122f91e9c0cb161e8c44382f80a77f1b95a0007c264
- 语言: C（100%；任务平台声明 cpp，c↔cpp 兼容族，lang-preflight 通过）
- 构建系统: meson（>= 0.60）
- 依赖: c-stdaux >= 1.5.0 + c-utf8 → requires c-stdaux/1.6.0 + c-utf8/1.1.0
- 可选依赖: libdbus-typenum（required: false，不提供；对应条件测试不启用）

## 适配方式（无补丁，无源码修改）
同族 shim 模式：上游 meson.build 以 dependency('libcstdaux-1'/'libcutf8-1') 消费依赖，
conan 依赖名与上游 pkg-config 名不同 → generate() 手写两个同名 shim（c-stdaux 侧
提供 cflags/version_scripts 变量；c-utf8 侧提供 Cflags + Libs -lcutf8-1）。
仓库先例：abiword-plugin-* 3.0.8 对 glib-2.0；同族 c-siphash/c-shquote/c-rbtree/
c-utf8 1.1.0 已验证同款。

## W0/W0b
- ci/scripts/preflight_check.sh c-dvar/1.2.0：通过（无 conanfile 阶段无依赖可查）
- 依赖发布状态（2026-09-08 实测）：c-stdaux/1.6.0（PR !8549 open）、c-utf8/1.1.0
  （任务 #6168，配方就绪）均未发布。本地以一次性验证包代跑（stdaux-local +
  由 #6168 已验证配方创建的 c-utf8 包，仅存于任务 CONAN_HOME）。
- lang-preflight：通过（task=cpp, detected=c）
- 上游无 meson.options：无配置选项

## 上游测试（R51 四数口径）
- 上游静态声明总数: 4（src/meson.build 无条件 test() 注册：API Symbol Visibility、
  Basic API Behavior、D-Bus String Restrictions、Type and Signature Parser）
  另有 1 项条件测试（Type and Data Verification with Enumerated Types）：需可选
  依赖 libdbus-typenum，上游 required:false 默认不注册，本包不启用，如实不计入
- 实际执行: 4；通过: 4；失败: 0；跳过: 0
- 静态断言数: 118（test-api.c 42 + test-basic.c 36 + test-string.c 18 +
  test-type.c 22；test-enumerated.c 5 不计）
- 执行证据:
  - 探索构建（meson + c-stdaux/c-utf8 子项目）：~/tmp/uc2/c-dvar/meson-test.log
    （c-dvar 4/4 OK；另 4 项 OK 为子项目自测，不计入本包）
  - conan create 内嵌（build() 的 meson test）：~/tmp/uc2/c-dvar/conan-create.log

## 消费者测试（test_package，1 项）
- test.c 真实调用 c_dvar_type_new_from_signature/c_dvar_type_compare_string/
  c_dvar_new/c_dvar_begin_write/c_dvar_write/c_dvar_end_write/c_dvar_begin_read/
  c_dvar_read/c_dvar_end_read：对 (su) 变体做写读往返断言，大小端各一轮；
  ctest 1/1 通过。

## W3 本地验证
- conan create（ohos-aarch64 profile）：rc=0，日志 ~/tmp/uc2/c-dvar/conan-create.log
- R36/finish：待 c-stdaux 与 c-utf8 官方发布后执行（PF4 依赖闸 + R36 均以此为准）

## 已知限制
- 无。默认测试套件无外部资源依赖，全部执行。
