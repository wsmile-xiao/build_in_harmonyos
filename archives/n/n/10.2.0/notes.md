# n 10.2.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-05
- 编译器: 无需编译器（纯 bash 脚本）
- 状态: built

## 编译步骤

n 是 Node.js 版本管理器，为纯 bash 脚本项目，无需编译步骤：

1. 下载源码: 从 GitHub 下载 v10.2.0 tarball
2. 解压: tar -xzf n-10.2.0.tar.gz
3. 安装: make install PREFIX=$TEST_PREFIX$DEFAULT_PREFIX
   - 使用 DESTDIR 模式：PREFIX=$TEST_PREFIX$DEFAULT_PREFIX
   - 例如: PREFIX=/data/storage/el2/base/cache/test-install-n-10.2.0/storage/Users/currentUser/usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 默认使用 /usr/local 无权限 | Makefile 中 PREFIX 默认为 /usr/local | 传入 PREFIX=$TEST_PREFIX$DEFAULT_PREFIX |
| 2 | Makefile 不支持 DESTDIR | 简单 Makefile 未实现 DESTDIR | 使用 PREFIX 组合路径模拟 DESTDIR |

## 源码修改

无补丁，无需修改源码。

## 依赖版本

无编译依赖。运行时依赖：
- bash (已在系统中安装)
- curl (用于下载 Node.js 版本)
- jq (可选，用于读取 package.json)

## 验证结果

```bash
$ file /data/storage/el2/base/cache/test-install-n-10.2.0/storage/Users/currentUser/usr/local/bin/n
/data/storage/el2/base/cache/test-install-n-10.2.0/storage/Users/currentUser/usr/local/bin/n: bash script

$ ls -la /data/storage/el2/base/cache/test-install-n-10.2.0/storage/Users/currentUser/usr/local/bin/n
-rwxrwxr-x 1 20020100 20020100 52436 2026-06-05 11:50 n
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| n | 52KB | bash 脚本，Node.js 版本管理器 |

## 注意事项

1. n 是纯 shell 脚本，无需 ELF 签名
2. 运行时需要 curl 工具用于下载 Node.js 版本
3. 建议安装到 /usr/local/bin 或 ~/usr/local/bin 以便 PATH 访问
---

**编译结束**: 2026-06-08 20:44
**最终状态**: built
