# liblo

## 描述
轻量级 OSC (Open Sound Control) 实现 - 用于实时音频/音乐软件通信的轻量级库。

OSC 是一种用于实时音频/音乐软件通信的协议，广泛应用于音频合成器、音乐软件和多媒体系统之间的数据交换。

## 主页
https://liblo.sourceforge.net/

## 已编译版本
- 0.34 (2026-05-20)

## 依赖
无外部依赖

## 提供组件
- **liblo.so** - OSC 核心库
- **oscdump** - OSC 消息 dump 工具（监听并显示 OSC 消息）
- **oscsend** - OSC 消息发送工具
- **oscsendfile** - OSC 文件发送工具

## 使用示例
```bash
# 监听 OSC 消息
oscdump 7777

# 发送 OSC 消息
oscsend localhost 7777 /test if 42 3.14
```

## 编译备注
- 由于 HMDFS 文件系统限制，使用 cmake 构建而非 autotools
- 需要配置 LD_LIBRARY_PATH 或使用 RPATH 修复
