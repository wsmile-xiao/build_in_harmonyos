# libkgapi

## 简介
KDE PIM 的 Google API 客户端库（KPim6GAPI），提供 Calendar / Drive / Tasks /
People / Latitude / Blogger / StaticMaps 等服务的访问 API，是 kio-gdrive 等
Google 生态集成组件的底层依赖。

## OHOS 适配
- 构建系统: cmake（ECM 6.26.0）
- 编译器: OHOS clang
- KF_IGNORE_PLATFORM_CHECK=TRUE 绕过 KDE 平台白名单
- KF_MIN_VERSION 6.22.0→6.18.0（补丁，对齐 ohpcd 已发布 KF6 栈）
- BUILD_SASL_PLUGIN=OFF（SASL 插件本平台未使用）
- 上游 48 个 CTest 测试全部在 conan create 内实测运行（离线 fake 网络层）

## 依赖
- qtbase/6.11.1（Core/Network/Gui/Widgets/Xml/Test）
- kwallet/6.18.0（KF6::Wallet，账号密钥存储）
- kcalendarcore/6.26.0
- kcontacts/6.18.0
- ecm/6.26.0（tool_requires）

## 参考
- 官网: https://invent.kde.org/pim/libkgapi
