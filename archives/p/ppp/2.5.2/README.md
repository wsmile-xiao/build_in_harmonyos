# PPP 2.5.2 for OpenHarmony

## 软件简介

PPP (Point-to-Point Protocol) 是点对点协议的实现，用于在两个节点之间建立直接连接。本项目为 PPP 2.5.2 在 OpenHarmony 平台上的预编译版本。

### 主要功能

- **pppd**: PPP 守护进程主程序，负责建立和管理 PPP 连接
- **chat**: 拨号对话脚本工具，用于与调制解调器交互
- **pppstats**: PPP 连接状态和流量统计工具

### 支持的特性

- ✅ PPP over Serial（串口 PPP）
- ✅ PAP/CHAP 认证
- ✅ IP 地址协商
- ✅ DNS 自动配置
- ⚠️ PPPoE (需要适配内核头文件)
- ✅ 流量统计和监控

## 版本信息

- **软件版本**: PPP 2.5.2
- **编译平台**: OpenHarmony
- **目标架构**: aarch64
- **SDK 版本**: ohos-sdk 26.0.0.18
- **编译状态**: 核心组件成功（pppd/chat/pppstats），PPPOE 插件失败

## 编译产物

```
bin/
├── pppd        # PPP 守护进程主程序
├── chat        # 拨号对话脚本工具
└── pppstats    # PPP 统计工具
```

## 安装方法

### 方法一：直接安装（推荐）

```bash
# 复制可执行文件到系统目录
cp bin/pppd /usr/bin/
cp bin/chat /usr/bin/
cp bin/pppstats /usr/bin/

# 设置可执行权限
chmod 755 /usr/bin/pppd
chmod 755 /usr/bin/chat
chmod 755 /usr/bin/pppstats

# 创建配置目录
mkdir -p /etc/ppp/peers
mkdir -p /etc/ppp/options

# 设置必要权限
chmod 700 /etc/ppp
```

### 方法二：使用预编译包

```bash
# 解压预编译包
tar xzf ppp-2.5.2-ohos-aarch64.tar.gz -C /
```

## 配置说明

### 1. 创建 PPP 配置文件

**基本配置** `/etc/ppp/options`:
```
# PPP 基本选项
noauth
defaultroute
usepeerdns
persist
maxfail 5
holdoff 10
```

### 2. 创建拨号脚本

**串口拨号示例** `/etc/ppp/peers/serial`:
```
# 串口 PPP 连接
/dev/ttyUSB0
115200
connect '/usr/sbin/chat -v -f /etc/ppp/chat/isp.chat'
noauth
defaultroute
usepeerdns
```

### 3. 创建认证文件

**PAP 认证** `/etc/ppp/pap-secrets`:
```
# 用户名    服务提供商    密码
username    *             password
```

**CHAP 认证** `/etc/ppp/chap-secrets`:
```
# 用户名    服务提供商    密码
username    *             password
```

### 4. 创建 Chat 脚本

**调制解调器拨号脚本** `/etc/ppp/chat/isp.chat`:
```
TIMEOUT 10
ABORT 'BUSY'
ABORT 'NO ANSWER'
ABORT 'ERROR'
'' ATZ
OK 'ATDT 12345678'        # 替换为实际拨号号码
TIMEOUT 60
CONNECT ''
```

## 使用方法

### 启动 PPP 连接

```bash
# 使用配置文件启动
pppd call serial

# 直接指定参数启动
pppd /dev/ttyUSB0 115200 noauth defaultroute usepeerdns

# 启用调试模式
pppd call serial debug nodetach
```

### 查看连接状态

```bash
# 显示 PPP 连接统计
pppstats

# 显示详细信息
pppstats -v

# 持续监控
watch pppstats
```

### 断开连接

```bash
# 查找 pppd 进程
ps | grep pppd

# 终止进程
kill <pid>

# 或使用 pkill
pkill pppd
```

## OpenHarmony 注意事项

### 1. 权限要求

PPP 守护进程需要以下权限和条件：

- **网络权限**: `ohos.permission.INTERNET`
- **网络信息权限**: `ohos.permission.GET_NETWORK_INFO`
- **Root 权限**: pppd 需要以 root 权限运行
- **设备访问**: 需要访问 `/dev/ppp` 设备节点

### 2. 内核支持

确保 OpenHarmony 内核支持以下特性：

```
CONFIG_PPP=y
CONFIG_PPP_ASYNC=y
CONFIG_PPP_DEFLATE=y
CONFIG_PPP_BSDCOMP=y
CONFIG_PPP_MPPE=y
```

### 3. PPPOE 插件问题

**编译失败原因**: 
PPPOE 插件编译时遇到内核头文件定义冲突：
```
error: redefinition of '__packed' with a different type
```

**解决方案**:
1. 更新 OpenHarmony 内核头文件
2. 修改 `linux/if_pppox.h` 头文件定义
3. 使用第三方 PPPoE 实现
4. 等待 OpenHarmony 官方修复

### 4. 设备节点

如果 `/dev/ppp` 不存在，需要创建：

```bash
# 检查 PPP 内核模块
lsmod | grep ppp

# 加载 PPP 模块（如果需要）
modprobe ppp_generic
modprobe ppp_async

# 创建设备节点（如果需要）
mknod /dev/ppp c 108 0
chmod 600 /dev/ppp
```

### 5. 网络配置

PPP 连接建立后：

```bash
# 检查网络接口
ifconfig ppp0

# 检查路由表
route -n

# 检查 DNS
cat /etc/resolv.conf
```

### 6. 调试技巧

```bash
# 启用详细日志
pppd call serial debug nodetach logfd 2

# 查看系统日志
dmesg | grep ppp

# 检查 PPP 状态
cat /proc/net/ppp/stats
```

## 故障排查

### 常见问题

#### 1. 连接失败

**症状**: pppd 无法建立连接

**检查清单**:
- [ ] 串口设备是否存在 `/dev/ttyUSB0`
- [ ] 是否有访问设备的权限
- [ ] Chat 脚本是否正确
- [ ] 认证信息是否正确
- [ ] 调试模式输出：`pppd call serial debug nodetach`

#### 2. 权限不足

**症状**: `Permission denied`

**解决方案**:
```bash
# 检查文件权限
ls -l /usr/bin/pppd
ls -l /etc/ppp

# 设置正确权限
chmod 4755 /usr/bin/pppd
chmod 600 /etc/ppp/pap-secrets
chmod 600 /etc/ppp/chap-secrets
```

#### 3. DNS 不生效

**症状**: 可以连接但无法解析域名

**解决方案**:
```bash
# 检查 DNS 配置
cat /etc/resolv.conf

# 手动指定 DNS
echo "nameserver 8.8.8.8" > /etc/resolv.conf
```

#### 4. 连接中断

**症状**: PPP 连接频繁断开

**解决方案**:
- 增加重连参数：`persist maxfail 0 holdoff 10`
- 检查串口波特率
- 检查调制解调器状态
- 查看系统日志

## 依赖项

### 运行时依赖

- **openssl**: >= 1.1.0 (加密认证支持)
- **glibc**: >= 2.28 (C 标准库)

### 编译时依赖

- **openssl-dev**: >= 1.1.0 (SSL 开发头文件)

## 文件清单

```
archives/p/ppp/2.5.2/
├── bin/
│   ├── pppd           # PPP 守护进程
│   ├── chat           # 拨号工具
│   └── pppstats       # 统计工具
├── lib/               # 库文件（无）
├── include/           # 头文件（无）
├── patches/           # 补丁文件（无）
├── reports/
│   └── build.log      # 编译日志
├── packaging/
│   └── ppp-2.5.2-ohos-aarch64.tar.gz  # 预编译包
├── manifest.yaml      # 元数据
└── README.md          # 本文档
```

## 技术支持

### 参考文档

- PPP 官方文档: https://ppp.samba.org/
- OpenHarmony 文档: https://docs.openharmony.cn/
- PPP 协议 RFC 1661: https://tools.ietf.org/html/rfc1661

### 问题反馈

如遇到问题，请提供以下信息：
1. OpenHarmony 版本
2. 设备型号
3. pppd 调试输出 (`pppd call serial debug nodetach`)
4. 系统日志 (`dmesg | grep ppp`)
5. 配置文件内容

## 许可证

PPP 采用以下许可证：
- **BSD-3-Clause**: 部分 PPP 代码
- **GPL-2.0**: pppd 主程序

使用时请遵守相应许可证条款。

## 版本历史

- **2.5.2** (2025-06-17): OpenHarmony aarch64 预编译版本
  - ✅ 核心组件编译成功
  - ⚠️ PPPOE 插件需要额外适配
  - 📝 添加 OpenHarmony 适配说明

---

**最后更新**: 2025-06-17  
**编译者**: OpenHarmony Build System  
**适用平台**: OpenHarmony >= 4.0, aarch64