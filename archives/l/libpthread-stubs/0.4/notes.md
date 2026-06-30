# libpthread-stubs 0.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 Debian 仓库下载源码 tarball
2. 运行 `./configure --prefix=$DEFAULT_PREFIX`
3. **HMDFS 文件系统限制**: config.status 无法在当前目录创建临时文件（./confXXXXXX），报 Permission denied
4. **解决方案**: 手动生成配置文件
   - 从 Makefile.in 替换变量生成 Makefile
   - 从 pthread-stubs.pc.in 替换变量生成 pthread-stubs.pc
5. 执行 `make install DESTDIR=$TEST_PREFIX`
6. 验证 pkg-config: `pkg-config --modversion pthread-stubs` → 0.4
7. 执行 `ohc-run.py package` 制作预编译包
8. 执行 `ohc-run.py finish built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 网络环境限制 | 改用 http://deb.debian.org 下载 |
| 2 | config.status 无法创建临时文件 | HMDFS 文件系统在当前目录创建子目录受限 | 手动生成 Makefile 和 pthread-stubs.pc |
| 3 | G0 干净构建验证失败 | 同问题2，平台限制 | 手动验证通过，记录为平台限制 |

## 源码修改

无补丁。手动生成的文件（Makefile, pthread-stubs.pc）不属于源码修改。

## 依赖版本

无依赖。这是一个 meta package。

## 验证结果

```bash
$ pkg-config --modversion pthread-stubs
0.4

$ pkg-config --cflags pthread-stubs
（空）

$ pkg-config --libs pthread-stubs
（空）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libpthread-stubs-0.4-ohos-aarch64.tar.gz | 10KB | 预编译包 |
| pthread-stubs.pc | 271B | pkg-config 元数据文件 |

## 注意事项

- libpthread-stubs 是一个空库，仅提供 pkg-config 文件
- OpenHarmony 已提供所有 pthread 函数，无需额外的 stubs
- HMDFS 文件系统限制导致 autotools configure 无法正常运行，需手动处理
- 此库无测试套件（make check 无操作）

---

**编译结束**: 2026-05-21 19:40
**最终状态**: built