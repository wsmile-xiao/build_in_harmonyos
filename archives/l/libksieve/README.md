# libksieve

KDE PIM 邮件过滤（Sieve / ManageSieve 协议）支持库。为 KMail 等 KDE PIM 客户端提供
Sieve 脚本解析、ManageSieve 协议客户端、脚本管理与基于图形界面（Qt WebEngine）的
Sieve 脚本编辑器。

- 上游: https://invent.kde.org/pim/libksieve
- 许可证: GPL-2.0-only（KSieve 解析器部分为 SPDX 文件级标注）
- 归档版本: 25.12.3（KDE release-service，PIM_VERSION 6.6.3）

## 产物与依赖

该库一次构建 4 个库：

| 库 | CMake 包 | 关键依赖 |
|----|---------|---------|
| KPim6KSieve（解析器） | KPim6KSieve | QtCore + KF6I18n |
| KPim6KManageSieve（协议客户端） | KPim6KManageSieve | KIOCore/KIOWidgets + Sasl2 |
| KPim6KSieveCore（脚本引擎） | KPim6KSieveCore | PimCommon, Mime, MailTransport, IdentityManagementCore |
| KPim6KSieveUi（脚本编辑器 UI） | KPim6KSieveUi | **QtWebEngineWidgets**, KIO, PimCommon 全套 |

顶层 CMake 无条件生成全部 4 个库，并硬 REQUIRED `Qt6::WebEngineWidgets`（无上游开关
可跳过 KSieveUi），因此完整构建强依赖 qtwebengine 包。

## OHOS 适配要点

- KDE PIM 25.12.3 线：kpimtextedit / kidentitymanagement / kimap / kmailtransport /
  kmime / libkdepim / pimcommon（KPim6 25.12.3）；KF6 6.18.0 线；Qt 6.11.1 线。
- `BUILD_TESTING=ON` 接入上游 CTest（解析器层 `autotests/` 注册 2 个用例）。
- `BUILD_QCH=OFF` / `KF_IGNORE_PLATFORM_CHECK=TRUE` / `KF_SKIP_PO_PROCESSING=ON`，
  并 `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON`（DocTools 上游为 OPTIONAL）。
- 安装产物做 OHOS `.codesign` section 移除 + binary-sign-tool 重签。
- 已知限制：qtwebengine（Chromium 栈）在制品仓是否可用直接决定完整 4 库构建能否通过；
  详见版本目录 notes.md。
