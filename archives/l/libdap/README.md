# libdap

libdap 是 OPeNDAP 项目核心 C++ 库，实现 DAP2/DAP4 (Data Access Protocol)
科学数据访问协议——广泛用于海洋/大气/遥感数据的网络发布与访问（OPeNDAP/DODS 生态，
Hyrax/THREDDS 服务器等依赖）。

- 上游: https://github.com/OPENDAP/libdap4
- 许可: LGPL-2.1-or-later
- 构建系统: autotools
- 产物: libdap / libdapclient / libdapserver 库 + getdap / getdap4 命令行工具

## OHOS PC (aarch64) 适配状态

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.20.6 | ✅ built | 2026-09-03, 上游测试 290/292 (2 失败为环境限制) |
| 3.21.1 | ❌ failed | 2026-05-26 历史尝试 (当时缺 libtirpc/uuid conan 包) |

依赖 (制品仓): libxml2/2.15.3, curl/8.15.0, libtirpc/1.3.7, uuid/2.40.1
构建工具链 (tool_requires): automake/1.18, libtool/2.5.4, bison/3.8.2,
flex/2.6.4, cppunit/1.15.1

适配要点详见 `3.20.6/notes.md`。
