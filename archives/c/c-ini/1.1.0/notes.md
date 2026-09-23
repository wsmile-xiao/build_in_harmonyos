# c-ini 1.1.0 适配笔记

## 任务与上游
- 任务号: #6160（activity: 开源鸿蒙PC专项积分赛；claimer: wanderlust_0823；changeType: feat）
- 分支: feat/c-ini-1.1.0（worktree ~/qzy/c-ini）
- 上游仓库: https://github.com/c-util/c-ini
- 上游版本: v1.1.0（tag tarball）
- 源 URL: https://github.com/c-util/c-ini/archive/refs/tags/v1.1.0.tar.gz
- SHA256: df01f3e2bd20a3857d9b9d7e4d13c6bf6cda69580ca110e7e41f14ad5423c950
  （2026-09-08 重新下载比对一致，此前 STATE 中"URL/SHA 待定"已过时）
- 语言: C（100%；任务平台声明 cpp，c↔cpp 兼容族，lang-preflight 通过）
- 构建系统: meson（>= 0.60）
- 依赖: c-list/3.1.0（header-only）+ c-rbtree/3.2.0 + c-stdaux/1.6.0 + c-utf8/1.1.0
  （四依赖均为本批次任务；c-list 见 PR !8547，c-stdaux 见 PR !8549）

## 适配方式（无补丁，无源码修改）
同族 shim 模式的多依赖版：generate() 手写 4 个 shim pc——libcstdaux-1（cflags +
version_scripts 变量）、libclist-3（仅 Cflags，c-list 3.1.0 上游 header-only 无编译
产物）、libcrbtree-3 / libcutf8-1（Cflags + Libs 指向真实静态归档基名 crbtree-3 /
cutf8-1）。仓库先例：abiword-plugin-* 3.0.8 对 glib-2.0；同族 c-siphash/c-shquote/
c-rbtree/c-utf8 1.1.0 已验证同款。

## W0/W0b
- ci/scripts/preflight_check.sh c-ini/1.1.0：通过（无 conanfile 阶段无依赖可查）
- 依赖发布状态（2026-09-08 实测）：四依赖均未发布（!8549/!8547 open；c-rbtree #6163、
  c-utf8 #6168 为本批次任务，配方就绪待提交）。本地以一次性验证包代跑：
  stdaux-local + 由各任务已验证配方创建的 c-list/c-rbtree/c-utf8 包（仅存于任务
  CONAN_HOME，绝不提交/发布）。
- lang-preflight：通过（task=cpp, detected=c）
- 上游无 meson.options：无配置选项

## 上游测试（R51 四数口径）
- 上游静态声明总数: 3（src/meson.build 无条件 test() 注册：API Symbol Visibility、
  Basic API Behavior、Parser Capabilities）
- 实际执行: 3；通过: 3；失败: 0；跳过: 0
- 静态断言数: 68（test-api.c 14 + test-basic.c 32 + test-reader.c 22）
- 执行证据:
  - 探索构建（meson + c-stdaux 子项目）：~/tmp/uc2/c-ini/meson-test.log
    （c-ini 3/3 OK；子项目自测不计入本包）
  - conan create 内嵌（build() 的 meson test）：~/tmp/uc2/c-ini/conan-create.log

## 消费者测试（test_package，1 项）
- test.c 真实调用 c_ini_reader_new/feed/seal → c_ini_domain_find → c_ini_group_find
  → c_ini_entry_get_value 的流式解析链路，断言 "[group]\nkey=value\n" 解析结果；
  ctest 1/1 通过。（test_package 于 2026-09-06 由前一轮会话编写，本轮复核合格）

## W3 本地验证
- conan create（ohos-aarch64 profile）：rc=0，日志 ~/tmp/uc2/c-ini/conan-create.log
- R36/finish：待四依赖官方发布后执行（PF4 依赖闸 + R36 均以此为准）

## 已知限制
- 无。上游测试套件无外部资源依赖，全部默认执行。
