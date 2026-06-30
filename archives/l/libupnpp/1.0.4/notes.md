# libupnpp 1.0.4 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-12
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 初始化编译环境
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build libupnpp 1.0.4 --url=https://www.lesbonscomptes.com/upmpdcli/downloads/libupnpp-1.0.4.tar.gz
   ```

2. 安装依赖（libnpupnp 6.3.0）
   ```bash
   # libnpupnp 不在预编译包列表中，需要手动编译
   export CC=/storage/Users/currentUser/usr/local/bin/clang
   export CXX=/storage/Users/currentUser/usr/local/bin/clang++
   export AR=/storage/Users/currentUser/usr/local/bin/llvm-ar
   export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig

   cd /storage/Users/currentUser/builds/libnpupnp-6.3.0.work
   meson setup builddir --prefix=$DEFAULT_PREFIX
   cd builddir && ninja && ninja install
   ```

3. 编译 libupnpp
   ```bash
   export CC=/storage/Users/currentUser/usr/local/bin/clang
   export CXX=/storage/Users/currentUser/usr/local/bin/clang++
   export AR=/storage/Users/currentUser/usr/local/bin/llvm-ar
   export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig

   cd /storage/Users/currentUser/builds/libupnpp-1.0.4.work
   meson setup builddir --prefix=$DEFAULT_PREFIX
   cd builddir && ninja
   DESTDIR=$TEST_PREFIX ninja install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 无法找到 C++ 编译器 | PATH 环境变量缺少 clang++ 路径 | 设置 CC/CXX 为完整路径 |
| 2 | meson 无法找到 ar（静态库工具） | 同上 | 设置 AR 为完整路径 |
| 3 | 缺少依赖 libnpupnp | 预编译包列表中无 libnpupnp | 手动编译 libnpupnp 6.3.0 |

## 源码修改

无补丁，纯配置环境变量编译。

## 依赖版本

- libnpupnp: 6.3.0（手动编译）
- libcurl: 8.19.0（已安装）
- libmicrohttpd: 0.9.77（libnpupnp 子项目，自动下载）

## 验证结果

```bash
# 检查安装产物
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/lib/
# libupnpp.so -> libupnpp.so.17
# libupnpp.so.1.0.4 (11598336 bytes)
# libupnpp.so.17 -> libupnpp.so.1.0.4

# 验证 pkg-config
pkg-config --modversion libupnpp
# 未测试（需要先安装到系统）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libupnpp.so.1.0.4 | 11MB | 共享库 |

## 注意事项

1. Meson 构建系统需要完整路径设置编译器环境变量（CC、CXX、AR）
2. libnpupnp 是 libupnpp 的必需依赖，但预编译包列表中缺失，需要手动编译
3. DESTDIR 安装模式：`DESTDIR=$TEST_PREFIX ninja install`

---
**编译结束**: 2026-06-12 17:35
**最终状态**: built（手动编译成功，档案信息待完善）
---

**编译结束**: 2026-06-15 11:31
**最终状态**: built
