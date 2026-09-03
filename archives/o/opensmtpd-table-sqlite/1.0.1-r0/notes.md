# opensmtpd-table-sqlite 1.0.1-r0 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am + bootstrap)
- 编译日期: 2026-08-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装 automake 工具依赖: `conan install --tool-requires=automake/1.18`
2. 安装 sqlite3 运行依赖: `conan install --requires=sqlite3/3.49.1`
3. 运行 bootstrap: `autoreconf -vfi` (通过 conan tool_requires 提供 automake)
4. 配置: `./configure --prefix=$PREFIX` (CFLAGS/LDFLAGS 指向 sqlite3)
5. 编译: `make -j1`
6. 安装: `make install DESTDIR=$STAGING`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | automake 未安装在系统中 | OHOS 不自带 automake | conan `tool_requires("automake/1.18")` |
| 2 | config.status 写入临时文件失败 (Permission denied) | HMDFS 不允许在 umask 077 创建的 0700 目录中写入文件 | 在 build() 中 patch config.status: `umask 077` → `umask 022` |
| 3 | configure 无法猜到 build type | OHOS 未被 config.guess 识别 | 显式 `--build=aarch64-unknown-linux-gnu` (仅探索阶段; conan recipe 由 AutotoolsToolchain 处理) |
| 4 | 3 个 -Wpointer-sign 警告 (sqlite3_column_text 返回 const unsigned char*) | 上游代码将 unsigned char* 赋给 const char* | 非致命警告, 不影响功能 |

## 依赖版本

- sqlite3/3.49.1 (conan ohpcd registry)
- automake/1.18 (conan ohpcd registry, tool_requires)

## 验证结果

```bash
# 编译成功
$ make -j1
# 二进制产物
$ file table-sqlite
table-sqlite: ELF shared object, 64-bit LSB arm64, dynamic

# 运行测试 (无参数应报错, 证明二进制可执行)
$ echo "" | ./table-sqlite
table-passwd[xxxx]: fatal: bogus argument(s)

# make check 通过 (上游无测试套件)
$ make check
```

## 注意事项

- 这是一个 **命令行应用** (application), 不是库。安装在 `libexec/smtpd/table-sqlite`
- 不需要 shared/static 选项 (不是库)
- 需要声明 commands.json (R38)
- HMDFS umask 077 workaround 已嵌入 conanfile.py build()
---

**编译结束**: 2026-08-25 01:00
**最终状态**: built
