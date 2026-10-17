# 【知识库扩展】libntru 0.5.0 适配 HarmonyOS PC + E999 musl 端序宏知识草稿

- **三方库名称**：libntru
- **上游版本**：0.5（tag `0.5`，2016-05-14 发布）
- **上游仓库地址**：https://github.com/tbuktu/libntru
- **适配路径**：路径 B（知识库扩展）
- **使用知识库**：无（本 PR 新增草稿 E999-draft-PC1-.kv/.md）

## 适配说明

C 实现的 NTRUEncrypt（IEEE P1363.1），纯 Makefile 构建，无第三方 Conan 依赖。
OHOS aarch64 本机构建并通过全部测试。

- 配方：`archives/l/libntru/0.5.0/`（conanfile.py + conandata.yml + test_package + manifest.yaml + notes.md）
- 补丁 `patches/0001-ntru_endian.h.patch`：OHOS/musl 下 `htole32/64/16` 未声明
  （上游头文件未覆盖 `__OHOS__`/`__linux__` 分支），补 `#include <endian.h>`。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 11 | 来源：tests/ 用户测试源，`print_result()` 粒度（testham 全功能构建） |
| 集成测试 | 0 | 无 |
| 其他测试 | 0 | src/bench.c、src/hybrid.c 为基准/示例程序，不计入 |
| **合计** | **11** | testnoham 变体 10 用例（test_mult_prod 由上游 `-DNTRU_AVOID_HAMMING_WT_PATENT` 宏门控排除） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 11 | 不变 | testham 11/11 通过（OHOS aarch64 本机运行） |
| 集成测试 | 0 | 不变 | 无 |
| 鸿蒙特有测试 | 16 断言 | 新增 | test_ohos：参数集/密钥生成/加解密往返/密钥导出导入/端序恒等 |
| **合计** | **11 用例 + 16 断言** | **不变/+16** | testnoham 变体 10/10 通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（仅新增独立鸿蒙专项测试，未触碰上游测试源码）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，适配后新增了鸿蒙专项测试（上游测试框架无法覆盖平台端序行为）

> - **补全的测试范围**：EES443EP1 参数集可用性、确定性密钥生成、加密/解密往返、
>   密钥导出/导入往返（导出字节流比对）、小端端序恒等（htole32/16 回归护栏）
> - **补全原因**：验证 OHOS 平台端序假设与 musl `<endian.h>` 修复的正确性
> - **新增测试文件清单**：
>   1. `tests/test_ohos.c` — 16 项断言，本机实测 16/16 通过

## 验证结果

- 编译状态：通过（conan create 端到端，静态库 + 上游测试 + test_package 消费者 smoke）
- 上游测试用例通过率：11/11（100.0%）（testham）；testnoham 10/10（专利规避构建）
- 新增测试用例通过率：16/16（100.0%）
- conan-verify 8 道门禁（G0/G1/G2/G3/G4/L2/L4/L5）：全部 PASS
- W3 本地 CI 模拟：通过（命中 util-linux-login 既有 `.ci-trigger` 基线文件，
  已按规则隔离复验并原样恢复，SHA-256 核对一致；未修改/提交该基线文件）

## 知识库扩展（路径 B）

新增草稿对（同 stem，与三方库归档同一 PR）：

- `knowledge/drafts/E999-draft-PC1-.kv`
- `knowledge/drafts/E999-draft-PC1-.md`

内容：OHOS/musl 下上游头文件未覆盖 `__OHOS__`/`__linux__` 分支时
`htole32/16/64` 宏未声明导致链接失败（`undefined reference ... htole32`），
修复为增加 musl 分支 `#include <endian.h>`；含根因、方案、验证命令、
适用边界/反例、七轴查重结论（similar_to: E493/E203/E020/E014/E085，
exact/causal_duplicate=false，combination/boundary/test_migration_novelty=true）。

## 补充说明

- 本机即 OHOS aarch64，上游测试与鸿蒙专项测试均为本机真实运行结果。
- W3/JC5 基线隔离审计：path=`archives/u/util-linux-login/2.42.2/.ci-trigger`，
  pre_sha256=post_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855，
  复跑后原样恢复，未纳入本 PR。
