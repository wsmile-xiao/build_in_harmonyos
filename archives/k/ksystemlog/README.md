# ksystemlog

KDE 系统日志查看器：Qt6/KF6 图形应用，浏览内核、启动、认证、守护进程、X.org、
cron、apache、postfix、cups、samba 等日志文件，基于 KXmlGui 主窗口与 KIO 文件读取。

- 上游：https://invent.kde.org/utilities/ksystemlog
- 适配版本：26.04.0（archives/k/ksystemlog/26.04.0/）
- 依赖闭包：qtbase/6.11.1 + KF6 6.14.0 全闭包（13 框架）+ ecm/6.26.0
- 上游测试：autotests/ 4 项，on-device ctest 4/4 通过（100%）
- 平台适配要点：
  - Qt6PrintSupport 缺失（qtbase FEATURE_printsupport=OFF）→ 打印动作改经
    QPdfWriter（QtGui）导出 PDF（conducteo 先例）
  - journald / audit 为上游可选依赖，OHOS 上自动禁用
  - 发布 KF6 包 DT_NEEDED 携带构建机绝对/相对路径 → test_package 内建
    符号链接兜底（kfourinline 26.04.0 先例，含 sh_link 定位 .dynstr 的
    ELF 解析修正）
