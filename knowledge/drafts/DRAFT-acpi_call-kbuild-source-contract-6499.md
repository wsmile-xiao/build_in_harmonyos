# DRAFT-acpi_call-kbuild-source-contract-6499 - Kbuild 模块阻塞时的诚实源码契约

> **Contributor**: gcw_6YxinkyD | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-04
> **Source event**: acpi_call 1.2.2, issue pending, PR #6499

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、正式文档、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 适用场景

适用于满足以下全部条件的组件：

- 上游是外部 Linux Kbuild 模块，而不是普通 userspace 库；
- 构建需要目标内核的 configured build tree 和 `linux/module.h`、`linux/acpi.h`
  等内核头，目标 CI 只有 OHOS userspace sysroot；
- 运行验证需要 `insmod`、root 权限、导出的内核符号和真实 procfs/ACPI 接口；
- 下游仍需要从 Conan 包取得可审计、来源可追溯的模块源码。

这类组件不能通过补几个头文件桩来“编译通过”，也不能把静态检查说成内核态验证。
路径 B 的价值在于把可验证部分与明确阻塞部分分开，并让缺失交付物的门禁 fail closed。

## 问题模型

外部内核模块的 ABI 与目标内核绑定。即使源码语法可以编译，缺少匹配的
`Module.symvers`、内核配置和导出符号时，产物也不具备可加载性；即使可以加载，
procfs 和 ACPI 行为还依赖真实内核与固件。

因此存在两类常见误报：

1. 构建层伪造：用桩头或非匹配内核树生成 `.ko`，宣称适配成功；
2. 测试层伪造：`test_package` 找不到包内源码时打印 `SKIP` 并退出 0，
   CI 把未验证状态记录为通过。

正确边界是承认构建与内核态验证阻塞，同时验证仓库真正交付的源码契约。

## 推荐方法

### 1. 固定来源并显式记录加固

`conandata.yml` 记录官方源 URL 和 SHA-256；如果本地为已知内核内存安全缺陷做加固，
notes 必须列出与 pinned upstream 的差异，并保留向上游反馈的意图。不能把本地文件
摘要误写成官方 tarball 摘要。

### 2. 让包内交付物可消费

当目标 CI 无法编译模块时，配方应显式 `exports_sources` 并把实际交付的
模块源码复制到 `package/src/`。`test_package` 必须从 Conan package folder 读取
该文件，而不是从配方源目录读取，否则无法证明消费者拿到的是预期产物。

### 3. 使用 fail-closed 源码契约检查

静态检查只应覆盖构建被阻塞后仍可可靠验证的关键契约，例如 procfs 入口、ACPI 调用
入口、参数上限、清理置空、有界格式化、整数宽度、空结果保护和共享状态锁。脚本需要
区分退出码：交付源码缺失应返回阻塞码，源码契约缺失应返回失败码；两者都不能返回 0。

契约断言应避免只匹配入口初始化这类“空过”文本。对清理回归，应匹配错误路径附近的
`kfree` 与置空组合；必要时把辅助检查拆成更精确的独立断言。

### 4. 分层记录证据

报告必须至少区分四层数据：

- 上游可执行自动化测试：按真实入口统计，无套件时为 `0/0（不适用）`；
- 静态源码契约：记录断言数与通过数；
- 内核态 load/invoke：明确 `0/1` 未执行及阻塞原因；
- 包完整性：包内源码与工作区交付源码的 SHA-256 一致。

静态契约通过不能折算为内核态验证通过，上游 `0/0` 不能写成 100%。

### 5. 单独解锁目标内核验证

只有拿到匹配目标内核的 configured build tree、模块加载权限和真实硬件接口后，才单独
执行编译、`insmod`、procfs 写入/读取和 `rmmod`。该验证应有独立计划与结果记录，
不能并入普通 userspace CI。

## 与已有知识的差异

- `DRAFT-cute_files-1.0.0-upstream-zero-test-ohos-validation` 处理上游零测试但
  API 可在 OHOS userspace 中真实调用的单头库；本条处理连目标 API 编译都依赖内核树
  的 Kbuild 模块，只能做源码契约验证并显式保留内核态阻塞。
- seatd 的路径 B 使用上游 noop backend 真实执行公共 API；本条没有等价 userspace
  backend，不能引入 mock ACPI 内核语义后宣称功能通过。

因此，本条新增的可复用知识是“pinned 加固源码交付 + 包内源码契约 + 阻塞证据分层 +
fail-closed 门禁”的组合，而不是一般的跳过测试策略。

## 禁止做法

- 不要在源码缺失或契约不可检查时打印 `SKIP` 后 `exit 0`。
- 不要用少量内核头桩伪造 Kbuild 或 ACPI 环境。
- 不要把静态 grep、mock 或日志 warning 当作 `insmod` 与真实 ACPI 调用通过。
- 不要把本地加固源码描述成与官方 pinned commit 完全一致。
- 不要修改正式知识图谱、索引或预占正式 E 编号。

## 已验证示例

acpi_call 1.2.2 的 Conan 包导出本地加固后的 `src/acpi_call.c`。
`test_package/check_source.sh` 对包内源码执行 11 个契约断言，全部通过；缺失源码时
返回 2，契约缺失时返回 1。隔离 Conan Home 下的 `conan create --build=missing` 通过，
包内源码 SHA-256 与工作区交付源码一致。源码还通过临时 userspace shim 编译验证：
0、1、16 个实参解析通过，17 个实参拒绝，尾部空白不误计数。

上游自动化测试为 `0/0（不适用）`；内核模块 load/invoke 为 `0/1` 未执行，原因是
OHOS CI 没有匹配内核 build tree、root 权限、`insmod` 能力和真实 `/proc/acpi/call`。

复现入口：

```sh
CI_PACKAGES="archives/a/acpi_call/1.2.2" zsh ci/conan/build_and_test.sh
```

## 证据来源

- `archives/a/acpi_call/1.2.2/acpi_call.c`
- `archives/a/acpi_call/1.2.2/conanfile.py`
- `archives/a/acpi_call/1.2.2/test_package/check_source.sh`
- `archives/a/acpi_call/1.2.2/test_package/MANIFEST.yml`
- `archives/a/acpi_call/1.2.2/notes.md`
- GitCode PR #6499
