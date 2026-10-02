# qdiskinfo

QDiskInfo 是 `smartctl`（smartmontools）的 Qt6 图形前端，以 CrystalDiskInfo 风格
展示 ATA / NVMe 磁盘的 S.M.A.R.T. 健康数据。

## 版本信息

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.4-git20251119 | published | 2026-09-29 |

## 功能概述

- 磁盘列表：扫描 `smartctl --scan` 发现的 ATA / NVMe / SCSI 设备
- S.M.A.R.T. 属性表：ID / 属性名 / 当前值 / 最差值 / 阈值 / 原始值
- 状态着色与告警文案（合格 / 注意 / 异常）
- NVMe 专有日志与属性（含 ATA device statistics）
- 自检：short / long / conveyance 自检请求与中止
- ASCII 视图：`--ascii-view <device>` 直接输出设备的 SMART 原始数据
- 中英等多语言界面（翻译资源编译期可选）

## OHOS 适配要点

| 项 | 说明 |
|----|------|
| 提权命令回退 | 上游在特权路径（磁盘扫描、自检、ASCII 视图）固定调用 `pkexec`。HarmonyOS PC 没有 polkit / pkexec，`QProcess::start("pkexec", ...)` 启动失败且 `exitCode()` 为 0，上层只会拿到空结果——**既不报错也无数据（静默失败）**。补丁 0004 增加运行时探测：pkexec 存在则保持上游提权行为（Linux 无变化），不存在则直接执行命令；补丁 0001/0003 提供 `Utils.startProcess()` 并替换全部 4 处 `pkexec` 调用点。 |
| `--version` / `--help` | 上游只实现 `--ascii-view`；补丁 0002 补齐两个无 GUI 早期退出分支（在构造 `QApplication` 之前返回，不依赖显示服务器），供 CI 冒烟与用户自检。 |
| `scsi/sg.h` + SG_IO | ASCII 视图使用 `sg_io_hdr_t` / `SG_IO` ioctl 直读设备，OHOS SDK 已提供该头文件（`native/sysroot/usr/include/scsi/sg.h`），无需打补丁。 |
| smartctl 来源 | smartctl 为运行期依赖：声明 `requires("smartmontools/7.4")`（制品仓已发布 OHOS 预编译二进制），`conan install` 后 smartctl 即在运行环境 PATH 中，`getSmartctlPath()` 直接命中。上游 AppImage 同样把 smartctl 随应用一起分发。 |
| 翻译 | `ENABLE_TRANSLATIONS` 保持上游默认 OFF：qtbase 包不提供 `Qt6LinguistTools`（OHOS 无 lupdate/lrelease 原生工具链），官方 AppImage 构建同样未开启。 |
| 桌面集成文件 | `dist/QDiskInfo.desktop` 与图标安装到包内 `share/applications`、`share/icons`，不做 root 写系统目录。 |

## 已知限制

- 没有 polkit/pkexec 时，读取 S.M.A.R.T. 需要以特权用户启动（或设备节点本身可读）；
  这是 HarmonyOS PC 无提权框架的平台限制，补丁只保证不再静默失败。
- 未启用界面翻译资源（见上表），界面为英文。

## 依赖关系

| 类型 | 依赖 | 版本 | 说明 |
|------|------|------|------|
| 编译依赖 | qtbase | 6.11.1.3 | Qt6 Core/Gui/Widgets + 平台插件 |
| 运行依赖 | smartmontools | 7.4 | 提供 `smartctl` 可执行文件（制品仓已发布 OHOS 二进制） |

## 功能验证

```bash
# 消费者冒烟（含 --version/--help/--ascii-view/offscreen GUI 启动，9 项断言）
conan test <conanfile-dir> qdiskinfo/0.4-git20251119 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 手工复现
sh test_package/test_app.sh <pkg-folder>/bin/QDiskInfo
```

## 参考资料

- 上游仓库：https://github.com/edisionnano/QDiskInfo
- smartmontools：https://www.smartmontools.org/
