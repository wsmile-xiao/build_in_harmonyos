# E565-draft-7B2F — R51 无测试上游的大规模变体（test_package 内的批量交叉校验）

## 错误面
- **触发**：R51 上游测试三步法的"清点→运行→回填"，遇到**上游确无测试**的
  **大型** shell/元数据型包（大型 Debian blend、多二进制包元包、多版本 JSON 等等）
- **阶段**：testing（适配校验 / PR 申报）
- **签名**：`find . -iname '*test*'` 输出为空 / 无 tests/ 目录 / ctest、pytest
  注册数 = 0，同时存在 40+ 级待校验清单（tasks/ 任务文件、多段落 tasksel desc、
  control 多 Package 声明、dependency_data 多版本 JSON）

## 识别
- severity: 1（🟢minor —— 非编译错误；是 R51 申报场景的合规处理模板）
- category: testing, detection, packaging, ohos
- 关联：E563（小型 blend 的补测模板）；E564（配套的 R47 大型 blend 分流判定）

## 诊断
R51 要求适配前清点上游测试并**实测回填 N/N/通过率（禁占位符）**；
"上游确无测试"必须附清点证据。

debian-science 1.15 实测清点（R51 证据，写入 `test_package/MANIFEST.yml`
的 `upstream_test_evidence`）：

```console
$ find . -iname '*test*'                        # → 输出为空
$ find . -type d -iname '*test*'                # → 无 tests/ 目录
$ find . -name 'CTestTestfile.cmake' | wc -l    # → 0
$ find . -name 'test_*.py' | wc -l              # → 0
$ find . -name '*.c' -o -name '*.cpp' | wc -l   # → 0
```

97 文件构成：Makefile（仅 include blends-dev）、debian/、config/、tasks/(46)、
dependency_data/(38 个历史版本 JSON 0.1→1.15)、debian-science-tasks.desc、
COPYING。**零 C/C++ 源码、零可执行程序、零测试框架** —— 唯一可验证资产 =
打包结构/元数据有效性，且规模达 **45 二进制包 + 46 tasks + 42 desc 段落 +
41 Key + 46 快照键**，须**批量一致性**校验而非逐包抽查。

## 方案
把批量校验做进 **`test_package/`（消费者测试）**——使验证与交付物同源、
随 CI 自动执行（关键升级：不再依赖独立脚本）：

| 类 | 校验内容（大规模批量口径） | 断言数 |
|---|---|---|
| ① 布局 | tasks/ + tasksel desc + registry.json + 官方快照 + licenses/copyright 存在性 | 5 |
| ② tasks/ 批量 | 46 文件、Task/Description 非空、Install 布尔（18 true / 28 false） | 5 |
| ③ desc 结构 | 42 段落、父任务 `debian-science`、41 个 `Key:` 且全部映射到已打包文件 | 5 |
| ④ registry 交叉复核 | counts 三项 + 文件集合 + 逐任务 title/depends/suggests/recommends + 降级语义 | 6 |
| ⑤ control 声明 | 45 包、全 `Architecture: all`、`science-*` 前缀、描述摘要 | 4 |
| ⑥ 官方快照 | 主题集合 == tasks/ 集合、引用成员命名规范、引用计数一致 | 4 |
| ⑦ semantics | conan_requires == none、blends 降级规则、版本一致 | 4 |
| **合计** | | **33** |

运行与上报：

```bash
# 在仓库根目录执行
conan create archives/d/debian-science/1.15 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
# test_package → ALL checks PASSED（33/33，RC=0）
```

- 逐项 `[PASS]`/`[FAIL]` 输出 + 通过率 N/N，**运行日志留档佐证**；
- 测试脚本 bug 与通过率修正都要留日志（本次自检阶段抓到 3 处解析口径缺陷 →
  修正后 33/33；日志留存，避免"只报最终数字"的审计质疑）。

### 大规模特有：三处解析口径（本次实测踩坑，必须写进套件）
1. **blends-inject 注入注释行**（首字符 `;`，如
   `; Added by blends-inject 0.0.7. [Please note here if modified manually]`）
   是机器注入注释，**不得折入字段值**——否则包名会混入注释文本（本次 5 个
   tasks 文件受影响：distributedcomputing / neuroscience-cognitive /
   neuroscience-modeling / numericalcomputation / psychophysics）；
2. **空折叠续行**（仅一个空格的行）折为空，不做 `+ "\n"`；
3. **Debian 依赖字段的候选式与逗号列表**：快照中 13 条为 `a | b` 形式
   （如 `gromacs|gromacs-mpich|gromacs-openmpi`、`abinit | mpqc | openmx | psi3`），
   必须按 `[|,]` 拆成员后**逐成员**校验命名规范——按单一包名校验会误报
   上游"命名非法"（拆分后 0 条非法）。

## 禁止
- ❌ PR 模板测试对比表填"待验证 / N/A / 待 CI 验证"等占位符（R51 硬性拒绝）
- ❌ 谎报上游测试数（pixman 42 个测试文件谎报 0 被评审反查揭穿）
- ❌ 对大规模清单只抽查不批量校验；或把"解析器口径过窄"当成上游缺陷
  （误报会被审计按 R52 审计失真处理）
