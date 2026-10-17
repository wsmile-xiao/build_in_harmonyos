# gnuplot 6.0.3 适配笔记

## 编译信息
- 日期: 2026-07-23
- 构建系统: autotools (autoconf)
- 编译器: clang 15.0.4
- 编译选项: -O2 -fPIC

## 配置选项
```
./configure --prefix=/storage/Users/currentUser/usr/local \
  --with-readline=builtin \
  --without-gd \
  --without-cairo \
  --without-lua \
  --without-qt
```
注意: `--with-wx-config=no` 未被识别（configure WARNING），不影响结果。

## 遇到的问题

### E011: HMDFS umask 问题
- **问题**: configure 脚本第 17884/17889 行 `umask 077` 在 HMDFS 文件系统上导致临时目录创建失败
- **修复**: 通过 Conan 配方的 apply_conandata_patches 自动应用补丁
- **补丁**: patches/0001-configure.patch
- **参考**: 5.4.10 版本同样问题

### make check 部分失败
- **原因**: 缺少图形终端（X11/cairo/pango），gnuplot 输出 "unknown terminal" 警告
- **影响**: 不阻塞，属于预期行为（零依赖编译）
- **详情**: pm3d.dem 中 "cannot write temporary file" 因 /tmp 只读

## 验证结果
- `gnuplot --version` 输出: `gnuplot 6.0 patchlevel 3`
- 二进制大小: 1460736 bytes
- 产物: bin/gnuplot (可执行文件)

## 零依赖说明
gnuplot 的所有终端库都是可选的，configure 检测不到就自动跳过：
- readline: 使用 builtin (内置最小实现)
- gd/cairo/pango: 未检测到，跳过
- lua: 未检测到，跳过
- Qt: 未检测到，跳过
- wxwidgets: 未检测到，跳过
---

**编译结束**: 2026-07-23 20:32
**最终状态**: published
