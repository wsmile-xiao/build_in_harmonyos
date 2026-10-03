# libydpdict 1.0.4

YDP 词典读取库，支持索引、词目查询、RTF 释义及 Windows1250/UTF8 转换。

上游：[wojtekka/libydpdict](https://github.com/wojtekka/libydpdict)。
许可证：LGPL-2.1。

## 功能概述

- 打开 YDP 词典，读取词目及释义，查询和遍历词目。
- 转换词典 RTF 内容及 Windows1250/UTF8 字符编码。
- 为 C/C++ 消费者提供词典读取接口。

## HarmonyOS PC 适配

HMDFS 临时目录权限及 Make jobserver 的行为与常见 Linux 文件系统不同；
配方通过本地临时目录辅助脚本和串行 Make 处理，并保持 configure/config.status
使用一致的 shell。上游检查目录需显式构建，检查程序需实际执行。

消费者通过 `find_package(libydpdict REQUIRED)` 导入 `libydpdict::libydpdict`。
版本索引见 [软件元数据](manifest.yaml)，具体构建配置、真机验证结果及已知发布门禁
见 [移植记录](https-github.com-wojtekka-libydpdict/notes.md)。

## 依赖关系

编译需要 HarmonyOS C/C++ 工具链、Make、Python 3、Conan 2，以及用于消费者验证的 CMake。
运行依赖系统 C 运行库和 iconv 接口，无额外 Conan 库依赖。
上游的 libxml2 支持是可选功能，本归档未启用；相关测试边界见版本移植记录。

## 路线 B 知识贡献

成对草稿 [E14722-draft-YDPB](../../../knowledge/drafts/E14722-draft-YDPB.md)
记录发布包的 `DIST_SUBDIRS` 与默认 `SUBDIRS` 不一致造成的检查程序漏构建，
包含真实失败、修复、复算命令及与既有 runner 派发知识的边界。
归档中的 `build_support/verify_upstream_census.py` 可校验官方发布包并复算清点结果。
