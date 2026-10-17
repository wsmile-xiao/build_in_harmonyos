# string-view-lite 1.8.1 适配笔记

## 编译环境
- 构建系统: cmake（CMake INTERFACE header-only 库）
- 编译日期: 2026-09-05
- 编译器: clang 15（OHOS aarch64 工具链，profile ohos-aarch64）
- Conan: 2.29.1（os=OHOS 适配版），CONAN_HOME=~/tmp/ch/home-svl
- 状态: built（conan-verify 通过，未 upload；published 需合并后 release 流水线上传）
- 任务号: #5901（开源鸿蒙PC专项积分赛-依赖，类型 feat）

## 前置核验（W0/W0b）

- W0 依赖预检：`ci/scripts/preflight_check.sh string-view-lite/1.8.1` 通过——header-only，无任何依赖。
- W0b 历史经验：读取本仓已合入的 `archives/s/string-view-lite/1.8.0/`（junshi_liu，MR !7517，含 1.7.0）notes 与配方；历史成功环境为同 profile 的 CI/本地 conan create，语义可直接迁移；历史踩坑记录为模板占位（未填实），无需要逐项比对的绕坑结论。
- 语言预检（R47）：`ohc-run.py lang-preflight string-view-lite 1.8.1` 通过——task=cpp，detected=cpp，构建系统 cmake。
- recipe-search：命中 `string-view-lite/1.8.0`（score 0.5，同构 cmake 骨架）。
- 知识图谱：命中 **E321**（martinmoene lite 系 header-only 库 Conan 2.x 配方迁移与 INTERFACE 消费，来源 PR !7220），配方按其方案逐项落实（package_type=header-library、cmake_layout、CMakeToolchain OHOS 映射、cpp_info.set_property cmake_file_name/cmake_target_name、{NAME}_OPT_BUILD_TESTS=ON 保持上游测试入口、test_package 实调 API）。

## 源码与配方

- 官方源码：https://github.com/martinmoene/string-view-lite/archive/refs/tags/v1.8.1.tar.gz
- SHA256：`97b812275f07d02592efb092bd70366d310b2294f677644ea07828e6138b091d`（本地 curl 下载实测，与 conandata.yml 一致）
- 无补丁（patches: {}，`apply_conandata_patches` 显式调用保留）
- 配方以 1.8.0 已验证配方为基，仅版本号、conandata 与描述更新；单头文件 `include/nonstd/string_view.hpp`

## 编译步骤

1. `conan-verify`（8 道门禁）：G1/G0/G2/G3/G4/L2/L4/L5 全部 PASS，报告见 `reports/conan-verify-report.md`。
2. G2 = `conan create ... -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing --user=ohpcd --channel=stable`，一次通过，无任何源码修改。

## 上游测试（R51 三步法，四类数字分列）

1. **上游源码静态声明总数**：`test/string-view.t.cpp` 逐处统计 lest `CASE(`/`CASE (` 注册入口 **89 处**（84 处无空格 + 5 处带空格，与 lest 实际注册一致）；CMake `add_test` 注册 4 项（test-cpp98/cpp11/cpp14/cpp17）。
2. **官方套件实际执行数**：ctest 4/4 项全部执行（clang 15 下 cpp98/11/14/17 全支持），运行时 lest 注册用例 350 个（cpp98=89, cpp11=89, cpp14=83, cpp17=89，cpp14 少 6 项为编译器条件编译差异，非跳过），每项 lest 直接运行（`-l` 实测注册数）。
3. **未执行/跳过数**：0。
4. **新增消费者测试数**：`test_package/test_string_view_lite.cpp` 1 个（7 项断言：构造/访问/substr/compare/find/empty）+ 鸿蒙专项 `test/ohos_string_view_test.cpp` 1 个（12 项 CHECK，aarch64 本机实跑）。

## 验证结果

```text
ctest --output-on-failure（G2 conan create 内，见 reports/conan-create.log:149-158）
1/4 Test #1: test-cpp98 .......................   Passed    0.04 sec
2/4 Test #2: test-cpp11 .......................   Passed    0.03 sec
3/4 Test #3: test-cpp14 .......................   Passed    0.04 sec
4/4 Test #4: test-cpp17 .......................   Passed    0.03 sec
100% tests passed, 0 tests failed out of 4

lest 用例注册实测（可执行文件 -l）：
cpp98=89, cpp11=89, cpp14=83, cpp17=89（合计 350，全部随 ctest 通过）

消费者 test_package（conan create 自动执行）：
PASS: string-view-lite header-only 库链接和核心 API 验证通过 (exit 0)

鸿蒙专项测试（clang++ -std=c++17 -O2 -I<src>/include，aarch64 本机运行）：
OHOS 专项测试打印: [HarmonyOS] size=31
PASS: string-view-lite 1.8.1 HarmonyOS 专项测试全部通过 (exit 0)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 0 | 无 | — | 配方复用 E321 + 1.8.0 已验证模式，一次构建通过，无新问题 |
| 1 | conan-verify E017 镜像注入恢复失败污染活文件 conandata.yml（url 标量→gh-proxy.com 镜像列表），并被 submit 自动 git add 提交推送（ed1b4714e9） | 恢复守卫仅匹配 ghfast.top，注入域名为 gh-proxy.com 不命中；"已恢复原始 conandata.yml"日志为假象 | 用正确基线 run_preflight(upstream/main, HEAD) 捕获 PF7 唯一违规；git show b942b9fba5 恢复官方形态，新提交 5cb4d39586 修复推送，正确基线 preflight 转 PASS；详见知识草稿 DRAFT-string-view-lite-1.8.1-e017-ghproxy-livefile-mutation-commit-escape |

## 依赖版本

无依赖（header-only，W0 预检通过）。

## 注意事项

- lest 默认静默通过（无失败不输出），用例数需 `-l` 或静态统计获取，不能拿空输出当通过证据。
- lest 用例行名含转义引号与 `CASE (`（带空格）两种写法，静态统计需同时覆盖，否则 84≠89 会对不上账。
- cpp14 变体注册 83 项（少 6 项）是上游源码条件编译所致，属上游行为，不是适配跳过。
- 设备 `/tmp` 只读（E002），临时文件一律放 `~/tmp/`。
---

**编译结束**: 2026-09-05 00:55
**最终状态**: built
