# libaccounts 1.17 适配笔记

## 上游信息
- 名称: libaccounts-glib (Accounts-SSO 在线账户框架，上游项目名)
- 归档包名: libaccounts（对齐平台任务名，R40 分支门禁要求 分支名 feat/libaccounts-1.17 去前缀 == 包名-版本；产物 .so 与头文件路径仍为上游名 libaccounts-glib/accounts-glib）
- 版本: 1.17
- 上游: https://gitlab.com/accounts-sso/libaccounts-glib
- 标签: 1.17 (commit 30301bac)
- 构建系统: autotools (configure.ac + Makefile.am)
- 语言: C

## 依赖
- glib2/2.88.0.1 (glib-2.0, gio-2.0, gio-unix-2.0, gobject-2.0)
- libxml2/2.15.3.1
- sqlite3/3.53.4
- check/0.15.2 (测试框架, build-time)

## 适配修改
1. 禁用 gobject-introspection (OHOS 无此功能)
2. 禁用 gtk-doc 文档生成
3. 禁用 python 绑定 (pygobject 不可用)
4. 移除 -Werror 标志 (glib 2.88 有 deprecated API 警告)
5. 移除 docs 和 pygobject 子目录
6. 添加 AM_PROG_AR 到 configure.ac
7. 修复 LIBACCOUNTS_REQUIRED 多行变量为单行
8. 修复 /tmp 只读问题 (E002): 测试中 /tmp/result.xml 和 /tmp/check_ag.lock 改用 $TMPDIR

## 上游测试
- 测试框架: check (libcheck)
- 测试文件: tests/check_ag.c
- 测试用例数: 44 (START_TEST count)
- 测试套件: accounts-glib-testsuite
- 测试结果: 0/44 通过 (0%)
- 失败原因: OHOS 平台无 D-Bus daemon 和 machine-id 文件
  - "Failed to get D-Bus connection (Cannot spawn a message bus without a machine-id)"
  - 所有测试因无法初始化 AgManager (需要 D-Bus) 而失败
  - Failures: 5, Errors: 39
- XML DTD 验证测试: 1/1 通过 (xml-dtd-validate.sh)

## 编译验证
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 构建系统: autotools (autoreconf + configure + make)
- 编译状态: 成功
- 产物: libaccounts-glib.so, accounts-glib-testsuite, test-process

## 已知限制
- OHOS 平台无 D-Bus: 导致 44 个上游测试全部失败
  - libaccounts-glib 的 AgManager 需要 D-Bus 连接
  - OHOS 无 /var/lib/dbus/machine-id 或 /etc/machine-id
- glib 2.88 兼容性: 上游代码使用 deprecated GSimpleAsyncResult API
