# perl-net-mqtt-simple

**Net::MQTT::Simple** — Minimal MQTT version 3.1.1 interface (pure Perl)

## 软件描述

Net::MQTT::Simple 是一个纯 Perl 实现的 MQTT v3.1.1 客户端模块，提供最小化的
MQTT 协议接口。支持以下功能：

- QoS 0 消息发布 (publish)
- 主题订阅与消息接收 (subscribe)
- 通配符主题匹配 (+ 和 #)
- 保留消息 (retained messages)
- Last Will and Testament (遗嘱消息)
- 自动重连
- 心跳保活 (keep-alive ping)
- SSL/TLS 支持 (可选，需 IO::Socket::SSL)

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.33-r0 | built | 2026-06-26 | 首次鸿蒙平台适配，纯 Perl 模块无需补丁 |

## 使用说明

### 安装

```bash
# 通过 Conan 安装
conan install --requires=perl-net-mqtt-simple/1.33-r0
```

### 基本用法

```perl
use Net::MQTT::Simple;

# 连接到 MQTT broker
my $mqtt = Net::MQTT::Simple->new("broker.example.com:1883");

# 发布消息
$mqtt->publish("sensor/temperature" => "23.5");

# 发布保留消息
$mqtt->retain("status/online" => "yes");

# 订阅主题
$mqtt->subscribe(
    "sensor/+" => sub {
        my ($topic, $message) = @_;
        print "$topic: $message\n";
    },
);

# 运行事件循环
$mqtt->run();

# 或者非阻塞处理
$mqtt->tick(0.1);  # 处理 100ms 的网络事件
```

### 鸿蒙平台特性

- **纯 Perl 模块**: 无需 XS 编译，不受 SELinux HMDFS 限制影响
- **直接可用**: 安装后即可使用，无需管理员权限
- **无外部依赖**: 仅依赖 Perl 核心模块 (IO::Socket::IP)
- **SSL 可选**: SSL/TLS 功能需要额外安装 IO::Socket::SSL

## 链接

- [CPAN](https://metacpan.org/release/Net-MQTT-Simple)
- [GitHub](https://github.com/Juerd/Net-MQTT-Simple)
- [MQTT 3.1.1 协议规范](http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html)
