# libaccounts-qt 1.13 适配笔记

## 编译环境
- 构建系统: qmake (upstream) → CMake (custom, since qt5-qtbase conan package does not ship qmake)
- 编译日期: 2026-08-27
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: https://gitlab.com/accounts-sso/libaccounts-qt/-/archive/1.13/libaccounts-qt-1.13.tar.gz
2. SHA256: 9c1a5310672992ef3c67207705dd12091287bd038f87ab4765a868ed6c26c36b
3. 应用3个补丁 (QString::null → QString(), 移除tests子目录)
4. 使用自定义 CMakeLists.txt 构建 (替代qmake)
5. 依赖: qt5-qtbase/5.15.2.2, libaccounts-glib/1.27, glib2/2.88.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | QString::null deprecated | Qt5 移除了 QString::null | 改为 QString() |
| 2 | tests 子目录编译失败 | tests 依赖 QtTest 且平台不兼容 | 从 SUBDIRS 移除 tests |
| 3 | qmake 不可用 | qt5-qtbase conan 包不包含 qmake 工具 | 编写自定义 CMakeLists.txt |
| 4 | gio/gdesktopappinfo.h not found | glib2 gio-unix-2.0 include dir not exposed via CMakeDeps | Pass GLIB_GIO_UNIX_INCLUDE_DIR to CMake |
| 5 | Linking shared lib fails with -fPIC | zlib static lib not compiled with -fPIC | Default to static library build |

## 源码修改

- 0001-Accounts-account.h.patch: QString::null → QString()
- 0002-Accounts-manager.h.patch: QString::null → QString() (regenerated for accounts-sso source)
- 0003-accounts-qt.pro.patch: 移除 tests 子目录
- CMakeLists.txt: 自定义 CMake 构建文件 (替代 qmake)

## 依赖版本

- qt5-qtbase/5.15.2.2 (Qt5Core, Qt5Xml)
- libaccounts-glib/1.27 (accounts management C library)
- glib2/2.88.0 (gio-unix-2.0 headers)

## 验证结果

```bash
conan create . --build=missing -pr=ci/conan/profiles/ohos-aarch64
# Build succeeded, test compiled and ran
```

## 注意事项

- 库目标名: accounts-qt5 (Qt5版本)
- 头文件安装路径: include/accounts-qt/Accounts/
- moc 需要处理3个Q_OBJECT头文件: account.h, account-service.h, manager.h
- 默认静态构建以避免 -fPIC 传递依赖问题

---

**编译结束**: 2026-08-27
**最终状态**: published
