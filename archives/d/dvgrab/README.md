# dvgrab

> Digital video capture tool for IEEE 1394 (FireWire) devices

## 简介

dvgrab 是一个从 IEEE 1394（FireWire/i.LINK）设备抓取数字视频的工具，支持 DV 和 HDV 格式。它可以将视频直接保存为 Raw DV、AVI Type 1/2 或 QuickTime 格式。

## OHOS 适配要点

- 需要替换 config.guess/config.sub 以识别 OpenHarmony 平台
- musl libc 缺少 `pthread_testcancel`、`pthread_cancel`，需要用宏替代
- `__ASSERT_FUNCTION` 是 glibc 特有，musl 使用 `__func__`
- 需要添加 `<sys/select.h>` 头文件以解决隐式声明问题

## 依赖

| 依赖 | 说明 |
|------|------|
| libraw1394 | IEEE 1394 库 |
| libavc1394 | AV/C 协议库 |
| libiec61883 | IEC 61883 协议库 |

## 参考

- [源码仓库](https://github.com/ddenn/dvgrab)