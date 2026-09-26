# kann 0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile C 库，无 configure、无 make install）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（OHOS arm64, musl）
- 状态: built

## 编译步骤

1. 官方源码：https://github.com/attractivechaos/kann tag v0（commit 1f279b9d6684e320d7b85fe089f0c5d9de9bc43b），
   tarball sha256=e9a5fc2f7dd991eab9bb303bb4170cc25bb757ec82eb4ea85e0ef6e499cdf2c3
2. `make CC=clang kautodiff.o kann.o kann_extra/kann_data.o` 编译库对象
3. `llvm-ar rcs libkann.a kautodiff.o kann.o kann_extra/kann_data.o` 静态归档
4. 全部 7 个上游示例（mlp/mnist-cnn/inspect/textgen/rnn-bit/ae/vae）用 clang 编译通过
5. 上游 README rnn-bit 训练验证：3000 样本训练收敛（cost 0.57→0.08，class error 29%→1.4%），
   预测 400958+737471=1138429 正确
6. 鸿蒙专项测试 test/kann_ohos_test.c：8->32(ReLU)->8(CEM) MLP popcount 任务训练 20 epoch
   收敛，未见样本错误率 0.00% (0/500)，模型 save/load 往返一致，on_ohos=1 PASS
7. Conan 配方：conan create 通过（G2），产物 libkann.a + 头文件（kann.h/kautodiff.h/kann_extra/*.h）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Conan 2 报 Invalid package version '0' | Conan 2 要求版本号至少两段（0/1 单段均拒绝） | 归档目录与配方版本用 "0.0"，manifest 保留平台任务版本 "0"（asyncfuture 1.0 先例同构） |
| 2 | conan create 中 make 报 No rule to make target 'kautodiff.o' | basic_layout 下 build() 在 build-release 目录运行，Makefile 在源码目录 | make/ar 显式 cwd=self.source_folder 执行 |
| 3 | /tmp 只读 | OHOS /tmp 为 erofs 只读（E002） | 下载/构建改用 $HOME/tmp |

## 依赖版本

- 无 Conan 外部依赖（仅系统 libc/pthread/z/m，kann 为独立库）

## 验证结果

```bash
# 上游示例
./examples/rnn-bit -m2 -o add.kan -   # 训练收敛
echo '400958 737471' | ./examples/rnn-bit -Ai add.kan -  # 输出 1138429 = 两数之和
# 鸿蒙专项测试
./test/kann_ohos_test  # PASS: MLP converged on OHOS, error=0.00%, on_ohos=1
# conan 门禁
ohc-run.py conan-verify kann 0.0  # G0-G4 + L2/L4/L5 全 PASS
```

## 上游测试统计（双口径台账）

- 上游无 tests/ 目录、无测试框架（gtest/catch/CUNIT 均无）、无 ctest、无 `make check`/`make test` 目标。
- 源码中唯一 "check" 命中的 `kad_check_grad()` 是库公开的梯度检查 API，非测试用例。
- 独立上游测试用例数 = 0（source_declared_total=0，configured_executable_total=0）。
- 台账覆盖项：
  - 测试源：无 tests/ 目录，无独立测试用例
  - 框架头/源码：无
  - 样例（非独立用例，不计入）：examples/{mlp,mnist-cnn,inspect,textgen,rnn-bit,ae,vae}.c 7 个 C 样例，
    全部 clang 编译通过，rnn-bit 已实际运行验证收敛与预测
  - 基准：README 基准表（纯文档，无脚本）
  - fixture：无
  - 测试脚本：无
  - 构建目标：kautodiff.o/kann.o/kann_extra/kann_data.o（库目标）+ 7 个样例可执行
- 通过率口径：0/0（全量发现数=0，无独立用例；样例运行通过作为适配验证证据单独记录）
- 鸿蒙专项测试（新增）：test/kann_ohos_test.c，真实 MLP 训练/预测/持久化，on_ohos=1，PASS
- test_package 消费者测试（新增）：test.c 调用公开 API 训练预测 popcount，conan create 内实际运行，PASS

## 注意事项

- kann 为纯 Makefile 库：示例程序是演示用途（依赖外部 MNIST 数据），不作为 CLI 交付，
  配方只打包 libkann.a + 头文件（R38：库类型无需 commands.json）
- GitHub 直连不可达，下载经 api.github.com tarball 与 gh-proxy 镜像完成，内容逐文件一致
- 平台任务版本 "0" ↔ Conan 版本 "0.0"（见问题 #1）

## 知识候选台账与路径决定（摘要，完整见 reports/knowledge-candidate-ledger.md）

- 候选 C1（Conan 2.29.1 拒绝单字符版本号 "0"）与 C2（纯 Makefile 库配方：
  basic_layout 下 make/ar 需 cwd=self.source_folder、L0d test() 需 self.run）经
  四范围查重（index.tsv/doc/graph kv/drafts）均为既有草稿 causal_duplicate：
  DRAFT-btyacc-3.0-conan-single-char-version、DRAFT-commander-1.4.0-makefile-recipe-build-package-traps、
  DRAFT-cd-hit-4.8.1-make-conan-recipe。
- 七轴结论：C1/C2 均 exact_duplicate=false、causal_duplicate=true、trigger_overlap=true、
  solution_overlap=true、combination_novelty=false、boundary_novelty=false、
  test_migration_novelty=false；无新增可跨库复用差异。
- 路径决定：**reuse_existing（Path A 常规适配）**，不建新 .md/.kv 草稿；
  knowledge_candidate_ledger 见 reports/knowledge-candidate-ledger.md（本地保留）。
---

**编译结束**: 2026-09-21 16:00
**最终状态**: built
