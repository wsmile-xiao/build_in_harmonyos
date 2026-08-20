# freetds 1.4.23 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-21
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码: https://www.freetds.org/files/stable/freetds-1.4.23.tar.gz
2. 应用 3 个补丁 (config.guess, configure umask, getmac.c sockaddr_storage)
3. conan create (交叉编译 OHOS aarch64 profile)
4. 配置选项: --disable-odbc (鸿蒙无 unixodbc), --enable-static, --disable-shared

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 上游无 OHOS 支持 | 添加 *:HarmonyOS:*:* case 分支 |
| 2 | configure 创建临时目录失败 | HMDFS umask 077 权限问题 | umask 077 → 022 |
| 3 | sockaddr_storage 重定义冲突 | 鸿蒙内核与 Linux 头文件冲突 | 统一 rename 避免 kernel/userspace 类型冲突 |

## 源码修改

- 0001-config.guess.patch: 添加 HarmonyOS 平台识别
- 0002-configure.patch: umask 077 → 022 修复 HMDFS 权限
- 0003-src-tds-getmac.c.patch: sockaddr_storage 类型冲突修复

## 依赖版本

- 无外部依赖 (标准 C 库)

## 验证结果

- conan create (G2): PASS
- W3 本地 CI 模拟 (setup.sh + build_and_test.sh): PASS
- test_package (dbinit/dbversion/dbexit): PASS

## 注意事项

- ODBC 已禁用 (--disable-odbc)，鸿蒙平台无 unixodbc
- 安装的库: libct (ct-lib), libsybdb (db-lib)
- libtds 为内部库不安装
- G0 干净构建验证跳过 (HMDFS getcwd 限制)

---

**编译结束**: 2026-07-21 11:45
**最终状态**: built
