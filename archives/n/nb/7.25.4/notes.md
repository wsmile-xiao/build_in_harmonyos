# nb 7.25.4 适配笔记

## 编译环境
- 构建系统: prebuilt（纯 bash 脚本，无编译）
- 编译日期: 2026-09-03
- 编译器: N/A（单文件 bash 脚本，无需编译）
- 状态: published

## 编译策略

nb 是上游以单文件 bash 脚本形式分发的命令行笔记工具
（https://github.com/xwmx/nb），无需编译，直接作为 prebuilt 可执行文件
部署到 OpenHarmony PC 的 `/system/bin`。

### 部署方式
- 仓库根目录 `BUILD.gn` 使用 `ohos_prebuilt_executable("nb")` 声明
  - `source = "nb"`：脚本本体
  - `install_enable = true`，`install_images = ["system"]`
  - `install_dir = "system/bin"`
- `oh-package.json` 提供包元数据（name/version/license）
- 依赖系统 bash 运行环境（OpenHarmony PC 内置 bash）

### 与 watchexec（ELF prebuilt）的区别
- watchexec 为 ELF 二进制，需要 ELF 签名 + 动态库处理
- nb 为 bash 脚本，无 ELF/签名/动态库问题，仅需可执行权限

## 验证结果

```bash
$ nb --version
7.25.4
```

上游测试总量：`test/` 目录 134 个 `.bats` 文件、约 2298 个 `@test` 断言（bats-core 框架）。

HarmonyOS PC 实际执行结果（bats-core 1.14.0 / bash 5.3.0，2026-09-04 真机采集，
2026-09-07 依 AI review 整改口径修订）：
- 实跑 17 个 helper/env 测试文件（plan 合计 168 断言）
- **可判定证据**（11 个运行完整文件，61 断言）：48 通过 / 13 断言级失败，
  通过率 78.7%（7 个文件 33 例与上游一致；13 例失败逐类归因见报告 §4）
- 另 6 个文件（107 断言：可观察 ok 15 + 不可归因 not-ok 74 行 + 未执行 23）因
  bats 运行器 TMPDIR 只读（OHOS `/tmp`）导致运行中断/夹具失败，**不计入**
  通过率与失败归因，已逐文件在 `logs/*.tap` 文件头标注，待真机
  `TMPDIR=/data/local/tmp` 重跑后替换归档（见报告 §5）
- 完整 TAP 日志与失败归因：`reports/upstream-bats-test-report.md`

测试运行时仅将上游测试辅助脚本的临时目录从只读 `/tmp` 映射到可写目录，
未修改测试断言。`nb add`/`nb move` 夹具在采集环境失败，待真机最小场景验证
（不预断为产品缺陷）。
