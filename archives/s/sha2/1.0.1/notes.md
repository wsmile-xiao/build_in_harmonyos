# sha2 1.0.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：`ohc-run.py init-build sha2 1.0.1 --url=file://~/builds/sha2-1.0.1.tar.gz`
2. 编译源码：`make PREFIX=$DEFAULT_PREFIX`
3. 安装到 staging：`make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
4. 运行测试：`make test`（三种 SHA-2 算法全部通过）
5. 安装到本地：`make install PREFIX=$DEFAULT_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译时找不到 OpenSSL 头文件 | Makefile 使用硬编码路径 `/usr/local/include` | 修改 Makefile 使用 `PREFIX` 变量，传递 `PREFIX=$DEFAULT_PREFIX` |
| 2 | 链接时找不到 OpenSSL 库函数 | 使用了已弃用的 OpenSSL API | 移除 `OpenSSL_add_all_digests()` 和 `EVP_cleanup()`（OpenSSL 1.1.0+ 自动处理） |
| 3 | 运行时找不到共享库 | 缺少 RPATH | 修改 Makefile 添加 `-Wl,-rpath,$(PREFIX)/lib` |
| 4 | verify-build 报告无二进制文件 | 脚本在 packaging 目录查找 | 手动安装到 DEFAULT_PREFIX 后验证可用 |

## 源码修改

- **0001-Makefile.patch**: 添加 RPATH 支持（`-Wl,-rpath,$(PREFIX)/lib`）
- **0002-src-sha2.c.patch**: 移除已弃用的 OpenSSL 1.0 API（`OpenSSL_add_all_digests` 和 `EVP_cleanup`）

## 依赖版本

- openssl/1.1.1w（已安装）
- clang/15.0.4（编译器）

## 验证结果

```bash
# 编译测试
make test
./sha2 -a 256 Makefile
1e4ffb0cb5cf5775954afd5d3537aca1949707b0c3d83a088f72fd9cbf8ea32f  Makefile

./sha2 -a 384 Makefile
aa24b00a7d04c3f0aa726641941aa89583d07c76c31acae21eee7db65894ae1866b67f9565e70e9b3937fb79ffd1f574  Makefile

./sha2 -a 512 Makefile
43c8430cf4706f01551c316acd294597960317b6fc16f9af6f2a4f6b01c9a8801741f38f608cf00cfeb3ef8c1980182c2348102032ab35e4a244825aac41c281  Makefile

# 安装验证
~/usr/local/bin/sha2 -a 256 ~/usr/local/bin/sha2
1777898cb888bb0cd64efd7b7ee1fb3cd3861be5c990b81837447d5164713027  /storage/Users/currentUser/usr/local/bin/sha2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sha2 | 23KB | SHA-2 哈希工具二进制 |
| 0001-Makefile.patch | 1 文件 | RPATH 支持补丁 |
| 0002-src-sha2.c.patch | 1 文件 | OpenSSL 1.1.0+ API 适配补丁 |

## 注意事项

1. **OpenSSL 依赖**: sha2 依赖 libcrypto.so，运行时需要正确设置 LD_LIBRARY_PATH 或使用 RPATH
2. **OpenSSL 1.1.0+ API**: 移除旧版初始化/清理函数，OpenShell 自动处理
3. **Makefile 项目**: 无 configure 脚本，直接使用 make 编译

---

**编译结束**: 2026-06-11 18:07
**最终状态**: built
---

**编译结束**: 2026-06-11 18:09
**最终状态**: built
