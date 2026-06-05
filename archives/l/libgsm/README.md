# libgsm

GSM 06.10 13 kbit/s RPE/LTP 语音编码库

## 简介
libgsm 是 GSM 06.10 标准的实现，用于语音压缩编码。
- 压缩帧：160 个 13-bit 样本（8kHz 采样率）-> 260 bits
- 实际输出：160 个 16-bit 线性样本 -> 33 字节帧（1650 Bytes/s）

## 主要组件
- libgsm.a: 静态库
- gsm.h: 头文件
- toast/untoast/tcat: 命令行工具

## 参考
- 官网：http://kbs.cs.tu-berlin.de/~jutta/gsm/
- 协议：自定义开源协议
