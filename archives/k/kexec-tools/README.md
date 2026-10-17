# kexec-tools

内核热启动工具集——kexec/kdump 用户态工具。`kexec` 允许从当前运行中的内核直接引导新内核（跳过固件自检），`vmcore-dmesg` 从 kdump 转储文件中提取 dmesg 日志。

- 上游：https://kernel.org/pub/linux/utils/kernel/kexec/kexec-tools.git
- 许可证：GPL-2.0
- 语言：C（零外部强制依赖，zlib 可选）
- 构建：autotools

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.0.32 | built | arm64 适配（详见 2.0.32/notes.md） |

## 平台说明（OHOS）

- 构建产物 `kexec` / `vmcore-dmesg` 可执行（`--version` 验证通过）
- `kexec_load` 系统调用在当前 OHOS 内核未实现（syscall 探针实测返回 SIGSYS）——kexec 的真实加载/热启动动作属**运行时内核依赖**，用户态工具本体按"工具构建可用性"验证；`vmcore-dmesg` 为纯文件解析工具，不受影响
