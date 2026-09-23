# 【高难度挑战】feat(binutils): 2.46.0 适配 HarmonyOS PC

- **三方库名称**：binutils
- **上游版本**：2.46.0
- **上游仓库地址**：https://sourceware.org/git/binutils-gdb.git
- **适配路径**：路径 C（高难度挑战候选）
- **使用知识库**：E007（config.guess）、E011（HMDFS 临时目录）、
  E272（DejaGNU stty/tmpfile）、E386/E490（脚本解释器）；新增 E547 草稿
  （Clang `.addrsig` 与 GNU as 互操作）
- **智能任务平台任务**：`#3485`，精确分支 `feat/binutils-2.46.0`
- **认领记录**：`sawakage` 于 2026/09/08 19:59:25（北京时间）认领，状态 `assigned`
- **队伍名称**：中国矿业大学鸿晕当头
- **期限**：平台 `dueDate` 当前为空；按指南七天推算为 2026/09/15 19:59:25，页面值优先

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游未单独标记 unit 驱动 |
| 集成测试 | 386 | 8 个 testsuite 中的 DejaGNU `.exp` 文件 |
| 其他测试 | 9 | gprof 2 个 shell 入口 + libiberty 7 个 Make 目标 |
| **合计** | **395** | 按测试入口计数，不把断言数混入 |

386 个 `.exp` 中，gprofng 7 个随 Linux collector 组件显式关闭；其余 379 个文件
由 `make -k -j1 check` 加载，实际执行 367 个驱动，12 个为支持文件。gprof 因
`gprof_cv_sys_native=no` 为 0 discovered / 0 executed；libiberty 为 930/930 检查。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------|------|
| 单元测试 | 0 | 不变 | 上游分类不变 |
| 集成测试 | 386 | 不变 | 367 个驱动完整执行，未静默删测 |
| 其他测试 | 9 | 不变 | gprof/libiberty 边界如实记录 |
| 鸿蒙特有测试 | 2 | +2 | 安装包 ELF 工作流 + 原生程序变换/执行入口 |
| **合计** | **397** | **+2** | 本表统一按测试入口计数 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（如下）

1. **`gas/testsuite/lib/gas-defs.exp`**
   - **修改原因**：OHOS pipe transport 下原 Expect spawn 读取路径依赖 PTY。
   - **修改内容**：从已有输出文件 channel 读取；测试输入和比较逻辑不变。
2. **`libsframe/testsuite/libsframe.decode/decode.exp`、`libsframe.encode/encode.exp`**
   - **修改原因**：HMDFS 对测试 symlink 的语义受限。
   - **修改内容**：复制相同只读 DATA 文件，断言和二进制输出比较不变。
3. **`ld/testsuite/ld-elfvers/vers.exp`、`ld-elf/shared.exp`**
   - **修改原因**：负退出值被 Tcl 误作选项；已加载 DSO 需 force replace。
   - **修改内容**：使用 `send_log --` 和 `cp -f`，保留原 FAIL/PASS verdict。
4. **`ld/testsuite/config/default.exp`、`ld-elf/compress.exp`**
   - **修改原因**：Clang `-B` 仍使用 integrated assembler，未测试本轮 GNU as。
   - **修改内容**：OHOS 以普通文件部署测试 ld/as，仅在 `compress.exp` 生命周期内
     加入并恢复 `-fno-integrated-as`；该组 28/28 PASS，其他驱动标志不变。
5. **`libctf/testsuite/config/default.exp` 和相关 Makefile/libtool 入口**
   - **修改原因**：Clang 与 HMDFS 脚本入口需要显式 linker/shell。
   - **修改内容**：选择本轮 GNU ld 并由配置 shell 读取 helper。
6. **`site-stty-fix.exp`、`ohos-test-sign.py/.exp`**
   - **修改原因**：OHOS 无可用 PTY 初始化，且 GNU ld 产物运行前需要平台签名。
   - **修改内容**：使用 DejaGNU pipe；只签名当前 tmpdir 的请求程序、本地
     `DT_NEEDED` 闭包和明确的 literal dlopen 夹具，不改测试输出或 verdict。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

上游并非无测试库。另增安装包消费者是为了覆盖上游 build-tree 测试未验证的 Conan
package 边界，不将其表述为“上游无测试补全”。新增文件为
`test_package/test.sh`、两份架构夹具、`native-test.py` 和 `native-consumer.c`。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：3419/3454（98.99%）
- 新增测试用例通过率：16/16（100%，计量单位：断言）

详细口径：15 XFAIL、203 UNSUPPORTED、4 UNTESTED 不并入普通 PASS 分子；
0 UNRESOLVED、0 XPASS。35 个 FAIL 的逐项分析见
`archives/b/binutils/2.46.0/ohos-failure-analysis.md`。分类器完成 35/35 名称映射；
结合日志上下文和对照试验复核，未发现当前适配引入的失败。libiberty 另有 930/930
检查。

最终 clean run 使用全新 Conan cache，Conan create 退出码 0。安装包完整引用：

```text
binutils/2.46.0#11a4a9b63a85bc14b6f4edc65fc4fdfe:6b129b068851896169fae42d399fa922d239ce8a#79f95fb4875a2b5b802d4eaec2ee7349
```

## 补充说明

- 平台将任务 `#3485` 列在“开源鸿蒙PC专项积分赛-依赖”活动。本 PR 申请路径 C 时
  只使用 `【高难度挑战】` 一个标题前缀；活动归类由对应 Issue 请求评审确认。
- 路径 C 明确依据赛事第 3 条“含汇编等复杂架构”：官方归档含 8,815 个 `.s`、
  7 个 `.asm`，同时覆盖 BFD/opcodes/gas/ld 和多架构后端。运行时 `required: []`，
  不以依赖链庞大作为申报理由。
- 最终输入 bundle SHA256：`61f2ab642e0405787a1af1fa34e47b9e12281eb9fd1d8a93d509348fc2beec79`；
  结果归档 SHA256：`8efd26e9be91e44d4deb7eb53a4d85ebc9320dc54481f00d392936b183d7c6f3`。
- gprof 0/0 和 gprofng 组件关闭均在报告中明确，不写成通过。
- `【高难度挑战】` Issue 草稿位于 `reports/high-difficulty-issue.md`；创建 PR 时先在
  AtomGit 关联该 Issue，再在智能任务平台关联任务。
- 当前分支已 rebase 到官方 `main=7285d0428`；finish 生成的 W3 状态为通过。创建 PR
  后仍需触发官方 CI 和 `/ai review`；本地真机结果不等同于平台复审通过。
