# ksh93 1.0.10 鸿蒙适配笔记

## 环境信息
- 操作系统：HarmonyOS 6.0（aarch64）
- 编译器：Clang 15.0.4
- 构建系统：AT&T AST `bin/package`

## 依赖
- libc（标准 C 库）

## 构建步骤
1. 克隆上游源码：`git clone https://github.com/ksh93/ksh.git`
2. 切换到标签：`git checkout tags/v1.0.10`
3. 设置 `AST_NO_DYLIB=y`（跳过动态库构建，只编译静态版本）
4. 执行 `bin/package quiet make CCFLAGS="-O2 -fPIC"`
5. 构建输出位于 `arch/<hosttype>/bin/` 目录

## 平台限制
### HMDFS 拒绝 mkfifo(2)
- `bin/package make` 在默认（非 quiet）模式下会创建 `make.out.fifo`，导致 `mkfifo: Operation not permitted` 而构建失败。
- **解决方案**：改用 `bin/package quiet make`，该模式跳过 FIFO 创建，直接重定向输出到 `make.out` 文件。

### HarmonyOS 禁止第三方应用创建符号链接
- AST 构建系统在链接动态库（`libast.so`）后会创建 `libast.so.6`、`libast.so` 等符号链接。
- HarmonyOS 安全策略禁止第三方应用调用 `symlink()`，返回 `EACCES`（错误码 13900012），且官方确认无替代方案。
- **解决方案**：设置 `AST_NO_DYLIB=y`，跳过动态库构建，只编译静态链接的 ksh。

## 测试
- 上游测试：`bin/package quiet test`
- 消费者测试：验证 `ksh` 可执行文件可正常运行

## 相关问题
- E074: make -j 并行构建失败（FIFO 禁止）
- E075: 符号链接创建失败（HarmonyOS symlink 限制）
