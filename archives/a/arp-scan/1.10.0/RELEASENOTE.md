# arp-scan 1.10.0 Release Notes for OpenHarmony

## 发布信息

- **软件版本**: arp-scan 1.10.0
- **发布日期**: 2026-05-16
- **目标平台**: OpenHarmony (aarch64)
- **构建状态**: partial (功能完整，测试部分受限)

---

## 新增功能

这是 arp-scan 在 OpenHarmony 平台的首次编译发布：

- ✅ 完整的 arp-scan 1.10.0 功能
- ✅ 静态链接 libpcap 1.10.6
- ✅ 包含完整 IEEE OUI 数据库 (47399 条记录)
- ✅ 支持 TPACKET_V3 高性能扫描
- ✅ PIE (位置无关可执行文件) 支持

---

## 已知问题

1. **网络权限要求**
   - arp-scan 需要 CAP_NET_RAW 权限或 root 权限
   - 普通用户无法直接运行扫描功能
   - 解决方案：使用 `setcap cap_net_raw+ep arp-scan`

2. **平台检测限制**
   - config.guess 不自动识别 HarmonyOS
   - 需要手动指定 `--build=aarch64-unknown-linux-ohos`

---

## 安装说明

### 方法 1: 使用预编译包

```bash
# 解压预编译包
tar xzf arp-scan-1.10.0-ohos-aarch64.tar.gz

# 运行安装脚本
./install-arp-scan-1.10.0.sh

# 设置权限（可选）
setcap cap_net_raw+ep /storage/Users/currentUser/usr/local/bin/arp-scan
```

### 方法 2: 手动安装

```bash
# 复制文件
cp arp-scan ~/usr/local/bin/
cp -r share/arp-scan ~/usr/local/share/
cp -r etc/arp-scan ~/usr/local/etc/
```

---

## 使用示例

### 验证安装

```bash
$ arp-scan --version
arp-scan 1.10.0
libpcap version 1.10.6 (64-bit time_t, with TPACKET_V3)
```

### 基本扫描（需要权限）

```bash
# 扫描本地网络
$ sudo arp-scan --localnet

# 扫描指定网段
$ sudo arp-scan 192.168.1.0/24

# 显示详细信息
$ sudo arp-scan -v 192.168.1.1-254
```

---

## 依赖信息

| 依赖 | 版本 | 类型 |
|------|------|------|
| libpcap | 1.10.6 | 静态链接 |
| musl libc | 系统提供 | 动态链接 |

---

## 文件大小

| 文件 | 大小 |
|------|------|
| arp-scan 二进制 | 96 KB |
| ieee-oui.txt | 1.4 MB |
| mac-vendor.txt | 2 KB |
| 预编译包 (tar.gz) | 1.9 MB |

---

## 测试结果

| 测试项 | 结果 |
|--------|------|
| 版本验证 | ✅ PASS |
| 参数解析 | ✅ PASS |
| 二进制格式 | ✅ PASS |
| 链接依赖 | ✅ PASS |
| 数据文件 | ✅ PASS |
| 网络功能 | ⚠️ SKIP (需权限) |

**总体状态**: 功能完整，运行时需网络权限

---

## 更新历史

- **2026-05-16**: 首次发布 arp-scan 1.10.0 for OpenHarmony

---

**维护者**: OpenHarmony Compile Agent
**联系方式**: https://github.com/royhills/arp-scan/issues