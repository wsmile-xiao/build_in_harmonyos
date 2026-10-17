# addrwatch-mysql 1.0.2 适配笔记

## 概述

addrwatch-mysql 是 [addrwatch](https://github.com/fln/addrwatch) 的 MySQL 输出变体。同一上游源码 v1.0.2，configure 加 `--enable-mysql` 后额外编译 `addrwatch_mysql` 二进制。

`addrwatch_mysql` 是一个共享内存客户端，从 addrwatch 主进程读取 ARP/NDP 数据，写入 MySQL/MariaDB 数据库。

## 与 addrwatch 的关系

| 项目 | addrwatch 1.0.2 | addrwatch-mysql 1.0.2 |
|------|----------------|----------------------|
| 源码 | 同 | 同 |
| configure | 默认 | `--enable-mysql` |
| 额外依赖 | 无 | mariadb-connector-c/3.4.8 |
| 产出二进制 | addrwatch, addrwatch_stdout, addrwatch_syslog | + addrwatch_mysql |
| 补丁 | 6 个 portability 补丁 | 相同 |
| 状态 | published | 本机前置准备中 |

## 依赖分析

### W0 依赖发布检查

| 依赖 | 版本 | 状态 | 来源 |
|------|------|------|------|
| mariadb-connector-c | 3.4.8 | ✅ published | Conan remote (ohpcd) |
| libpcap | 1.10.6 | ✅ | cmd-pkgs |
| libevent | 2.1.12 | ✅ | cmd-pkgs |
| argp-standalone | 1.5.0 | ✅ | cmd-pkgs |
| gettext (libintl) | 0.22.5 | ✅ | cmd-pkgs |

所有依赖已就绪，无需先拆依赖 PR。

### 名称不匹配处理

`configure.ac` 中:
```
AC_CHECK_LIB([mysqlclient], [mysql_real_connect])
```

`mariadb-connector-c` 提供:
- 库: `libmariadb` (非 `libmysqlclient`)
- 头: `include/mariadb/mysql.h` (非 `include/mysql/mysql.h`)

解决方案: 在 `build()` 中创建符号链接:
- `libmysqlclient.a` → `libmariadb.a`
- `include/mysql/` → `include/mariadb/`

mariadb-connector-c API 与 MySQL C API 完全兼容 (`mysql_real_connect` 等符号一致)。

## 构建系统

- **系统**: Autotools
- **补丁**: 6 个 portability 补丁 (复用自 addrwatch 1.0.2)
- **静态链接**: R26 终端工具 `-static`
- **config.guess/config.sub**: 源码不含，通过补丁 0003 使引用变为条件式 (R15)

## 验证计划

### 本机前置 (已完成)
- [x] W0 依赖检查
- [x] 源码 URL 和 SHA256 确认
- [x] 构建系统识别 (Autotools)
- [x] 配方编写
- [x] test_package 编写
- [x] 补丁文件准备

### 真机验证 (待执行)
- [ ] `conan create . --profile:build=... --profile:host=...` 本机构建
- [ ] shadow CI 单包验证
- [ ] test_package 通过 (addrwatch_mysql --help)
- [ ] conan-verify 全部通过

## 真机验证命令

```bash
# shadow CI 单包验证
CI_PACKAGES="archives/a/addrwatch-mysql/1.0.2" zsh ci/conan/build_and_test.sh
```

## 阻塞点

1. **真机验证待执行**: 本机网络受限无法下载源码包，需要真机环境验证
2. **静态链接 + mariadb-connector-c 默认 shared**: 需要确认 `-static` 链接时 mariadb-connector-c 的静态库 `libmariadb.a` 能正确使用。如果静态链接失败，可能需要在 Conan 选项中设置 `mariadb-connector-c*:shared=False`
3. **libmysqlclient 符号链接方案**: 理论可行，但需要真机实际验证 AC_CHECK_LIB 是否能正确找到

## 下一步

1. 等待真机空闲窗口
2. 执行 `conan create` 验证编译
3. 修复编译问题 (如有)
4. shadow CI 单包验证
5. 提交 PR

---

**文档日期**: 2026-08-25
**当前状态**: 本机前置完成，等待真机验证
