# perl-net-mqtt

Perl modules for MQTT Protocol (http://mqtt.org/).

## 描述

Net-MQTT 提供了 MQTT 协议的 Perl 实现，包括：
- `Net::MQTT::Message` - MQTT 消息编解码
- `Net::MQTT::Constants` - MQTT 协议常量
- `Net::MQTT::TopicStore` - MQTT 主题存储管理
- `net-mqtt-pub` - MQTT 发布工具
- `net-mqtt-sub` - MQTT 订阅工具
- `net-mqtt-trace` - MQTT 报文解码工具（需要 Net::Pcap）

这是一个纯 Perl 模块，不包含 C/C++ 编译代码，适合在 OpenHarmony 平台上直接使用。

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.163170-r0 | published | 2026-06-29 | 初始适配，添加 FindBin 补丁 |

## 使用方法

```bash
# 通过 Conan 安装
conan install --requires=perl-net-mqtt/1.163170-r0@ohpcd/stable

# 设置 PERL5LIB
export PERL5LIB=$(conan cache path perl-net-mqtt/1.163170-r0@ohpcd/stable)/lib

# 使用 MQTT 发布
perl -MNet::MQTT::Constants -e 'print "Module loaded OK\n"'

# 或使用命令行工具
net-mqtt-pub --help
net-mqtt-sub --help
```

## 许可证

Perl (Artistic License 2.0)
