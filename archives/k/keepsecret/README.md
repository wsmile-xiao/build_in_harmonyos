# keepsecret

KDE Secret Service 密码管理器 GUI（Kirigami convergent QML 应用），
可作为 KWallet、oo7、gnome-keyring、KeepassXC 等 **Secret Service 兼容提供者**
的客户端。服务运行（或可 dbus 激活）时自动发现，显示全部 secret collection
及其中的条目。

- 上游: https://invent.kde.org/utilities/keepsecret
- 归档源: https://download.kde.org/stable/keepsecret/keepsecret-1.1.0.tar.xz
- 版本: 1.1.0
- License: GPL-2.0-or-later

## 产物

- `bin/keepsecret` — 主程序（QML/Kirigami UI，内嵌
  `qrc:/qt/qml/org/kde/keepsecret`；条目/collection 数据经 libsecret-1，
  Secret Service 服务发现经 QtDBus）
- `share/applications`、`share/metainfo`、`share/icons` — desktop 元数据

## OHOS 适配（1.1.0）

上游 Qt/KF 门槛（Qt ≥ 6.8、KF ≥ 6.8）在仓基线（Qt 6.11.1 + KF 6.18.0）已满足，
无需下调。实际障碍是**制品仓缺失的 QML 模块**（与 alligator/klevernotes 同类），
共 6 个 patch：

| 文件 | 说明 |
|------|------|
| `1.1.0/conanfile.py` | Conan 配方（Kirigami 应用包打法 + zlib 图冲突 override） |
| `1.1.0/conandata.yml` | 官方 tarball URL + SHA256 + 6 个补丁清单 |
| `1.1.0/patches/0001-*.patch` | 去掉 `KF6::I18nQml` 链接，保留 `KLocalizedContext` 可见性 |
| `1.1.0/patches/0002-*.patch` | `KLocalizedQmlContext` → `KLocalizedContext`；QQC2 样式回落 `Basic` |
| `1.1.0/patches/0003-*.patch` | `About.qml` 去 `org.kde.coreaddons`，改用 `Kirigami.AboutPage` + JSON aboutData |
| `1.1.0/patches/0004-*.patch` | `Main.qml` 去 `org.kde.coreaddons`/`org.kde.config`：版本号内联、窗口状态用 `QtCore.Settings` |
| `1.1.0/patches/0005-*.patch` | `CollectionContentsPage.qml` 去 `org.kde.kitemmodels` |
| `1.1.0/patches/0006-*.patch` | 新增 `QmlSortFilterProxyModel` shim（补 `KSortFilterProxyModel`） |
| `1.1.0/test_package/` | 消费者验证：新增鸿蒙特有 ELF 适配闸 + 离屏启动冒烟 |

### 两类根因

1. **zlib 图冲突**：`kirigami-addons → kiconthemes → karchive` 钉 `zlib/1.3.2`，
   而 `libsecret/0.21.7 → glib/2.84.0.1` 钉 `zlib/1.3.1.1`。根 override
   `zlib/1.3.2`（**保持 glib 不动**）解冲突——若改 glib 版本会使 libsecret
   已发布二进制缺失，触发源码重编并因 `proxy-libintl.pc` 缺失失败（实测）。
2. **五个 QML 模块不在仓**：`org.kde.coreaddons`（kcoreaddons 以
   `KCOREADDONS_USE_QML=OFF` 构建）、`org.kde.config`（`KCONFIG_USE_QML=OFF`）、
   `org.kde.kitemmodels`（配方不 require qtdeclarative，跳过 QML 插件），
   以及 `KF6::I18nQml`（ki18n 以 `BUILD_WITH_QML=OFF` 构建）、
   `qqc2-desktop-style`。各自以在仓等价物替换。

适配详情见 `1.1.0/notes.md`。
