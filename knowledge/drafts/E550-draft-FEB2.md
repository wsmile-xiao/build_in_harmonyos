# E550 — HarmonyOS PC 无 polkit/pkexec：固定 `QProcess::start("pkexec", ...)` 提权失败却 `exitCode()==0`，功能静默失效

> **Status**: DRAFT（待主编审核） | **贡献者**: FEB2 | **更新**: 2026-09-29
> **来源**: qdiskinfo 0.4-git20251119 HarmonyOS PC 适配（`archives/q/qdiskinfo/0.4-git20251119`，Qt6 Widgets 磁盘 S.M.A.R.T. 查看器）

## 错误特征

程序可以正常启动、界面正常，但**功能静默失效**，日志里没有任何显式报错：

```text
$ <pkg>/bin/QDiskInfo --ascii-view /dev/nvme0
# 无输出、无报错；GUI 中设备列表为空
```

典型误判方向（都不是原因）：
- 权限位 / 属主问题
- 设备节点不存在（`/dev/nvme0` 实际存在且非 root 可读）
- 被调用的外部工具（smartctl）自身有问题（手动执行完全正常）

真实情况是**提权进程根本没起来**：HarmonyOS PC 上没有 polkit/pkexec。

```bash
$ command -v pkexec        # 无输出 —— 平台确实不带 polkit
```

## 触发条件

- 平台: HarmonyOS PC（本机即 HarmonyOS PC，aarch64）
- 代码形态: 用 Qt 的 `QProcess` 启动特权外部命令，且**硬编码** `pkexec`
- 关键陷阱: `QProcess::start("pkexec", args)` 在可执行文件不存在时的返回与普通失败不同——`exitCode()==0`、`isOpen()==false`；只判断 `exitCode()` 的上层代码会把"启动失败"当作"命令执行成功但无输出"

## 根因分析

1. 平台缺失：OHOS PC 未提供 polkit/`pkexec`，任何依赖 polkit 完成特权提升的调用链都会断在第一步。
2. 静默失败：`QProcess::start()` 对不存在的程序不会失败——这是 Qt 的异步启动语义（`errorOccurred` 才携带 `FailedToStart`）；只检查 `exitCode()`/`isOpen()` 的代码看不到任何异常，于是把"进程不存在 → 无输出"当成"命令成功但输出为空"，最终表现为空列表/空字符串。
3. 未做工具存在性检查：即使 `pkexec` 存在，被提升的命令（如 `smartctl`）也可能不在 PATH 上，同样应显式报错。

## 解决方案

### 推荐方案

**运行时探测 + 直接执行回退**，而不是删除提权逻辑（Linux 上游语义必须保持）：

1. `findExecutable(name)`：按 `PATH` 逐目录探测可执行文件（不要依赖 `which` 命令，OHOS 上不一定有；用 `QFileInfo::isExecutable()` 判断）。
2. `getPrivilegeElevator()` → `findExecutable("pkexec")`，为空表示平台无 polkit。
3. `startProcess(QProcess &proc, program, args, needs_root)`：
   - 有提权器：`pkexec program args`（保持上游行为不变）
   - 无提权器：直接 `program args`（此时能否读到数据取决于调用方权限/设备节点是否可读，但至少不再是"无输出"）
4. 对被调用的外部工具做存在性检查，缺失时给出明确的用户可见错误（对话框/日志），而不是返回空字符串。
5. 测试上要给一个可观测断言：把外部工具替换为记录调用的桩脚本，断言桩日志里确实出现了 `--scan` 与 `-x --json=o <device>`，从而证明"提权缺失时命令被直接执行"这条回退路径真的走到了。

### 禁止做法

- ❌ 只把 `pkexec` 字符串删掉——在 Linux 上会丢失正常提权语义（上游行为回归）
- ❌ 用 `QProcess::start()` 的返回值判断启动成功——应连接 `errorOccurred` 或先做可执行文件探测
- ❌ 让失败路径返回空字符串（上层无法区分"失败"与"无数据"）

## 验证

```bash
# 平台事实
command -v pkexec || echo NO_POLKIT

# 功能回退验证（桩 smartctl 记录调用参数）
PATH=<stub_bin>:$PATH QT_QPA_PLATFORM=offscreen HOME=$PWD/home TMPDIR=$PWD/tmp \
  <pkg_folder>/bin/QDiskInfo &
sleep 8; kill $!
grep -- '--scan' smartctl-calls.log          # 期望命中
grep -- '-x --json=o' smartctl-calls.log     # 期望命中
```

## 关联条目

- 相关: E077（OHOS ELF 签名，本适配同样涉及）
- 相关: E405（OHOS 上裸命令名/`shutil.which`/PATH 相关行为差异）
- 易混: 权限位/SELinux 类条目（本问题的症状同样是"什么都没发生"，但根因完全不同）
