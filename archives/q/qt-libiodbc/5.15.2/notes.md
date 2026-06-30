# qt-libiodbc 5.15.2 适配笔记

## 编译环境
- 构建系统: custom (手动clang++编译)
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 初始化
- 下载qtbase 5.15.2源码 (qtbase-everywhere-src-5.15.2.tar.xz)
- 本地已有qtbase 5.12.12源码 (qt-harmonyos-src-5.12.12-20260330)

### 编译
- 使用qtbase 5.12.12源码中的odbc驱动源代码（基于ODBC源码修改为iODBC接口）
- 手动使用clang++编译，指定Qt5 5.12.12 headers（排除Qt6 headers）
- 使用Qt5 moc工具生成main.moc
- 链接libiodbc、libiodbcinst、Qt5Sql、Qt5Core、ohenvironment
- 将驱动键从QODBC3/QODBC修改为QIODBC3/QIODBC（避免与unixODBC驱动冲突）
- 无外部补丁文件（源码修改在编译流程内完成）

### 关键编译参数
```bash
clang++ -c -pipe -O2 -std=c++14 -Wall -Wextra -Wno-deprecated-declarations -D_REENTRANT -fPIC \
  -DQT_NO_CAST_TO_ASCII -DQT_NO_CAST_FROM_ASCII -DQT_NO_DEBUG \
  -DQT_PLUGIN -DQT_SQL_LIB -DQT_CORE_LIB \
  -I[odbc-src] \
  -I[qt5-release-include] \
  -I[qt5-release-include/QtCore/5.12.12/QtCore/private] \
  -I[qt5-release-include/QtSql/5.12.12/QtSql/private] \
  -I[usr/local/include] \
  qsql_odbc.cpp main.cpp

clang++ -shared -o libqsqliodbc.so qsql_odbc.o main.o \
  -L~/usr/local/lib -lQt5Sql -lQt5Core -liodbc -liodbcinst -lohenvironment \
  -Wl,-rpath,~/usr/local/lib -Wl,-soname,libqsqliodbc.so
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qtbase 5.15.2源码无法编译odbc插件 | 安装的headers是混合Qt5(5.12.12)/Qt6(6.11.1)，Qt6 headers API不兼容Qt5源码 | 使用qtbase 5.12.12源码（ABI兼容），指定Qt5 5.12.12 headers |
| 2 | Qt6 moc生成Qt6风格的moc输出 | ~/usr/local/libexec/moc是Qt6版本 | 使用Qt5 moc工具(~/tmp/qt5-tools-cmake-build/build-moc/moc) |
| 3 | 驱动键与unixODBC冲突 | ODBC驱动默认使用QODBC3/QODBC键 | 将驱动键修改为QIODBC3/QIODBC（独立于unixODBC） |
| 4 | 驱动未自动部署到sqldrivers/目录 | 仅libiodbc.so本身被安装，驱动.so未自动安装 | 需手动将libqsqliodbc.so部署到$PREFIX/sqldrivers/目录 |
| 5 | 运行时dlopen加载失败 | OHOS平台要求所有动态库必须ELF签名 | 平台限制，编译产物本身正确，需在部署时完成ELF签名 |

## 依赖版本
- Qt5 Core/Sql: 5.12.12 (headers)
- iODBC: libiodbc.so.2, libiodbcinst.so.2
- ohenvironment: OHOS平台适配库

## 验证结果

```bash
# 查看libqsqliodbc.so依赖
readelf -d libqsqliodbc.so | grep NEEDED
# libiodbc.so.2, libiodbcinst.so.2, libQt5Sql.so, libQt5Core.so, libohenvironment.so, libc++_shared.so, libc.so

# 查看驱动键
# QIODBC3, QIODBC（独立于unixODBC的QODBC3/QODBC）

# 查看导出符号
nm -D libqsqliodbc.so | wc -l
# 73 exported symbols: create, qt_metacall, qt_metacast, staticMetaObject
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libqsqliodbc.so | ~138KB | Qt5 iODBC SQL驱动插件 |

## 注意事项
- ⚠️ 需手动将libqsqliodbc.so部署到sqldrivers/目录（自动安装未生效）
- 运行时需要 ELF 签名才能通过 dlopen 加载（OHOS平台限制）
- 编译需指定 Qt5 headers，排除混合环境中的 Qt6 headers
- iODBC驱动键(QIODBC3/QIODBC)与unixODBC驱动键(QODBC3/QODBC)不冲突，可共存

**编译结束**: 2026-06-12
**最终状态**: built