# socat — HarmonyOS aarch64 预编译包

## 快速安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- socat 1.7.4.4
```

或手动安装：
```bash
tar xzf socat-1.7.4.4-ohos-aarch64.tar.gz -C ~/usr/local
```

## 可用版本

| 版本 | 状态 | 补丁数 | 包大小 |
|------|------|--------|--------|
| 1.7.4.4 | built | 0 | 626KB |

## 当前版本 (1.7.4.4) 详情

### 包内容
- bin/socat (主程序)
- bin/procan (进程分析工具)
- bin/filan (文件描述符分析工具)

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 编译器: clang 15.0.4
- 质量门禁: G1-G4 PASS

### 功能支持
- ✅ TCP/UDP 端口转发
- ✅ UNIX socket
- ✅ IPv4/IPv6
- ✅ 文件/管道操作
- ✅ 进程执行
- ❌ OpenSSL (需要安装 openssl)

## 环境要求
- HarmonyOS/OpenHarmony aarch64
