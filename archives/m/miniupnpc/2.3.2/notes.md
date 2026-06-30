# miniupnpc 2.3.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-25
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. **环境设置**
   ```bash
   export LD_LIBRARY_PATH=/data/service/hnp/python.org/python_3.12/lib:$HOME/usr/local/lib:$LD_LIBRARY_PATH
   export TMPDIR=/data/storage/el2/base/cache
   export DEFAULT_PREFIX=/storage/Users/currentUser/usr/local
   export TEST_PREFIX=/data/storage/el2/base/cache/test-install-miniupnpc-2.3.2
   ```

2. **源码下载**
   - URL: https://github.com/miniupnp/miniupnp/releases/download/miniupnpc_2_3_2/miniupnpc-2.3.2.tar.gz
   - 使用 Python urllib 直接下载（SSL 证书问题导致 wget 失败）

3. **编译**
   ```bash
   cd /data/storage/el2/base/cache/builds/miniupnpc-2.3.2.work
   make PREFIX=$DEFAULT_PREFIX -j2
   ```

4. **安装（DESTDIR 模式）**
   ```bash
   make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
   ```

5. **测试**
   ```bash
   make check
   ```
   - 所有测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | GitHub HTTPS 证书问题 | 使用 Python ssl._create_unverified_context 绕过 |
| 2 | ln -fs 失败 | HMDFS 不支持 ln -sf 覆盖现有文件 | 改为 rm -f && ln -s 分两步执行 |

## 源码修改

### 0001-Makefile.patch
- 文件: Makefile
- 类型: platform_fix
- 平台: HMDFS
- 说明: 修复 ln -fs 为 rm -f + ln -s，解决 HMDFS 不支持强制覆盖符号链接的问题

修改内容：
```diff
-	ln -fs $(SONAME) $(DESTDIR)$(INSTALLDIRLIB)/$(notdir $(SHAREDLIBRARY))
+	rm -f $(DESTDIR)$(INSTALLDIRLIB)/$(notdir $(SHAREDLIBRARY))
+	ln -s $(SONAME) $(DESTDIR)$(INSTALLDIRLIB)/$(notdir $(SHAREDLIBRARY))
```

## 依赖版本

无外部依赖，纯 C 库。

## 验证结果

### 测试执行
```bash
make check
```

测试结果：
- minixml validation test: PASS
- miniwget validation test: PASS
- upnpreplyparse validation test: PASS
- portlistingparse validation test: PASS
- igd desc parse validation test: PASS
- addr_is_reserved() validation test: PASS

### 安装产物
```bash
ls -la $TEST_PREFIX/storage/Users/currentUser/usr/local/
```
- bin/upnpc (39296 bytes)
- bin/upnp-listdevices (22912 bytes)
- bin/external-ip (161 bytes, shell script)
- lib/libminiupnpc.a (82994 bytes, static library)
- lib/libminiupnpc.so -> libminiupnpc.so.20 (symbolic link)
- lib/libminiupnpc.so.20 (63872 bytes, shared library)
- lib/pkgconfig/miniupnpc.pc
- include/miniupnpc/*.h (10 header files)

## 交付物

预编译包尚未制作（质量门禁 G4 未完全通过）

| 文件 | 大小 | 说明 |
|------|------|------|
| libminiupnpc.a | 82KB | 静态库 |
| libminiupnpc.so.20 | 63KB | 动态库 |
| upnpc | 39KB | UPnP 命令行客户端 |

## 注意事项

1. HMDFS 不支持 `ln -sf` 强制覆盖，需要先 `rm -f` 再 `ln -s`
2. 源码下载需要处理 SSL 证书问题
3. 无 configure 步骤，直接使用 Makefile 构建
---

**编译结束**: 2026-05-25 20:52
**最终状态**: built
---

**编译结束**: 2026-05-26 10:56
**最终状态**: built
