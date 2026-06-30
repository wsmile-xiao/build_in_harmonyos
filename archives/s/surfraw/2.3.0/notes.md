# surfraw 2.3.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-24
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载并解压 surfraw-2.3.0.tar.gz
2. 执行 `./configure --prefix=/storage/Users/currentUser/usr/local`
3. config.status 因 HMDFS umask 077 限制失败，修复后重新生成 Makefile
4. 执行 `make -j1`（无 C 编译，纯 shell/perl 脚本生成）
5. 执行 `make install DESTDIR=$TEST_PREFIX`（staging 安装）
6. 执行 `make check`（无测试用例，直接通过）
7. 打包为 `surfraw-2.3.0-ohos-aarch64.tar.gz`
8. 执行 `make install`（安装到 ~/usr/local）
9. 验证可执行文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 无法创建临时文件 `./confXXXXXX/subs1.awk: Permission denied` | autoconf 2.69 的 config.status 使用 `umask 077` 创建临时目录，HMDFS 上 umask 077 创建的目录不可写（chmod 也无法修复） | 将 config.status 中的 `umask 077` 改为 `umask 002` |
| 2 | surfraw-update-path、opensearch-discover、opensearch-genquery 脚本无法执行 `bad interpreter: /usr/bin/perl: No such file or directory` | 硬编码 shebang `#!/usr/bin/perl`，但本平台 perl 在 `~/usr/local/bin/perl`，且 `/usr/bin/` 只读无法创建符号链接 | 将 shebang 改为 `#!/usr/bin/env perl` |

## 源码修改

### 0001-config.status.patch
- 文件: config.status
- 修改: `umask 077` → `umask 002`（2 处）
- 原因: HMDFS 上 umask 077 创建的目录不可写

### 0002-opensearch-discover.patch
- 文件: opensearch-discover
- 修改: `#!/usr/bin/perl -w` → `#!/usr/bin/env perl`
- 原因: /usr/bin/perl 不存在，使用 env 查找

### 0003-opensearch-genquery.patch
- 文件: opensearch-genquery
- 修改: `#!/usr/bin/perl -w` → `#!/usr/bin/env perl`
- 原因: 同上

### 0004-surfraw-update-path.IN.patch
- 文件: surfraw-update-path.IN
- 修改: `#!/usr/bin/perl -w` → `#!/usr/bin/env perl`
- 原因: 同上

## 依赖版本

无外部依赖（纯 shell/perl 脚本项目，使用系统自带 gawk 和 perl）

## 验证结果

```bash
$ surfraw --version
# 显示版本 2.3.0 及用法

$ sr -version
# sr 别名正常工作（surfraw 符号链接）

$ surfraw-update-path --help
# 正常显示帮助信息

$ opensearch-genquery --help
# 正常显示帮助信息

$ make check
# 无测试用例，全部通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| surfraw-2.3.0-ohos-aarch64.tar.gz | 431KB | 预编译包 |

## 注意事项

1. surfraw 是纯脚本项目（shell + perl），无 C/C++ 编译
2. 主程序 `surfraw` 是 bash 脚本，使用配置时的 perl 路径（正确）
3. 辅助脚本 `surfraw-update-path`、`opensearch-discover`、`opensearch-genquery` 是 perl 脚本，原始 shebang 硬编码为 `/usr/bin/perl`
4. `/usr/bin/` 在 HMDFS 上为只读，无法创建 perl 符号链接
5. 安装了 100+ elvi（搜索引擎接口脚本）到 `~/usr/local/lib/surfraw/`
6. G0 干净构建验证因 Python subprocess 平台限制（patch 命令不支持 --input 参数）跳过，已手动验证补丁可应用
---

**编译结束**: 2026-06-24 15:10
**最终状态**: built
