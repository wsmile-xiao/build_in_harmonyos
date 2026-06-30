# rhash 1.4.6 适配笔记

## 编译环境
- 构建系统: makefile（基于 configure 脚本）
- 编译日期: 2026-06-11
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

**Phase 1: 环境准备**
1. 手动下载源码（网络受限，SSL证书验证失败）
   ```bash
   curl -k -L -o rhash-1.4.6.tar.gz https://github.com/rhash/RHash/archive/refs/tags/v1.4.6.tar.gz
   ```
2. 初始化编译环境（ohc-run.py init-build --no-download）
3. 解压源码到 `/storage/Users/currentUser/builds/rhash-1.4.6.work`

**Phase 2: 编译**
```bash
cd /storage/Users/currentUser/builds/rhash-1.4.6.work
./configure --prefix=/storage/Users/currentUser/usr/local \
  --enable-static \
  --disable-lib-shared \
  --disable-gettext
make -j$(nproc)
```

**Phase 3: 安装（DESTDIR 模式）**
- make install 失败（install 命令不存在），手动安装：
  ```bash
  mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
  mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/lib
  cp -f rhash $TEST_PREFIX/$DEFAULT_PREFIX/bin/
  cp -f librhash/librhash.a $TEST_PREFIX/$DEFAULT_PREFIX/lib/
  cp -f dist/rhash.1 $TEST_PREFIX/$DEFAULT_PREFIX/share/man/man1/
  ```

**Phase 4: 测试验证**
```bash
make test test-lib
# 输出: 25 tests passed, librhash "All sums are working properly!"
```

**Phase 5: 打包与归档**
- verify-build G1-G4 全部通过
- package: rhash-1.4.6-ohos-aarch64.tar.gz (861KB)
- finish: built 状态

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | Python urllib 无法验证 GitHub SSL 证书 | 使用 curl -k 手动下载源码包 |
| 2 | install 命令不存在 | 鸿蒙系统缺少 GNU install 命令 | 手动创建目录并复制文件（mkdir + cp） |
| 3 | 共享库软链接失败 | HMDFS 文件系统不支持 ln -sf 覆盖操作 | 静态编译：--enable-static --disable-lib-shared |
| 4 | gettext 编译错误 | 缺少头文件导致 gettext() 未声明 | 禁用国际化：--disable-gettext |

## 源码修改

无补丁。源码无需修改，仅通过 configure 参数适配平台。

## 依赖版本

无外部依赖。RHash 是自包含的哈希计算工具。

## 验证结果

```bash
# 版本验证
/storage/Users/currentUser/usr/local/bin/rhash --version
RHash v1.4.6

# 测试套件
make test test-lib
# 25/25 tests passed
# librhash: All sums are working properly!

# BLAKE3 新功能验证（v1.4.6 新增）
/storage/Users/currentUser/usr/local/bin/rhash --blake3 --sha256 /etc/passwd
/etc/passwd fc0988c63b081489bfaa1e40e96c0c3299b8eff275fce34867adf7e2a12d362f 309f462b6dea0afda2ec769f0a9113852379e4efc8e06a304b1ee1ce2f4dad58

# 支持的哈希算法
/storage/Users/currentUser/usr/local/bin/rhash --help | grep -E "(blake3|sha256|sha512|crc32)"
      --blake3     Calculate BLAKE3 message digest.
  -H, --sha1       Calculate SHA1 message digest.
      --sha224, --sha256, --sha384, --sha512 Calculate SHA2 message digest.
      --crc32c     Calculate CRC32C checksum.
  -M, --md5        Calculate MD5 message digest.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rhash-1.4.6-ohos-aarch64.tar.gz | 861KB | 生产环境预编译包 |
| rhash-1.4.6-ohos-aarch64-debug.tar.gz | 752KB | 调试符号包（含调试信息） |
| librhash.a | 644KB | 静态库（供其他软件链接） |
| rhash.1 | 8KB | man 手册页 |

## 注意事项

1. **静态编译是必须的**：HMDFS 文件系统不支持动态库软链接，必须使用 `--enable-static --disable-lib-shared`
2. **gettext 需禁用**：编译时会因 gettext() 未声明而失败，使用 `--disable-gettext`
3. **手动安装**：鸿蒙系统缺少 GNU install 品令，make install 会失败，需手动 mkdir + cp
4. **BLAKE3 新增**：v1.4.6 新增 BLAKE3 支持，是唯一支持此算法的通用哈希工具
5. **30+ 算法支持**：支持 SHA-1/256/512、SHA-3、BLAKE2b/2s/3、CRC32/CRC32C、MD4/MD5、GOST、RIPEMD、TTH 等 30+ 种算法

## v1.4.6 新功能亮点

- ✅ **BLAKE3 哈希算法**：新增支持，性能优于 BLAKE2b
- ✅ SHA1/SHA256 性能优化：使用 Intel SHA CPU 扩展硬件加速
- ✅ 文件读取性能改进：优化大文件处理
- ✅ GCC 7/15 编译兼容性：修复新版本 GCC 编译问题
---
**编译结束**: 2026-06-11 14:30
**最终状态**: built
**质量门禁**: G1-G4 PASS
---

**编译结束**: 2026-06-11 14:33
**最终状态**: built
