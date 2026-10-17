# libeot

## 简介
解析微软 Embedded OpenType (EOT) 嵌入字体并转换为 TrueType 的 C 库（MPL-2.0），
附带 `eot2ttf` 命令行工具。上游唯一 tag v0.01（2013-11-30）。

## OHOS 适配
- 构建系统: makefile（上游 autotools 骨架无生成 configure，构建 profile PATH 无
  automake/libtoolize；配方按上游 Makefile.am 源列表与 release 旗标
  `--std=c99 -DDECOMPRESS_ON -O2` 直接编译，无源码修改、无补丁）
- 详见各版本 notes.md 获取适配详情

## 依赖
无外部依赖（仅 libc；上游构建脚本无任何库探测）。

## 功能验证
- test_package 消费者测试 23 项断言（EOT v1 元数据解析、无压缩转换字节一致、
  UTF-16 字符串解析、截断/损坏负路径）
- `eot2ttf` 工具端到端往返字节一致

## 参考
- https://github.com/umanwizard/libeot
