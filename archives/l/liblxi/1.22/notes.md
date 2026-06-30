# liblxi 1.22 适配笔记

## 编译环境
- 构建系统: meson (v1.11.1, pip安装)
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 (aarch64)
- ninja: v1.13.1
- 状态: published
- 无源码补丁

## 编译步骤

1. **下载源码**: GitHub HTTPS 直连超时，使用 ghfast.top CDN代理下载 v1.22.tar.gz (68777 bytes)
2. **安装依赖**:
   - `curl install.sh | sh -s -- libxml2 2.15.3` (预编译包, 4.6MB)
   - `curl install.sh | sh -s -- libtirpc 1.3.3` (预编译包, 2.1MB)
3. **安装meson**: `python3 -m pip install meson` → v1.11.1 (平台无预装)
4. **meson setup**:
   ```bash
   export LD_LIBRARY_PATH=...SDK llvm/lib:~/usr/local/lib:...
   export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:~/usr/local/share/pkgconfig
   meson setup builddir --prefix=$DEFAULT_PREFIX
   ```
   - 发现 libxml-2.0 YES, libtirpc YES, avahi-client NO
   - avahi-client 不可用 → 不编译 avahi.c, mdns discovery 禁用
5. **ninja -C builddir**: 编译成功, 4 warnings (非致命)
6. **DESTDIR staging 安装**:
   ```bash
   DESTDIR=$TEST_PREFIX ninja -C builddir install
   ```
   - 安装产物: liblxi.so.1.0.0, lxi.h, 7个man pages, liblxi.pc
7. **功能验证测试**: 编写C测试程序, 调用全部7个API函数, 全部PASS (详见 test-report.md)
8. **本地安装**: `ninja -C builddir install` (不带DESTDIR, 安装到~/usr/local)
9. **ELF签名**: `ohc-run.py sign-elf ~/usr/local/lib/liblxi.so.1.0.0` (运行时加载需要)
10. **打包**: `ohc-run.py package liblxi 1.22` → liblxi-1.22-ohos-aarch64.tar.gz (1.5MB)
11. **finish**: `ohc-run.py finish liblxi 1.22 published` → status=published, G0-G4 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识图谱引用 |
|---|------|------|----------|-------------|
| 1 | GitHub HTTPS连接超时 (curl exit 28) | 网络限制, HTTPS 443端口被封 | 使用 ghfast.top CDN代理下载 tarball | — |
| 2 | meson 未安装 (command not found) | 平台无预装meson构建工具 | `python3 -m pip install meson` (v1.11.1) | — |
| 3 | lld链接器启动失败 — libxml2.so.16符号冲突 | LD_LIBRARY_PATH中~/usr/local/lib优先于SDK llvm/lib, lld加载了不兼容版本的libxml2 (用户2.15.3 vs SDK 2.14.0) | 调整LD_LIBRARY_PATH顺序: SDK llvm/lib放在~/usr/local/lib之前 | **E080** |
| 4 | avahi-client不可用 | 平台无avahi预编译包 | meson required:false, 自动跳过, mdns discovery禁用 | platform |
| 5 | pthread_cancel未声明 (vxi11.c) | musl不实现pthread_cancel | 仅编译警告, 不影响链接; 运行时如触发会失败 | **E051** |
| 6 | 共享库运行时加载失败 (Error loading liblxi.so.1) | 未ELF签名的库不可运行时加载 | `ohc-run.py sign-elf` 签名后正常加载 | — |

## 源码修改
无。源码无需任何修改即可完成编译（仅4条编译警告, 均非致命）。

## 依赖版本

| 依赖 | 版本 | 来源 | 用途 |
|------|------|------|------|
| libxml2 | 2.15.3 | cmd-pkgs预编译包 | VXI-11 XML解析 |
| libtirpc | 1.3.2 (pkg-config) / 1.3.3 (包版本) | cmd-pkgs预编译包 | RPC通信协议 |
| threads | 系统提供 | 系统libc | 多线程支持 |

## 真实验证结果

### 功能测试 (7项全部PASS)
| # | 测试 | 函数 | 返回值 | 结果 |
|---|------|------|--------|------|
| 1 | 初始化 | lxi_init() | 0 | ✅ PASS |
| 2 | 设备发现 | lxi_discover() | 0 | ✅ PASS |
| 3 | 连接无效地址 | lxi_connect() | -1 | ✅ PASS |
| 4 | 发送无效句柄 | lxi_send() | -1 | ✅ PASS |
| 5 | 接收无效句柄 | lxi_receive() | -1 | ✅ PASS |
| 6 | 断开无效句柄 | lxi_disconnect() | 0 | ✅ PASS |
| 7 | 符号完整性 | 全部API | — | ✅ PASS |

### pkg-config验证
```
$ pkg-config --modversion liblxi → 1.22 ✅
$ pkg-config --libs liblxi → -L~/usr/local/lib -llxi ✅
$ pkg-config --cflags liblxi → -I~/usr/local/include ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| liblxi.so.1.0.0 | 39KB (未strip) / 38KB (strip后) | 共享库本体 |
| liblxi.so → liblxi.so.1 → liblxi.so.1.0.0 | 符号链接 | 版本链接链 |
| lxi.h | 2.7KB | 公共头文件 |
| liblxi.pc | — | pkg-config 描述文件 |
| lxi_connect.3 等 | 7个 | man 手册页面 |
| liblxi-1.22-ohos-aarch64.tar.gz | 1.5MB | 预编译包(含strip+签名+RPATH) |
| liblxi-1.22-ohos-aarch64-debug.tar.gz | 296KB | 调试符号包 |

## 注意事项

1. **LD_LIBRARY_PATH顺序**: 必须将SDK llvm/lib放在~/usr/local/lib之前, 否则lld因libxml2版本冲突无法启动 (E080)
2. **avahi-client缺失**: 导致mDNS发现(DISCOVER_MDNS)功能不可用, VXI-11发现(DISCOVER_VXI11)仍可用
3. **pthread_cancel**: musl不实现, vxi11.c中仅编译警告; 运行时如触发线程取消将失败
4. **meson需pip安装**: 平台无预装meson构建工具
5. **ELF签名**: 共享库必须签名才能在OpenHarmony运行时加载
6. **无测试套**: 项目未定义meson test, 使用自定义C程序验证功能

---
**编译结束**: 2026-06-12
**最终状态**: published
---

**编译结束**: 2026-06-12 16:41
**最终状态**: published
