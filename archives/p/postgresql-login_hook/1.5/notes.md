# postgresql-login_hook 1.5 适配笔记

## 编译环境
- 构建系统: makefile (PGXS)
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 搜索软件来源：通过 GitHub API 找到 splendiddata/login_hook 项目
2. 初始化编译：`ohc-run.py init-build postgresql-login_hook 1.5 --url=https://api.github.com/repos/splendiddata/login_hook/tarball/refs/tags/version_1.5`
3. 修复 PostgreSQL 17 API 变更：将 `IsBackgroundWorker` 替换为 `AmBackgroundWorkerProcess()`
4. 替换 GNU install：将 toybox install wrapper 替换为 GNU coreutils ginstall
5. 编译成功：`make` && `make install DESTDIR=$TEST_PREFIX`
6. 打包生成：`postgresql-login_hook-1.5-ohos-aarch64.tar.gz`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `IsBackgroundWorker` 未定义 | PostgreSQL 17 API 变更，该变量被替换为 `AmBackgroundWorkerProcess()` | 修改 login_hook.c，替换两处调用 |
| 2 | install 命令不支持多文件 | toybox wrapper 不支持多文件安装 | 删除 wrapper，创建软链接指向 ginstall |

## 源码修改

- **0001-login_hook.c.patch**
  - 将 `IsBackgroundWorker` 替换为 `AmBackgroundWorkerProcess()`
  - 修改两处：第78行和第106行
  - 原因：PostgreSQL 17 不再使用 `IsBackgroundWorker` 变量

## 依赖版本

- PostgreSQL: 17.0
- GNU coreutils: 9.10 (ginstall)

## 验证结果

```bash
# 编译成功
clang -Wall -Wmissing-prototypes ... -c -o login_hook.o login_hook.c
clang ... -shared -o login_hook.so login_hook.o

# 安装产物
ls /storage/Users/currentUser/usr/local/lib/postgresql/login_hook.so
ls /storage/Users/currentUser/usr/local/share/postgresql/extension/login_hook*
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| postgresql-login_hook-1.5-ohos-aarch64.tar.gz | 58KB | 主预编译包 |
| postgresql-login_hook-1.5-ohos-aarch64-debug.tar.gz | 21KB | 调试符号包 |
| 0001-login_hook.c.patch | 1KB | PostgreSQL 17 API 适配补丁 |

## 注意事项

- 此扩展依赖 PostgreSQL 17，需要先安装 PostgreSQL
- PostgreSQL 17 中 `IsBackgroundWorker` 已被替换为 `AmBackgroundWorkerProcess()`
- 需要确保系统有 GNU install（ginstall）支持多文件安装
---

**编译结束**: 2026-06-02 13:00
**最终状态**: published
