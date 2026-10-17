# acpi-support

## 简介
acpi-support 是笔记本电脑 ACPI 事件"胶水"脚本集:acpid 事件配置(events/)、
shell 处理脚本(无线开关/背光/扩展坞)、无线状态函数库(lib/state-funcs)与
键值常量表(key-constants),配合 acpid 把特殊功能键翻译为电源管理动作。

## OHOS 适配
- **构建系统**: 无(零编译,纯 shell/配置包;build() 以 bash -n 全量语法校验充当构建验证)
- **依赖链**: 无(acpid 为运行时协作方,非构建依赖)
- **上游仓库**: https://salsa.debian.org/debian/acpi-support
- **安装布局**(遵循 Debian):/etc/acpi(处理脚本 + 主配置)、/etc/acpi/events、
  /usr/share/acpi-support(key-constants、state-funcs)
- **版本索引**:
  - 0.143 — 2026-09-28 适配(上游 tag upstream/0.143,Debian orig tarball)
