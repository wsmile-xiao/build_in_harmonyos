# metamath 0.198 适配记录

## W0 依赖检查

- Conan 依赖：无。
- 运行时依赖：HarmonyOS/Linux libc；未声明为 Conan 依赖。
- 构建依赖：C 编译器。上游源码不需要第三方库或外部生成器。
- 远端预检：本机 Conan 2.29.1 已配置 `ohpcd`，但匿名访问返回 `system acceleration policy not enabled`；由于配方和上游审计均确认没有依赖，未产生依赖拆分任务。

## W1 源码与构建系统

- 上游仓库：`https://github.com/metamath/metamath-exe`
- 上游标签：`v0.198`
- 标签提交：`0e6fb2ebf0865fb90354839b2e586490b210d017`
- 归档 SHA256：`7029880b754ee7e7e97b4c1b5e79910222c4f258d353e9b739dc413a4f35551f`
- 源码类型：C CLI 程序，16 个 C 源文件和对应头文件。
- 归档中的 `Makefile.am` 与 `configure.ac` 只支持可选 Autotools 生成流程；官方归档没有生成的 `configure`、`Makefile` 或测试目录。
- 上游 README 明确支持直接执行 `gcc m*.c -o metamath`，本配方将其替换为 Conan profile 提供的 `clang` 并保留官方优化参数。
- 上游归档没有 `.mm` 数据库文件、测试框架或 `make check` 目标。
- 许可证：GPL version 2 or later，来自 `LICENSE.TXT` 和 README。

## W2/W3 配方与验证

- `package_type`：`application`。
- 包内容：`bin/metamath`、`share/man/man1/metamath.1`、`licenses/LICENSE.TXT`。
- 无 `conandata.yml`，源码 URL 和 SHA256 固定在 `conanfile.py`，避免触发仓库已知的预下载路径问题。
- 命令行工具按 R38 新增软件级 `archives/m/metamath/commands.json`，供 hicmd/CI 识别。
- test_package 使用六条语句的离线最小数据库，验证版本输出、源码读取和一个已完成证明的全库验证。
- 本机直接使用裸 DevEco `clang` 失败，因为未提供目标 sysroot；加入 `--target=aarch64-linux-ohos` 和 SDK sysroot 后交叉编译成功，产物为 AArch64 ELF。
- 使用隔离 Conan HOME 和临时 OHOS settings/profile 执行 `conan create`，源码下载、SHA256 校验、交叉编译、打包均成功；包内包含 `bin/metamath`、man page 和许可证。
- Windows 主机无法执行 AArch64 OHOS ELF；test_package 在跨编译时由 `can_run()` 跳过运行，shadow CI/真机需补运行证据。
- 本地 Conan 2.29.1 的默认 settings 未包含 OHOS，未修改全局配置；仓库 OHOS 适配版 Conan/profile 到 shadow CI 再验证。
- 第一次 shadow CI 运行暴露 test_package 参数错误：`metamath` 需要 `READ <file>` 命令，不能把裸文件路径作为命令参数；已修正为显式 `READ`。
- 真机输出使用 `The source has 6 statements`，不是旧版预期的 `(READ...) 6 statements have been read`；断言已按 v0.198 实际输出修正。

## 测试对比

- 上游测试：0 个。官方 v0.198 归档没有自动化测试入口。
- test_package：3 个断言，均为离线确定性行为检查。
- 上游测试未修改；新增的 `.mm` 文件仅用于消费者测试。

## W5 执行入口

```sh
conan create archives/m/metamath/0.198 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

拿到真机空闲窗口后，优先创建隔离 shadow job：

```sh
job="metamath-0.198-<timestamp>"
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job "$job" \
  --package archives/m/metamath/0.198 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/codex/$job/run-conan-heavy.sh"
```

真机验证命令已按下方 W5 结果执行完成。issue 编号按用户要求不追补，当前交接标记为 issue 待补。

## W5 真机 shadow CI 结果

- 设备：HarmonyOS AArch64，`10.62.178.77:2222`，用户 `currentUser`。
- 隔离 job：`/storage/Users/currentUser/ohos-users/codex/metamath-0.198-shadow-20260914-0130`。
- runner：`codex-metamath-metamath-0.198-shadow-20260914-0130-conan-20260914-083720-28564`。
- 执行命令：`zsh ci/conan/build_and_test.sh archives/m/metamath/0.198`。
- 退出码：`0`。
- 结果：`L0 pass`、`L1 pass`、`L2 pass`、`L4 pass`、`L5 pass`；`test_package` 输出 `PASS: metamath version, source parsing, and proof verification`。
- Conan 包引用：`metamath/0.198#4f3ccb712512339b0dd6e1056967e939:6b129b068851896169fae42d399fa922d239ce8a#deadde51504f4ef3de9155c30d56f5cb`。
- 设备 CI 额外 stderr 有旧 Git/OpenSSL 环境的仓库探测提示，但不影响本包门禁与构建测试结果。

## 可复用知识草稿

- `knowledge/drafts/DRAFT-metamath-cli-read-command-sequence.md/.kv`：记录多命令模式下必须显式 `READ "<path>"`、路径引用方式和 v0.198 稳定输出断言。
- `knowledge/drafts/DRAFT-metamath-standalone-c-cli-ohos-conan.md/.kv`：总结无外部依赖 C CLI 工具的 OHOS Conan 配方、sysroot 交叉编译、`commands.json`、`can_run()` 和 shadow CI 分层验证路径。
- 两条草稿均保留 `draft: true`，可作为本库 B 类难度提交的直接关联知识证据；其中通用的 R38 `commands.json` 和 HNP PATH 规则通过关联条目复用，不重复定义。
