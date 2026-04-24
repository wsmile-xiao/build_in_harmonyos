# tinyssh 20260401 — OpenHarmony 编译记录

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | tinyssh |
| 版本 | 20260401 |
| 状态 | ⚠️ partial |
| 构建系统 | makefile (configure 脚本) |
| 目标平台 | ohos-aarch64 |
| 编译日期 | 2026-04-24 |
| 源码地址 | https://api.github.com/repos/janmojzis/tinyssh/tarball/20260401 |

## 编译指导

### 环境准备
```bash
# 设置 OpenHarmony 交叉编译工具链
export CC=aarch64-linux-ohos-clang
export CFLAGS="-O2 -fPIC"
export LDFLAGS="-static"
```

### 构建步骤
```bash
# 1. 解压源码
tar xzf tinyssh-20260401.tar.gz
cd tinyssh-20260401

# 2. 配置（使用默认配置即可）
./configure --prefix=$TEST_PREFIX

# 3. 编译
make -j$(nproc)

# 4. 安装到测试前缀
make install DESTDIR=$TEST_PREFIX

# 5. Staging 验证
ls -lh $TEST_PREFIX/sbin/tinysshd
```

### 编译参数
- **Configure 参数**: 无额外参数，使用默认配置
- **编译选项**: 标准 make 构建
- **安装前缀**: $TEST_PREFIX (测试环境)

## 补丁清单

本次编译 **未应用任何补丁**。

| 补丁文件 | 目的 | 状态 |
|---------|------|------|
| - | 无补丁需求 | - |

**说明**: tinyssh 源码兼容性好，OpenHarmony 平台编译无需修改源码。

## 已知限制

### 平台相关限制
1. **HarmonyOS 安全弹窗**
   - 首次运行二进制文件时需手动确认授权
   - 解决方案：使用 `install.sh` 脚本自动触发确认

2. **动态链接依赖**
   - 依赖系统 C 库（libc）
   - 需确保目标系统 glibc 版本兼容

### 功能限制
1. **加密算法支持**
   - 仅支持现代加密算法：Ed25519、Curve25519、Chacha20-Poly1305
   - **不兼容**旧版 SSH 客户端（不支持 RSA、AES 等传统算法）

2. **认证方式**
   - 默认仅支持公钥认证
   - 密码认证需额外配置

## 功能验证

### 安装后检查
```bash
# 检查二进制文件是否存在
ls -lh ~/usr/local/sbin/tinysshd
# 预期输出: -rwxr-x--- 1 ... 130K ... tinysshd

# 检查符号链接
ls -l ~/usr/local/sbin/tinyssh*
# 预期输出:
# tinysshd
# tinysshd-makekey -> tinysshd
# tinysshd-printkey -> tinysshd
# tinysshnoneauthd -> tinysshd
```

### 基础功能测试
```bash
# 1. 生成密钥对
tinysshd-makekey /tmp/tinyssh-keys
ls /tmp/tinyssh-keys
# 预期: 应生成 Ed25519 密钥文件

# 2. 查看帮助
tinysshd --help 2>&1 || tinysshd 2>&1 | head -20
# 预期: 显示使用说明

# 3. 启动服务（需要 root 权限）
sudo tinysshd /tmp/tinyssh-keys
# 预期: 服务启动成功，监听 22 端口
```

### 连接测试
```bash
# 使用 SSH 客户端连接（需要密钥认证）
ssh -i ~/.ssh/id_ed25519 -p 22 user@localhost

# 验证加密套件
ssh -vv -p 22 user@localhost 2>&1 | grep "kex\|cipher"
# 预期: 显示 Curve25519 和 Chacha20-Poly1305
```

## 交付物清单

| 文件名 | 大小 | 说明 |
|--------|------|------|
| tinyssh-20260401-ohos-aarch64.tar.gz | 146KB | 主预编译包 |
| tinyssh-20260401-ohos-aarch64-debug.tar.gz | 49KB | 调试符号包 |
| install-tinyssh-20260401.sh | 1.1KB | 自动安装脚本 |

## 编译结果总结

- ✅ 编译成功：二进制文件生成正常
- ✅ 安装成功：文件已安装到测试前缀
- ✅ 质量门禁：PASS
- ⚠️ 状态：partial（部分功能未完全验证）
- ℹ️ 补丁数：0

## 相关文档

- [质量报告](./reports/quality-report.md)
- [测试报告](./reports/test-report.md)
- [流程反馈](./reports/skill-feedback.md)
