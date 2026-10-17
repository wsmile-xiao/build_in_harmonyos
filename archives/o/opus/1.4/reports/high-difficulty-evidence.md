# Opus 1.4 高难适配说明与复现证据

## 1. 文档用途

本文是 OpusFile 与 DOSBox Staging 前置依赖 Opus 1.4 的 Path C 举证文档，
供依赖 Issue `#1346` 与依赖 PR `#3146` 引用。文档绑定官方源码、九个
portability patch、14 个上游独立可执行入口、1 个安装包 consumer、fresh
目标 W3 r10 和独立 W4。测试统计按可执行路径，不按 Meson 标签、内部断言或
shared/static 重复运行扩充。

## 2. 上游身份与适配范围

- 上游仓库：`https://github.com/xiph/opus`
- 正式源码：`https://downloads.xiph.org/releases/opus/opus-1.4.tar.gz`
- 源码 SHA-256：
  `c9b32b4253be5ae63d1ff16eea06b94b5f0f2951b7a02aceef58e3a3ce49c51f`
- 构建系统：Meson。
- 第三方 Conan 依赖：无；本库是 OpusFile 的真实叶子前置。
- patched source tree：`401` 个文件，r8 与 r9 两套补丁表示逐文件
  SHA-256 完全一致。

## 3. Path C 逐项举证

### 3.1 AArch64 配置顺序

上游 Meson 先配置 SILK，再配置 SILK 在 AArch64 路径中使用的 CELT 变量。
`0001-meson-build-order.patch` 调整为先配置 CELT、后配置 SILK。该修改只影响
构建配置顺序，不改变 codec 源码、算法或测试判定。

### 3.2 Meson helper 的宿主执行语义

上游版本与源码生成 helper 是 Python 脚本。交叉构建中 helper 必须由 build
context 的 Python 执行，不能作为目标程序直接启动。`0002` 至 `0004` 将 helper
命令显式绑定 Python，并保持上游 version block 的语义与格式。

### 3.3 OHOS shared 输出与版本参数

`0005` 至 `0009` 把 shared library 的 `version` 与 `soversion` 参数收敛到
guarded kwargs。OHOS shared 不产生版本别名链，其他平台继续使用上游版本参数。
修改同时涉及条件、kwargs 生成和 `library()` 调用，拆分为有非空上下文的九个
patch，避免补丁边界含糊。

### 3.4 三种 patch 引擎的一致性

原 r8 三个功能 patch 在外层提交检查中暴露空白上下文表示问题。r9 不是重新
发明修复，而是将相同修改重生成为九个非空上下文 patch。验证要求：

1. 七个非 patch 候选输入在 r8/r9 间字节一致。
2. `git apply --check` 逐个接受九个 r9 patch。
3. GNU patch 以 `--fuzz=0` dry-run 和 replay 通过。
4. Conan patch-ng 逐个接受九个 patch。
5. r8/r9 应用后的 401 个源码文件逐文件 SHA-256 相同。

因此 r9 只改变补丁包装，不改变被测源树语义。

### 3.5 官方测试清单的重复标签陷阱

Meson 注册 14 个不同可执行路径，但 SILK 入口误复用前一个 CELT 标签。若按
标签去重，会漏掉真实入口；若按标签出现次数统计，又可能混淆身份。配方固定
执行路径清单：

组件 `9` 个：

1. `celt/tests/test_unit_types`
2. `celt/tests/test_unit_mathops`
3. `celt/tests/test_unit_entropy`
4. `celt/tests/test_unit_laplace`
5. `celt/tests/test_unit_dft`
6. `celt/tests/test_unit_mdct`
7. `celt/tests/test_unit_rotation`
8. `celt/tests/test_unit_cwrs32`
9. `silk/tests/test_unit_LPC_inv_pred_gain`

集成 `5` 个：

1. `tests/test_opus_api`
2. `tests/test_opus_decode`
3. `tests/test_opus_encode`
4. `tests/test_opus_padding`
5. `tests/test_opus_projection`

每个不同可执行路径只计一次；shared/static 两套 package ID 的重复执行只是构建
模式覆盖，不把 14 扩成 28。

### 3.6 安装包 consumer

`test_package/test_package.c` 通过已安装的 `Opus::opus` 完成版本查询、静音帧
编码与解码。它验证 Conan 包导出的头文件、库和 CMake target 可被下游消费，
只计 `1` 个集成流程。

### 3.7 目标 ELF 与运行顺序

native OHOS 构建在每个官方测试可执行文件完成链接后处理，再逐项运行；shared
库在安装完成后处理。r10 证据要求安装库和 consumer 是 AArch64 ELF，且目标节
计数符合约束。shared、static 和 runner 三个最终退出值都必须为零。

## 4. 失败演进、根因与实现取舍

| 阶段 | 现象 | 根因 | 修复与取舍 |
|---|---|---|---|
| 初始 AArch64 Meson | SILK 配置使用尚未生成的 CELT 状态 | 子目录配置顺序 | 先 CELT 后 SILK，不改 codec 源码 |
| helper 执行 | 交叉环境中 Python helper 启动语义不稳定 | helper 属于 build context | 显式使用 Python 命令执行 helper |
| OHOS shared | 默认产生版本化输出与别名 | Meson `version/soversion` kwargs | 只在 OHOS 省略，其他平台保留 |
| r8 外层检查 | 三个功能 patch 含空白上下文表示 | patch 包装形式不利于外层校验 | 重生为九个非空上下文 patch |
| r8/r9 对比 | 必须证明重生没有改变运行输入 | patch 数量已变化 | 三种 patch 引擎 + 401 文件哈希等价 |
| 上游清单 | 两个不同路径共享标签 | 上游 Meson 标签复用 | 按 14 个实际路径运行与统计 |
| review-fix 后 r10 | 需重新绑定候选与目标证据 | HEAD 输入发生变化 | 17/17 candidate manifest，fresh shared/static 全跑 |

## 5. 官方全量测试与真实结果

| 类型 | 独立入口 | shared | static | 逻辑结果 |
|---|---:|---:|---:|---:|
| 上游组件 | 9 | `9/9 PASS` | `9/9 PASS` | `9/9 PASS` |
| 上游集成 | 5 | `5/5 PASS` | `5/5 PASS` | `5/5 PASS` |
| 安装包 consumer | 1 | `1/1 PASS` | `1/1 PASS` | `1/1 PASS` |
| 合计 | 15 | `15/15 PASS` | `15/15 PASS` | `15/15 PASS` |

上游结果为 `14/14`，新增 consumer 为 `1/1`。重复标签没有漏测，不同 package
模式没有重复计数。

## 6. fresh W3 r10 与证据哈希

fresh 目标 W3 r10 的 shared/static Conan create、14 个官方路径、1 个 consumer
与 runner 均完成，最终退出值全部为 `0`。

```text
candidate manifest 16844f7561aaa8ba04ed76f08036d8f6dacb468c62e41ac281d9efd7b111a02a
evidence archive fabaa324089dbf56fcd772dfaf67e5c5c7d8bd047ea7545cfcfeba11af777c36
evidence closure 4ccfee475654a0136946e68b3d73f247c9eb3250747c1fffc9ae1df2dd4695a1
shared log 7bedc44db8b5b905b54146cd7534ada9f95c756d555b5fcdbfaf5975c6b4023d
static log ef13504fa18ab496f291fc8eba3adbefd4769ae7281f6757e42e0da0f4d17193
r9 patch candidate f72ec9812f258fae032beb56979a2c5d50a86894f511df0f7564e41c6d4125d1
```

独立 W4 r6 绑定原 HEAD `9860e3b849d6c04971d224a3fa7337a7ccb1e6a8`，结论为
`PASS, P0=0, P1=0, P2=0, P3=3`。P3 是改进建议，不影响已经完成的
14/14 上游与 1/1 consumer 结果。新增本文后需由独立 W4 重新绑定新 HEAD。

## 7. 复现步骤

1. 校验官方源码 SHA-256。
2. 在 fresh 源树按顺序应用九个 patch，并分别运行 git apply、GNU patch
   zero-fuzz 与 Conan patch-ng 检查。
3. 生成 patched tree manifest，确认 401 个源码文件与冻结等价树逐项一致。
4. 用 MesonToolchain 开启 tests，关闭 docs 与 extra-programs，分别创建
   shared/static 包。
5. 不依赖 Meson 标签，逐一执行固定的 9 个组件和 5 个集成可执行路径。
6. 安装后用 `Opus::opus` 构建并执行一个 consumer。
7. 记录 shared/static/runner 唯一退出值、每项终态和 SHA-256 闭包。
8. 对新 HEAD 运行独立 W4，只要存在 P0/P1 就先修复再复审。

## 8. 目标验证边界

- 已证明：官方源码身份、九个补丁可重放、401 文件等价、OHOS arm64
  shared/static 包创建、全部 14 个官方入口、1 个 consumer、AArch64 ELF 与
  evidence closure。
- 未把 Meson 标签当作唯一身份，也没有把同一入口的构建模式、断言或重复运行
  计成新测试。
- 本库没有外部第三方 Conan 依赖，也不需要独立网络服务。

## 9. 积分项说明

| 项目 | 本库事实 | 当前申报边界 |
|---|---|---|
| 测试框架/工具链（10 分，证明材料需 Wiki） | 建立 14 路径清单、重复标签保护、三种 patch 引擎等价和目标证据闭包 | 正式 Wiki 发布前不把本报告单独写成 10 分已取得；本文可作为 Wiki 原稿 |
| 搭建服务（2-5 分） | 未搭建独立服务 | 不申报 |
| 远程拉取资源并解决环境依赖（0.5 分） | 绑定 Xiph 正式源码并完成无第三方依赖的 fresh 目标构建 | 可按规则申报，最终以审核为准 |

## 10. Issue 与 PR 引用文本

Issue `#1346` 与 PR `#3146` 应同时引用：

```text
Path C 详细举证：archives/o/opus/1.4/reports/high-difficulty-evidence.md
```

PR 标题继续只使用 `【依赖项】` 前缀；不得为同一分支再创建第二个 Issue 或 PR。
