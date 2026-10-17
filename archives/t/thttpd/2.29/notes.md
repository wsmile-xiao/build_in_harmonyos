# thttpd 2.29 适配笔记

## 编译环境
- 构建系统: autotools (autoconf 2.13)
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 1. 更新 config.guess/config.sub（旧版不支持 OHOS 检测）
# 2. 运行 configure
./configure --prefix=$PREFIX
# 3. 编译
make -j1
# 4. 安装（需预先创建 man/man1, man/man8, www/cgi-bin 目录）
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法检测平台 | autoconf 2.13 太旧，不支持 HarmonyOS/OHOS | 替换 config.guess 为简单 stub 输出 aarch64-unknown-linux-gnu |
| 2 | config.sub 无法识别平台 | 同上 | 替换 config.sub 为简单处理器 |
| 3 | htpasswd.c: getpass 未定义 | OHOS 不提供 getpass() 函数 | 添加可移植 read_password() 辅助函数（POSIX stdio：fputs 提示 + fgets 读取 + strchr 去换行），检查 fgets 返回值处理 EOF，无平台宏（R8） |
| 4 | htpasswd.c: /tmp 路径只读 | OHOS /tmp 为只读文件系统 | 修改 temp_template 路径 |
| 5 | extras install: chgrp www 失败 | OHOS 无 www 用户组 | 在 Makefile.in 中使用 -chgrp 前缀使错误可忽略 |
| 6 | install: man/man1 目录不存在 | Makefile 未创建目标目录 | conanfile.py package() 中预创建所需目录 |
| 7 | Conan out-of-source build 失败 | autoconf 2.13 不支持 OOS 构建 | conanfile.py 中使用 cwd=self.source_folder |

## 源码修改

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001-config.guess.patch | config.guess | 替换为 OHOS/aarch64 平台检测 stub |
| 0002-config.sub.patch | config.sub | 替换为 OHOS/aarch64 平台处理 |
| 0003-extras-Makefile.in.patch | extras/Makefile.in | chgrp 命令改为非致命（-chgrp） |
| 0004-extras-htpasswd.c.patch | extras/htpasswd.c | 用可移植 read_password() 替代 getpass()（无平台宏）+ 修复 /tmp 路径 + 修复 fgets EOF 下溢 |

## 依赖版本

无外部依赖。thttpd 是自包含的 HTTP 服务器。

## 验证结果

```bash
$ thttpd -V
thttpd/2.29 23May2018
```

## 注意事项

- thttpd 使用非常老的 autoconf 2.13，不支持 out-of-source 构建
- 源码 URL 使用 http:// 而非 https://（acme.com SSL 与设备不兼容）
- 软件类型为 application（命令行工具），非 library
- commands.json 已创建（R38）
---

**编译结束**: 2026-08-23 00:37
**最终状态**: built
