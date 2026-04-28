# sshpass 1.10 — OpenHarmony 编译记录

## 基本信息
- 软件: sshpass (non-interactive SSH password authentication)
- 版本: 1.10
- 构建系统: autotools
- 目标: ohos-aarch64
- 状态: success
- 下载源: https://master.dl.sourceforge.net/project/sshpass/sshpass/1.10/sshpass-1.10.tar.gz

## 软件介绍
sshpass 是一个用于非交互式 SSH 密码认证的工具：
- 自动向 SSH 提供密码，无需手动输入
- 适用于自动化脚本和批处理任务
- 注意：使用密码认证存在安全风险，建议使用 SSH 密钥认证

## 编译指导

### configure 配置
```bash
./configure --prefix=$DEFAULT_PREFIX \
            --host=aarch64-unknown-linux-ohos
```

### 手动编译（绕过 Makefile 依赖问题）
```bash
# 由于 toybox mktemp 与 GNU mktemp 不兼容，可能需要手动编译
gcc -o sshpass sshpass.c -DHAVE_CONFIG_H
```

### 安装
```bash
cp sshpass $TEST_PREFIX/$DEFAULT_PREFIX/bin/
chmod +x $TEST_PREFIX/$DEFAULT_PREFIX/bin/sshpass
```

### 重要提示
- 需更新 config.guess 和 config.sub 以识别 HarmonyOS 平台
- toybox mktemp 与 GNU mktemp 不兼容，可能触发 Makefile 依赖问题
- 如遇 make 错误，可手动编译 sshpass.c

## 补丁清单

| 补丁文件 | 类型 | 说明 |
|---------|------|------|
| 0001-config.guess.patch | 平台适配 | 添加 HarmonyOS 平台识别支持 |
| 0002-config.sub.patch | 平台适配 | 添加 linux-ohos 内核识别到内核支持列表 |

## 已知限制
1. toybox mktemp 与 GNU mktemp 不兼容，可能影响 Makefile 生成
2. Makefile 依赖检查可能触发 autotools 重新生成规则
3. 建议使用手动编译方式绕过 Makefile 问题

## 功能验证

### 版本验证
```bash
sshpass -V  # 显示版本信息
sshpass --help  # 显示帮助信息
```

### 编译产物
- 二进制类型: ELF 64-bit LSB pie executable, ARM aarch64
- 动态链接: /lib/ld-musl-aarch64.so.1
- 功能特性检测: HAVE_FCNTL_H, HAVE_FORK, HAVE_POSIX_OPENPT, HAVE_SELECT, HAVE_STRDUP
