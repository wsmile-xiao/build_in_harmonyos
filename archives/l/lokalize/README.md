# lokalize

KDE 计算机辅助翻译工具（CAT）：PO/POT 文档编辑、翻译记忆与术语表管理，Qt6/KF6 桌面应用。

- 上游: https://invent.kde.org/sdk/lokalize
- 归档源: https://download.kde.org/stable/release-service/26.04.0/src/lokalize-26.04.0.tar.xz
- 版本: 26.04.0（KDE Gear 26.04.0 / KDE SDK）
- License: GPL-2.0-or-later

## 产物

- `bin/lokalize` — 翻译编辑器主程序（Qt6 Widgets + KXmlGui；翻译记忆走 Qt6 SQL 后端，
  拼写检查经 KF6::Sonnet + hunspell）
- 桌面消费者载荷：`share/applications/org.kde.lokalize.desktop`、
  `share/metainfo/org.kde.lokalize.appdata.xml`、`share/icons/`、`share/config.kcfg/lokalize.kcfg`

## OHOS 适配（26.04.0）

| 文件 | 说明 |
|------|------|
| `26.04.0/conanfile.py` | Conan 配方（KDE GUI 应用打法：Qt6 前缀 + KF6 依赖 + 上游 ctest + test_package） |
| `26.04.0/conandata.yml` | 官方 tarball URL + SHA256（无补丁） |
| `26.04.0/test_package/` | 消费者验证：离屏启动取版本号、打开真实 PO 文档有界运行 20s、安装载荷完整性 + OHOS ELF 契约 |

适配要点（不改上游源码，全部使用上游开关与 Conan 工具链变量）：

- `USE_DBUS=OFF` — OHOS 无 D-Bus 守护进程/会话总线，否则应用启动即退出
- `KF_SKIP_PO_PROCESSING=ON` — 交叉编译期无法运行 `lconvert`（界面翻译 .qm 未生成，已知取舍，见 notes.md）
- `tzdata/2026.3` + `TZDIR` — OHOS 镜像无 zoneinfo 树，供上游 `gettextheadertest` 使用
- KF6 模块保持 6.14.0 单版本链（sonnet 用 6.26.0 满足上游 `[6.14.0,7.0)` 约束）

适配详情见 `26.04.0/notes.md`，测试结果见 `26.04.0/reports/test-report.md`。
