# frugally-deep 0.20.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only，INTERFACE 目标 fdeep）
- 编译日期: 2026-09-27
- 编译器: clang/clang++（/data/service/hnp/bin/clang++ 15.0.4，Target aarch64-linux-ohos）
- 状态: published

## 编译步骤

1. 下载官方 tag v0.20.0 tarball（github.com 被墙，经 ghfast.top / gh-proxy.com 双镜像下载，SHA-256 交叉一致）
2. `ohc-run.py init-build frugally-deep 0.20.0 --url=https://github.com/Dobiasd/frugally-deep`（.orig/.work 双轨解压 + .tarball-sha256）
3. 重写 conanfile.py 为 header-only CMake 配方（conan-init 生成的 autotools 模板与 header-only 库不匹配）
4. `ohc-run.py conan-verify frugally-deep 0.20.0` — G0-G4/L2/L4/L5 全部 PASS（含 conan create 干净构建 + test_package 消费者测试）
5. HarmonyOS 专项测试：`clang++ -std=c++17 ohos_special_test.cpp`（链接 eigen/fplus/nlohmann_json 头），运行 PASS
6. `ohc-run.py finish frugally-deep 0.20.0 published` — W3 用 JUNK_PR_DIFF=pr.diff 单包口径通过（full 模式误扫 main 上其他库历史 junk：cloog/.build-closed 等，非本库文件）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试数据无法生成（R01 阻塞） | 测试数据链依赖 TensorFlow/Keras 训练后端，OHOS aarch64 无 TF 轮子（默认源与社区源均 No matching distribution；keras numpy backend 又依赖 jax） | R02 恢复：社区源 jaxlib cp312-ohos_aarch64 轮子 + keras 3.14.1 jax backend + IntegerLookup/AdaptivePooling 兼容层（语义同 fdeep），7 个上游测试 7/7 全部实际运行通过 |
| 2 | conan-init 生成 autotools 配方 | 构建系统按 URL 误判 autotools；实际为 header-only CMake | 重写为 package_type=header-library，package() 拷贝 include 树 |
| 3 | 依赖版本不匹配 | 上游 pinned functionalplus/v0.2.24、nlohmann_json/3.11.3 未发布 | 用制品仓已发布 fplus/0.2.28（提供 FunctionalPlus 配置）、nlohmann_json/3.12.0、eigen/3.4.0 |
| 4 | 专项测试运行报 invalid node index | Dense 层 inbound_nodes 为空导致节点数为 0 | JSON 补节点连接 [{"args":[{"config":{"keras_history":["input_1",0,0]}}]}] |
| 5 | 专项测试报 Invalid position rank | tensor_pos 参数量与 1 维张量形状不符 | 用 tensor_pos(单参) 读取 |
| 6 | finish W3 junk_check 拦截 | full 模式扫到 main 上其他库历史 junk（cloog 0.21.1/.build-closed、.staging-verified 等） | JUNK_PR_DIFF=pr.diff 单包口径复跑 W3，仅本库文件 |

## 源码修改
无源码修改（header-only 库，不生成 .patch）

## 依赖版本
- eigen/3.4.0（已发布）
- fplus/0.2.28（= FunctionalPlus，已发布）
- nlohmann_json/3.12.0（已发布）

## 验证结果

```bash
# conan-verify（G2 conan create + test_package 消费者测试）
python3 scripts/ohc-run.py conan-verify frugally-deep 0.20.0    # G0-G4/L2/L4/L5 PASS

# HarmonyOS 专项测试（公开 API：read_model_from_string + predict）
/data/service/hnp/bin/clang++ -std=c++17 -O2 \
  -I<fdeep/include> -I<eigen3> -I<fplus/include> -I<nlohmann_json/include> \
  ohos_special_test.cpp -o ohos_special_test.bin -pthread
./ohos_special_test.bin
# Loading json ... done. Building model ... done.
# model name: sequential_1
# predict output: [[[[[[7.0000]]]]]]
# PASS: dense output 7.0000 == expected 7.0000
# predict_single_output: 7.0000
# OHOS_SPECIAL_TEST_RESULT: PASS (0 failures)

# 上游测试全量：7/7 全部实际运行通过（R02 恢复 jaxlib ohos_aarch64 轮子 + keras 3.14.1 + 兼容层，见 reports/test-report.md 台账）
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | header-only CMake 配方（requirements: eigen/fplus/nlohmann_json） |
| conandata.yml | 官方 URL + SHA-256 |
| ohos_special_test.cpp | HarmonyOS 专项测试（真实消费入口） |
| test_package/ | 消费者测试（read_model_from_string+predict 断言） |
| reports/test-report.md | 上游测试双口径台账 |

## 注意事项
- 上游测试数据生成依赖 Python 训练后端：R02 已用社区源 jaxlib cp312-ohos_aarch64 轮子 + keras 3.14.1 jax backend + IntegerLookup/AdaptivePooling 兼容层恢复，7/7 通过；若后续环境更换需重新核对社区源轮子可用性
- conan-verify 的 E017 镜像注入会在 conandata.yml 残留 ghfast-bak，提交前已确认清理、URL 为官方 HTTPS
- 本库为 header-only，无系统同名库冲突（G3 通过），无 CLI 产物（R38 不需 commands.json）---

**编译结束**: 2026-09-27 02:49
**最终状态**: published
---

**编译结束**: 2026-09-27 07:06
**最终状态**: published
