# c-json 1.0.0 适配笔记

## 任务与上游
- 任务号: #6692（activity: 开源鸿蒙PC专项积分赛；claimer: wanderlust_0823；changeType: feat）
- 分支: feat/c-json-1.0.0（worktree ~/qzy/c-json）
- 上游仓库: https://github.com/c-util/c-json
- 上游版本: v1.0.0（唯一稳定 tag）
- 源 URL: https://github.com/c-util/c-json/archive/refs/tags/v1.0.0.tar.gz
- SHA256: 746371b9a752d4ecb8eef9e6022438cb772c88c4b636ff041b1eac3a02e311e2
- 语言: C（100%；任务平台声明 cpp，c↔cpp 兼容族，lang-preflight 通过）
- 构建系统: meson（>= 0.60）
- 依赖: c-stdaux（无版本约束，实际 1.6.0 满足）+ c-utf8（头文件库）

## 适配方式（1 个可移植性补丁，无平台宏）
1. **pc shim**（generate()，非补丁）：上游以 dependency('libcstdaux-1'/'libcutf8-1')
   消费依赖，conan 依赖名不同 → 手写两个同名 shim。注意 c-json 读连字符变量
   `version-scripts`（同族其他库是下划线 `version_scripts`），shim 两个拼写都提供。
2. **补丁 0001-flush-memstream-before-close.patch**（可移植性，无平台宏）：
   - 根因：OHOS libc 的 `open_memstream` 有缺陷——`fclose()` 返回 EBADF(-9) 且
     **丢弃尚未冲刷的 stdio 缓冲**，导致 `read_string()`/`read_file()` 得到空串。
     实测证据：先 fflush 再 fclose 时缓冲内容正确落盘（n=6, s="hello!"）。
   - 修复：在 `c_fclose(stream)` 前补 `fflush(stream);`，共 2 处
     （src/c-json-reader.c 的 read_string、src/json-validate.c 的 read_file）。
     fflush-then-close 在所有 POSIX 平台等价无害，可回馈上游。
   - 未修复时的表象：上游 test-basic 第 18 行断言失败（解码结果为空串）、
     test-reader 全部 317 个样例以"空输入"假通过。
3. **test-reader 超时**：脚本测试遍历 test/ 下 317 个 JSON 样例，本平台实测约 55s，
   超过 meson 默认 30s → conanfile 的 meson test 加 `--timeout-multiplier=20`。

## W0/W0b
- ci/scripts/preflight_check.sh c-json/1.0.0：通过（无 conanfile 阶段无依赖可查）
- 依赖发布状态（2026-09-08 实测）：c-stdaux/1.6.0（PR !8549 open）与 c-utf8/1.1.0
  （本批次任务 #6168，配方就绪待提交）均未发布。本地以一次性验证包代跑
  （stdaux-local + 由 #6168 已验证配方创建的 c-utf8 包，仅存于任务 CONAN_HOME）。
- lang-preflight：通过（task=cpp, detected=c）

## 上游测试（R51 四数口径）
- 上游静态声明总数: 2（src/meson.build 无条件 test() 注册：test-basic、test-reader）
- 实际执行: 2；通过: 2；失败: 0；跳过: 0（补丁后）
- 静态断言数: 69（test-basic.c 69 处 assert(；test-reader 为数据驱动脚本，
  317 个样例无 assert(）
- 执行证据:
  - 探索构建（meson + c-stdaux/c-utf8 子项目）：~/tmp/uc2/c-json/meson-test.log
    （补丁前 test-basic SIGABRT + test-reader 1 个样例失败；补丁后全过）
  - conan create 内嵌（build() 的 meson test）：~/tmp/uc2/c-json/conan-create.log

## 消费者测试（test_package，1 项）
- test.c 真实调用 c_json_reader_new/begin_read/read_string/read_number/end_read/free：
  断言转义解码（\n）、数字词法边界（-3.14）与错误传播（C_JSON_E_INVALID_TYPE）；
  ctest 1/1 通过。

## W3 本地验证
- conan create（ohos-aarch64 profile）：rc=0，日志 ~/tmp/uc2/c-json/conan-create.log
- R36/finish：待 c-stdaux 与 c-utf8 官方发布后执行（PF4 依赖闸 + R36 均以此为准）

## 路径 B 结论
- 走路径 B：适配中发现可跨仓库复用的平台级知识——OHOS libc open_memstream 的 fclose 丢弃未冲刷缓冲并返回 EBADF（静默数据损坏，四象限行为探针实证），最小修复为 close 前补 fflush（本 PR 补丁 0001/0002，2/2 测试全过验证）。
- 交付物：knowledge/drafts/E999-draft-C1N1.kv/.md（真实解析器 18 键校验通过；draft-review 判 create，最高分近邻 E302 相似度 0.13，人工核对为测试基建探测/禁用场景，与本条目库 API 场景互为边界）；知识库扩展 Issue 2873 与本 PR 双向关联。

## 已知限制
- 无。上游测试套件的测试数据（test/*.json）随源码分发，无外部资源依赖。
