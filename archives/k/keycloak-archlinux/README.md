# keycloak-archlinux — Arch Linux Keycloak 主题

## 一句话说明
keycloak-archlinux 是 Arch Linux 官方的 Keycloak IAM 主题包（上游仓库即
Arch GitLab 项目 keycloak-archlinux-theme）：为 Keycloak 的登录/注册/账户/
管理台/邮件/欢迎页提供仿 Arch Linux 官网视觉的主题界面，打包为 Keycloak
provider JAR（纯 Web 资源，零 C/C++ 代码）。

## 功能概述
- 五个主题子类型：login / account / admin / email / welcome
- 经典 FTL 模板覆盖 + 主题 CSS/品牌图片（logo、登录背景、favicon）
- i18n 文案资源（messages_en.properties）
- `META-INF/keycloak-themes.json` 主题注册文件（Keycloak provider 加载入口）
- 运行时宿主为 Keycloak 服务器本体（上游声明 keycloak >25）；主题 JAR 自身
  为纯资源制品，本仓库不提供也不需要 Keycloak 服务器配方

## OHOS 适配
- **构建路径**：上游有两条构建路径——`v2/` keycloakify（React+Vite+yarn+maven，
  Arch PKGBUILD 所用）与根目录 gradle 经典 FTL 路径（上游 README 文档化、上游
  CI 同款命令）。OHOS 采用 **gradle 经典路径**：keycloakify 的 vite 硬依赖
  esbuild 外来预编译二进制，被 HarmonyOS SecureAccessFence 拒绝 exec
  （仅 OHOS 工具链构建的 ELF 可执行），证据链详见 notes.md。
- **零编译**：主题 JAR 为纯资源装配（27 个资源文件），构建只需 JDK 17 +
  gradle wrapper（腾讯镜像预下载 + GradleWrapperMain 直调，keycloak-metrics
  同款方案）。
- 运行：将 JAR 放入 Keycloak 服务器 providers/ 目录即可（主题随 Keycloak
  运行时加载，不依赖设备原生环境）。

## 依赖关系
- 编译：bishengjdk 17.0.13、gradle 9.3.0（镜像预取）
- 运行：无（资源 JAR；宿主为用户自备的 Keycloak 服务器）

## 参考资料
- 上游仓库：https://gitlab.archlinux.org/archlinux/keycloak-archlinux-theme （tag v2.0.1）
- Arch 包页：https://archlinux.org/packages/extra/any/keycloak-archlinux-theme/
- 版本：2.0.1（Apache-2.0）
