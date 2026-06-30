# tofrodos 1.8.3 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, not autotools)
- 编译日期: 2026-06-09
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. **初始化**: 使用阿里云 Ubuntu 镜像下载源码包 `tofrodos_1.8.3+ds.orig.tar.xz`
2. **编译**: 使用 `make CC=clang` 编译（原 Makefile 默认使用 gcc，需指定 clang）
3. **手动安装**: 由于 Makefile 不支持 DESTDIR 模式，手动复制文件到 staging 目录
   - 复制 `fromdos` 到 `$TEST_PREFIX$DEFAULT_PREFIX/bin/`
   - 创建软链接 `todos -> fromdos`
   - 复制 `fromdos.1` 到 `$TEST_PREFIX$DEFAULT_PREFIX/share/man/man1/`
   - 创建软链接 `todos.1 -> fromdos.1`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 系统缺少根证书 | 使用阿里云镜像（国内可访问） |
| 2 | make 找不到 gcc | 系统只有 clang | 使用 `make CC=clang` |
| 3 | make install 不支持 DESTDIR | Makefile 是简单手工编写 | 手动复制文件到 staging 目录 |
| 4 | ln -sf 卡住 | HMDFS 文件系统 SELinux 限制 | 使用 `rm -f && ln -s` 替代 |

## 源码修改

无补丁，仅编译时指定 CC=clang。

## 依赖版本

- clang: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

```bash
# 二进制验证
/storage/Users/currentUser/test-install-tofrodos-1.8.3/storage/Users/currentUser/usr/local/bin/fromdos --version
# (tofrodos 无 --version 参数，通过执行测试验证)

# 文件完整性
ls -la /storage/Users/currentUser/test-install-tofrodos-1.8.3/storage/Users/currentUser/usr/local/bin/
# fromdos: 18048 bytes
# todos -> fromdos (symlink)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tofrodos-1.8.3-ohos-aarch64.tar.gz | 28695 bytes | 预编译包 |

## 注意事项

1. tofrodos 使用简单 Makefile，不是标准 autotools 项目
2. 需要指定 CC=clang 编译
3. DESTDIR 不生效，需要手动安装
4. HMDFS 上 ln -sf 会卡住，必须先 rm -f
---

**编译结束**: 2026-06-09 15:34
**最终状态**: built