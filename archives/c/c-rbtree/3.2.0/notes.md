# c-rbtree 3.2.0 适配笔记

## 任务与上游
- 任务号: #6163（activity: 开源鸿蒙PC专项积分赛；claimer: wanderlust_0823；changeType: feat）
- 分支: feat/c-rbtree-3.2.0（worktree ~/qzy/c-rbtree，基于 upstream/main 720939d0a4 创建）
- 上游仓库: https://github.com/c-util/c-rbtree
- 上游版本: v3.2.0（tag tarball，2023-12-12）
- 源 URL: https://github.com/c-util/c-rbtree/archive/refs/tags/v3.2.0.tar.gz
- SHA256: 5440bdce011e37c63e5b8b56c1ecbefc26b08d3e83c9fa2cb94762e7a6fc8749
- 语言: C（100%；任务平台声明 cpp，c↔cpp 兼容族，lang-preflight 通过：detected=c, build_system=meson）
- 构建系统: meson（>= 0.60）
- 依赖: c-stdaux >= 1.5.0（头文件库）→ 本配方 requires c-stdaux/1.6.0

## 适配方式（无补丁，无源码修改）
上游 meson.build 以 `dependency('libcstdaux-1')` 消费 c-stdaux，并读取 pc 变量
`cflags` 与 `version_scripts`。conan 依赖名 `c-stdaux` 与上游 pkg-config 名
`libcstdaux-1` 不一致，PkgConfigDeps 生成的 c-stdaux.pc 无法命中，因此在配方
generate() 手写 libcstdaux-1.pc shim，Cflags 指向真实 c-stdaux 包 include 目录，
变量取值：
- cflags：c-stdaux 上游 get_supported_arguments 在本平台 clang 15 的实测生效集合
  （与 meson 子项目直接构建的 build.ninja 一致，见探索构建
  ~/builds/c-rbtree-3.2.0.work/build/build.ninja）
- version_scripts=yes（clang 15 支持 -Wl,--version-script，探索构建实测通过）

仓库先例：abiword-plugin-docbook/eml/openwriter 3.0.8 对 glib-2.0 的同名 shim 处理；
同族已验证配方 c-siphash/c-shquote 1.1.0 同款。

## W0/W0b
- ci/scripts/preflight_check.sh c-rbtree/3.2.0：通过（无 conanfile 阶段无依赖可查）
- 依赖发布状态（2026-09-08 实测，制品仓 v2/conans/search）：c-stdaux/1.6.0 未发布
  （任务 #6167 已提 PR !8549，open）。本地以一次性验证包（conanfile 位于
  ~/tmp/uc2/c-rbtree/stdaux-local/，仅存在于任务 CONAN_HOME，绝不提交/发布）
  代跑依赖，完成配方全链路验证。官方 c-stdaux/1.6.0 发布后重跑 conan-verify 与 finish/W3。
- lang-preflight：通过（task=cpp, detected=c, 源文件 8 个（c:7, python:1），主体占比 88%）
- 上游无 meson.options（用旧式 meson_options.txt）：唯一选项 ptrace 默认 false

## 上游测试（R51 四数口径）
- 上游静态声明总数: 4（src/meson.build 无条件 test() 注册：API Symbol Visibility、
  Basic API Behavior、Generic Map、Miscellaneous）
  另有 2 项条件测试（Lockless Parallel Readers、Posix tsearch(3p) Comparison）：
  由 meson_options.txt 选项 ptrace 控制，上游默认 value: false 不注册，需 ptrace()
  系统调用，本包与设备实测均不启用，如实不计入默认套件
- 实际执行: 4；通过: 4；失败: 0；跳过: 0
- 静态断言数: 130（test-api.c 34 处 assert( + test-basic.c 23 + test-map.c 63 +
  test-misc.c 10；未启用的 test-parallel.c 26 与 test-posix.c 10 不计）
- 执行证据:
  - 探索构建（meson + c-stdaux 子项目）：~/tmp/uc2/c-rbtree/meson-test.log
    （c-rbtree 4/4 OK；另 2 项 OK 为子项目 c-stdaux 自测，不计入本包）
  - conan create 内嵌（build() 的 meson test）：~/tmp/uc2/c-rbtree/conan-create.log

## 消费者测试（test_package，1 项）
- test.c 真实调用 c_rbtree_add()/c_rbnode_next()/c_rbnode_prev() 断言中序正反向
  严格有序，c_rbnode_next_postorder() 断言后序恰好覆盖全部结点，c_rbnode_unlink()
  移除重插后仍有序，c_rbtree_move() 搬移后内容一致；ctest 1/1 通过。

## W3 本地验证
- conan create（ohos-aarch64 profile）：rc=0，日志 ~/tmp/uc2/c-rbtree/conan-create.log
- R36/finish：待官方 c-stdaux/1.6.0 发布到制品仓后执行（PF4 依赖闸 + R36 均以此为准）

## 已知限制
- 无。默认测试套件无外部资源依赖，全部执行。
---

**编译结束**: 2026-09-09 00:20
**最终状态**: built
