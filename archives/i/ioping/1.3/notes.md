# 适配笔记 — ioping 1.3 (磁盘 I/O 延迟测量工具)

## 2026-07-27 适配

### 库信息
- **软件**: ioping (Konstantin Khlebnikov)
- **版本**: 1.3
- **构建系统**: Makefile
- **许可证**: GPL-3.0-only
- **上游**: https://github.com/koct9i/ioping
- **功能**: 轻量级磁盘 I/O 延迟测量工具，类似 ping 测量网络延迟

### 构建说明
- `make` 直接编译 ioping.c 为单一二进制
- 安装：`make install PREFIX=/usr DESTDIR=<pkgdir>`
- Makefile 已打补丁，使 CC 可从环境变量覆盖（`?=`）

### 依赖
- **运行时**: 零依赖（仅系统 libm、librt）
- **构建时**: clang + make

### 适配变更
- `patches/0001-Makefile.patch`：CC = → CC ?=，使交叉编译器通过环境变量生效
- `conanfile.py build()`：使用 `cross_building` 守卫，native 编译时运行上游 `make test`
- `test_package/conanfile.py`：交叉编译时通过 `_check_binary_exists()` 验证产物存在

### 上游测试
- 上游 `make test` 运行 3 组磁盘 I/O 延迟测试
- native 编译时在 `build()` 中自动执行
- 交叉编译时跳过（无法在构建机运行 OHOS 二进制）

### test_package 测试
- `test_ioping.c`：验证 `ioping --version`、`--help`、产物完整性
- `_check_binary_exists()`：交叉编译时验证二进制安装正确

### 本地验证记录
| 检查项 | 结果 |
|--------|------|
| conan export | ✅ 成功 |
| SHA256 | ✅ |
| test_package | ✅ 二进制存在、--version/--help 输出正常 |
