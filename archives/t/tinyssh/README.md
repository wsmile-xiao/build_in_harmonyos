# tinyssh — OpenHarmony 预编译归档

## 软件简介

tinyssh 是一个小型、安全的 SSH 服务器实现，设计目标是简洁和安全。它使用现代加密算法（Ed25519、Curve25519、Chacha20-Poly1305），代码量小，易于审计，特别适合嵌入式系统和资源受限环境。

主要特性：
- 现代加密：Ed25519、Curve25519、Chacha20-Poly1305
- 小巧精简：代码量小，便于安全审计
- 无需外部依赖：不依赖 OpenSSL 或其他加密库
- 适合嵌入式：资源占用低，适合 OpenHarmony 等嵌入式平台

## 编译指导

### 构建系统
tinyssh 使用 Makefile 构建系统，通过 `./configure` 脚本进行配置。

### 标准编译命令
```bash
# 1. 配置
./configure --prefix=$TEST_PREFIX

# 2. 编译
make -j$(nproc)

# 3. 安装
make install DESTDIR=$TEST_PREFIX

# 4. 功能测试
make test  # 如果支持
```

### OpenHarmony 交叉编译
针对 OpenHarmony aarch64 平台的编译要点：
- 使用 OpenHarmony 工具链（clang/llvm）
- 设置正确的 CC、CFLAGS、LDFLAGS 环境变量
- 目标三重态：aarch64-linux-ohos

## 补丁清单

当前版本无补丁。如需添加补丁，请放置在版本级 `patches/` 目录中，并在此记录：

| 补丁文件 | 目的 | 状态 |
|---------|------|------|
| - | 暂无补丁 | - |

## 已知限制

### 平台相关
- **HarmonyOS 安全弹窗**：首次运行二进制文件时需手动确认授权
- **动态链接**：依赖系统 C 库，需确保目标系统兼容

### 功能限制
- **加密算法**：仅支持现代加密算法（Ed25519、Curve25519），不兼容旧版 SSH 客户端
- **认证方式**：默认仅支持公钥认证，密码认证需额外配置

## 功能验证

### 安装后验证
```bash
# 检查二进制文件
ls -lh ~/usr/local/sbin/tinysshd

# 查看帮助
tinysshd --help

# 生成密钥
tinysshd-makekey /path/to/keydir

# 启动服务（需要 root 权限）
tinysshd /path/to/keydir
```

### 连接测试
```bash
# 使用 SSH 客户端连接
ssh -p 22 user@localhost

# 验证加密套件
ssh -vv -p 22 user@localhost 2>&1 | grep "kex"
```

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 | 质量门禁 |
|------|------|---------|--------|---------|
| 20260401 | partial | 2026-04-24 | 0 | PASS |

## 相关资源

- 官方网站：https://tinyssh.org/
- 源码仓库：https://github.com/janmojzis/tinyssh
- 文档：https://tinyssh.org/docs/
