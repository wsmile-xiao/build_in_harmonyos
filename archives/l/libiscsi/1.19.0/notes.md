# libiscsi 1.19.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **初始化**: `ohc-run.py init-build libiscsi 1.19.0 --url=https://github.com/sahlberg/libiscsi/archive/refs/tags/1.19.0.tar.gz`
2. **生成构建脚本**: `./autogen.sh`
3. **应用平台修复**: `./patches/apply-ohos-fixes.sh` (E011 umask 修复)
4. **配置**: `./configure --prefix=/storage/Users/currentUser/usr/local`
5. **编译**: `make -j1`
6. **安装**: `make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libiscsi-1.19.0`
7. **本地验证**: `make install` (安装到 ~/usr/local)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识条目 |
|---|------|------|----------|---------|
| 1 | configure 创建临时目录 Permission denied | HMDFS umask 077 限制 | 修改 configure 中的 umask 077 为 umask 022 | E011 |
| 2 | socket.c 编译失败 -Werror | 函数声明缺少 void 参数 | 修改为 `void iscsi_decrement_iface_rr(void)` | 已生成补丁 |

## 源码修改

### 文件：lib/socket.c
```diff
-void iscsi_decrement_iface_rr() {
+void iscsi_decrement_iface_rr(void) {
```

补丁文件：`0001-fix-function-declaration.patch`

## 依赖版本

无外部依赖，仅需要标准 C 库和构建工具（autoconf, automake, libtool）。

## 验证结果

```bash
# 二进制验证
iscsi-ls --help
# 输出: Usage: iscsi-ls [OPTION...] <iscsi-url>

# 库文件验证
ls ~/usr/local/lib/libiscsi.so
# 输出: libiscsi.so -> libiscsi.so.9.0.0

# pkg-config 验证
pkg-config --modversion libiscsi
# 输出: 1.19.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libiscsi-1.19.0-ohos-aarch64.tar.gz | 10KB | 预编译包（手动打包） |
| bin/iscsi-* | 35-58KB | 工具二进制 |
| lib/libiscsi.so.9.0.0 | 动态库 | |
| lib/libiscsi.a | 静态库 | |

## 注意事项

1. **E011 umask 修复必须在 autogen.sh 之后应用**：configure 是由 autogen.sh 生成的，每次重新运行 autogen.sh 后都需要应用 apply-ohos-fixes.sh
2. **测试套件不可用**：configure 检测不到 libcunit，测试套件不会构建（不影响核心功能）
3. **不生成构建产物补丁**：遵循 R6 规则，只保留源码修改的补丁
**验证标记**: 二进制可执行，库文件完整
---

**编译结束**: 2026-05-25 18:02
**最终状态**: built
