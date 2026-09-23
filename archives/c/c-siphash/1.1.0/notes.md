# c-siphash 1.1.0 适配笔记

## 任务与上游
- 任务号: #6166（activity: 开源鸿蒙PC专项积分赛；claimer: wanderlust_0823；changeType: feat）
- 分支: feat/c-siphash-1.1.0
- 上游仓库: https://github.com/c-util/c-siphash
- 上游版本: v1.1.0（tag tarball）
- 源 URL: https://github.com/c-util/c-siphash/archive/refs/tags/v1.1.0.tar.gz
- SHA256: a70c71effbcd553858250d109dd39599b9e3d5a91d46f0beb731bf6799893e63
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
  ~/builds/c-siphash-1.1.0.work/build/build.ninja）
- version_scripts=yes（clang 15 支持 -Wl,--version-script，探索构建实测通过）

仓库先例：abiword-plugin-docbook/eml/openwriter 3.0.8 对 glib-2.0 的同名 shim 处理。

## W0/W0b
- ci/scripts/preflight_check.sh c-siphash/1.1.0：通过（无 conanfile 阶段无依赖可查）
- 依赖发布状态（2026-09-06 实测，制品仓 v2/conans/search）：c-stdaux 未发布
  （由其他 agent 适配中）。本地以一次性验证包（conanfile 位于
  ~/tmp/uc2/c-siphash/stdaux-local/，仅存在于任务 CONAN_HOME，绝不提交/发布）
  代跑依赖，完成配方全链路验证。官方 c-stdaux/1.6.0 发布后重跑 conan-verify 与 finish/W3。
- lang-preflight：通过（task=cpp, detected=c, 源文件 c:3 占比 100%）

## 上游测试（R51 四数口径）
- 上游静态声明总数: 2（src/meson.build 的 test() 注册：API Symbol Visibility、
  Basic API Behavior；无 meson.options，无条件测试）
- 实际执行: 2；通过: 2；失败: 0；跳过: 0
- 静态断言数: 19（test-api.c 2 处 assert( + test-basic.c 17 处 assert(）
- 执行证据:
  - 探索构建（meson + c-stdaux 子项目）：~/tmp/uc2/c-siphash/meson-test.log
    （c-siphash 2/2 OK；另 2 项 OK 为子项目 c-stdaux 自测，不计入本包）
  - conan create 内嵌（build() 的 meson test）：~/tmp/uc2/c-siphash/conan-create-2.log
    （Ok: 2 Fail: 0）

## 消费者测试（test_package，1 项）
- test.c 真实调用 c_siphash_hash()（one-shot）与 c_siphash_init/append/finalize()
  （流式三块分片），均断言 SipHash 论文 Appendix A 参考向量 0xa129ca6149be45e5
  （与上游 test-basic.c 同源）；ctest 1/1 通过。

## W3 本地验证
- conan create（ohos-aarch64 profile）：rc=0，日志 ~/tmp/uc2/c-siphash/conan-create-2.log
- R36/finish：待官方 c-stdaux/1.6.0 发布到制品仓后执行（PF4 依赖闸 + R36 均以此为准）

## 已知限制
- 无。上游测试套件无外部资源依赖，全部默认执行。
---

**编译结束**: 2026-09-09 00:27
**最终状态**: built
