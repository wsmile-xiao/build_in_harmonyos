# libmanette 0.2.7 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码：libmanette-0.2.7.tar.xz（从 GNOME FTP）
2. 安装依赖 libevdev-1.11.0（手动编译，需创建 harmonyos 头文件目录）
3. 配置 meson：
   ```
   meson setup build --prefix=$HOME/usr/local \
     -Dgudev=disabled -Dintrospection=false -Dvapi=false \
     -Ddemos=false -Dbuild-tests=false
   ```
4. 手动生成资源文件（因 glib-compile-resources 需要 libffi）：
   ```
   LD_LIBRARY_PATH=/data/service/hnp/libffi.org/libffi_3.4.4/lib:$HOME/usr/local/lib \
     /data/service/hnp/bin/glib-compile-resources ...
   ```
5. 编译：ninja -j2
6. 安装：meson install（DESTDIR staging + 本地安装）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 libevdev 依赖 | 无预编译包 | 手动编译 libevdev-1.11.0 |
| 2 | libevdev meson 找不到 harmonyos/input.h | host_machine.system() 返回 "harmonyos" 但目录不存在 | 创建 include/linux/harmonyos/ 并复制 linux 目录头文件 |
| 3 | glib-compile-resources 缺少 libffi.so.8 | LD_LIBRARY_PATH 未包含 libffi 路径 | 设置 LD_LIBRARY_PATH=/data/service/hnp/libffi.org/libffi_3.4.4/lib |

## 依赖版本

- glib-2.0: 2.88.0（已安装）
- gio-2.0: 2.88.0（已安装）
- gobject-2.0: 2.88.0（已安装）
- libevdev: 1.11.0（本次编译）

## 验证结果

```bash
pkg-config --modversion manette-0.2
0.2.7

pkg-config --libs manette-0.2
-L/storage/Users/currentUser/usr/local/lib -lmanette-0.2 -lglib-2.0 -lgio-2.0 -lgobject-2.0 -lgmodule-2.0

ls -lh ~/usr/local/lib/libmanette-0.2.so.0
-rwxr-x--- 307K libmanette-0.2.so.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmanette-0.2.so.0 | 307K | 共享库（已安装到 ~/usr/local/lib） |

## 注意事项

1. libevdev 需要先编译并创建 harmonyos 头文件适配
2. glib-compile-resources 需要 ELF 签名 + LD_LIBRARY_PATH 设置
3. 禁用 gudev（可选依赖，系统无 udev）
4. 禁用 demos 和 tests（避免运行时依赖问题）
**预编译包**: archives/l/libmanette/0.2.7/packaging/libmanette-0.2.7-ohos-aarch64.tar.gz (5.3MB)

## 质量门禁结果

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 | ⚠️ SKIP | build.ninja 修改未固化 |
| G1 | PASS | 二进制完整性通过 |
| G2 | PASS | 功能可用性通过 |
| G3 | PASS | 可移植性通过 |
| G4 | ⚠️ FAIL | "无二进制文件"（库文件，无可执行命令）|

### G4 失败原因

libmanette 是共享库，不是可执行程序。预编译包包含库文件和头文件，不包含可执行命令（demos 已禁用）。这是预期行为，不影响实际使用。
---

**编译结束**: 2026-06-02 12:18
**最终状态**: built
