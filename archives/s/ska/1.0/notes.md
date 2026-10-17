# ska 1.0 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（target aarch64-unknown-linux-ohos）
- 状态: published

## 编译步骤

1. W0 依赖检查：`conan download zlib/1.3.1 -r=ohpcd --only-recipe` 与
   `conan download gtest/1.17.0 -r=ohpcd --only-recipe` 均 exit 0（可消费）。
2. 上游源码：https://github.com/simonrharris/SKA/archive/refs/tags/v1.0.tar.gz（tag v1.0, First Release）
   sha256 = fc6110c22c756158b190f50dc11d596265f9b0d09c28725b2b23ed22e2e4fbff
3. 探索性编译（OHOS 实机）：
   ```bash
   make -j2 CXX=clang++ \
     CXXFLAGS="-O2 -std=c++0x -I<conan zlib include>" \
     LDFLAGS="-L<conan zlib lib> -lz"
   ```
   一次通过，产物 bin/ska。zlib 使用制品仓静态包 libz.a（R26：系统同名库禁动态）。
4. 冒烟验证：`ska version`（Version: 1.0）；`ska fasta g1.fa g2.fa` → 940 kmers
   added / 520 unique；`ska info`、`ska distance` 均正常产出。
5. 固化 Conan 配方：conanfile.py（make 驱动，编译器与 zlib 路径全部来自
   Conan conf/依赖图，R33）+ conandata.yml + test_package（R34 真实消费）。
6. conan create + conan-verify 全绿后 finish（W2/W3 嵌入式门禁）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py 内置 urllib 下载 GitHub tarball 超时（Errno 110） | Python urllib 网络栈在该网络环境下到 codeload.github.com 超时（curl 同 URL 正常） | curl 预下载到 `$TMPDIR/builds/ska-1.0.tar.gz`，init-build 检测到 tarball 已存在自动跳过下载 |
| 2 | init-build 将归档骨架生成到主仓 archives/ 而非 worktree | find_project_dir() 定位到了主仓路径 | 将未跟踪的 archives/s/ska/ 整体移动到 wt-ska-1.0 worktree，主仓恢复干净 |
| 3 | `ska fasta` 首次运行报 Failed to open .skf | 误把 .skf 当作输入参数（实际用法 `ska fasta <fasta files>`，输出默认 fasta.skf） | 按 `--help` 用法重试，非平台问题 |

## 源码修改

无补丁（patches/ 为空）。上游源码零修改即可在 OHOS 编译通过；
平台差异仅通过配方层（编译器/zlib 路径注入）解决。

## 上游测试（R51 三步法）

1. 清点：tests/ 下 3 个 googletest 套件（general 6 + kmers 6 + DNA 15 = 27 个
   活跃用例；FactorialTest/IsPrimeTest 各 3 个被上游注释禁用，不计入）。
2. 实际运行（OHOS 实机 aarch64，gtest/1.17.0 制品包链接）：
   - general_unittest: 6/6 PASSED
   - DNA_unittest: 15/15 PASSED
   - kmers_unittest: 6/6 PASSED
   - 合计 27 通过 / 0 失败 / 0 跳过
   - 日志: `$TMPDIR/ska-test-run.log`、用例清单 `$TMPDIR/ska-test-cases.log`
3. 新增鸿蒙消费者用例：test_package/test.sh（端到端：version → fasta 建库 →
   info 回读 → gzip 压缩输入（zlib 链接可行性）→ distance 距离矩阵）。

## 依赖版本

- zlib/1.3.1（制品仓 ohpcd，静态 libz.a）
- gtest/1.17.0（仅测试期使用，制品仓 ohpcd）

## 验证结果

```bash
$ ska version
SKA: Split Kmer Analysis
Version: 1.0
Citation: TBA

$ 上游 gtest 套件（OHOS 实机）
[  PASSED  ] 6 tests.   (general_unittest_ohos)
[  PASSED  ] 15 tests.  (DNA_unittest_ohos)
[  PASSED  ] 6 tests.   (kmers_unittest_ohos)
```

## 注意事项

- 上游 Makefile 硬编码 `CXX = g++` 且 `LDFLAGS = -lz`，配方通过 make 变量
  覆盖（CXX/CXXFLAGS/LDFLAGS），不改上游文件。
- 上游 tests/Makefile 期望 tests/googletest/ 内嵌 gtest 源码；本适配改为链接
  制品仓 gtest/1.17.0 预编译包，不向仓库混入依赖库源码。
- gtest 1.17 需 C++14+，测试编译使用 -std=c++17（被测库本身保持 C++11）。
- CI 仅消费 conanfile.py/conandata.yml/test_package/patches 四类输入；
  test_package/test.sh 即鸿蒙消费者可行性用例。

### 对话 #1: init-build
`ohc-run.py init-build ska 1.0 --url=...` 首次因 urllib 超时失败；curl 预下载
tarball 后重跑成功。归档骨架误生成到主仓，整体移动到 wt-ska-1.0 worktree。

### 对话 #2: AI 编译
1. W0 依赖检查（conan download zlib/1.3.1、gtest/1.17.0）— 通过
2. 探索性编译 `make -j2 CXX=clang++ CXXFLAGS=... LDFLAGS=...` — 一次通过
3. 冒烟验证 ska version / fasta / info / distance — 通过
4. 上游测试编译链接（gtest/1.17.0 制品包，-std=c++17）— 通过

### 对话 #3: 上游测试与配方固化
1. 上游 3 个 gtest 套件 OHOS 实机运行 27/27 PASSED（0 失败 0 跳过）
2. conanfile.py + conandata.yml + test_package（含鸿蒙消费者用例 5 项）
3. conan create 全绿；conan-verify G1–G4 + L2/L4/L5 全 PASS

### 对话 #4: finish 收尾
`ohc-run.py finish ska 1.0 published` — W3 本地 CI 模拟通过、W2 PR 原子性
通过、submit 就绪预检通过（test-report.md / packaging/ / .staging-verified 齐备）。

G0 clean-build 验证说明：上游为纯 Makefile 项目（无 configure 脚本），
clean_verify 的 configure 步骤结构性不适用（bash ./configure → exit 127，
特征签名同知识库 E168：无 configure 项目 G0 configure 失败）。等价的干净
构建验证由 G2 conan create（干净源码树 + test_package 5 项）与 W3 本地 CI
（build_and_test.sh 同源）覆盖，两者均 PASS。先例参照：accrete 1.0
（纯 Makefile，已 published，同样仅以 conan-verify 作为干净构建证据）。
---

**编译结束**: 2026-09-21 18:52
**最终状态**: published
