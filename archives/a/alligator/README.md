# alligator

KDE Plasma Mobile 播客与 RSS/Atom 订阅阅读器，Kirigami convergent QML 应用。

- 上游: https://invent.kde.org/network/alligator
- 归档源: https://download.kde.org/stable/release-service/26.04.0/src/alligator-26.04.0.tar.xz
- 版本: 26.04.0（KDE Gear 26.04.0）
- License: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL

## 产物

- `bin/alligator` — 馨鱼（alligator）RSS/播客阅读器主程序（QML/Kirigami UI，
  数据存于 SQLite，订阅抓取经 KF6::Syndication 解析）

## OHOS 适配（26.04.0）

| 文件 | 说明 |
|------|------|
| `26.04.0/conanfile.py` | Conan 配方（kirigami-addons 1.13.0 应用包打法） |
| `26.04.0/conandata.yml` | 官方 tarball URL + SHA256 + 补丁清单 |
| `26.04.0/patches/0001-*.patch` | 禁用 QQC2BreezeStyle（静态构建才需要，OHOS 共享构建跳过） |
| `26.04.0/patches/0002-*.patch` | KF6::I18nQml → KF6::I18n 的 KLocalizedContext 等价替换 |
| `26.04.0/patches/0003-*.patch` | org.kde.coreaddons AboutData → FormCard.AboutPage JSON 形式 |
| `26.04.0/test_package/` | 消费者验证：bin/alligator --self-test 离屏跑完整 QML UI |

适配详情见 `26.04.0/notes.md`。
