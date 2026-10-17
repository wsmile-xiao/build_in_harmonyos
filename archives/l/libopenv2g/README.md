# libopenv2g

libopenv2g 是一个 C 语言实现的 ISO/IEC 15118 与 DIN 70121 EXI 编解码器及 V2GTP 帧处理库。

## 功能概述

- ISO 15118-2（ISO1/ISO2）消息数据类型、EXI 编码与解码；
- DIN 70121 和应用握手协议数据类型；
- EXI 位流、头部、字节流工具和 V2GTP framing API；
- Conan 包同时支持静态库和共享库构建选项。

## HarmonyOS PC 适配

- 上游 OpenV2G 0.9.5 ZIP 仅包含 Eclipse 生成的 `Release/makefile`，目标是一个示例可执行文件；本适配通过配方导出可移植的根目录 Makefile，构建可复用的 `libopenv2g` 库；
- 构建使用 HarmonyOS PC 上的 clang、llvm-ar 和 llvm-ranlib，不依赖缺失的 gcc；
- `src/test` 中的示例程序不作为库构建目标；消费者测试通过应用握手 EXI round-trip、位流编码/解码和 V2GTP header API 验证；
- 无第三方编译依赖。

## 依赖

无 Conan 运行时或编译时依赖。

## 验证

```bash
python3 scripts/ohc-run.py conan-verify libopenv2g 0.9.5
python3 scripts/ohc-run.py finish libopenv2g 0.9.5 built
```

## 参考资料

- [OpenV2G SourceForge 项目](https://sourceforge.net/projects/openv2g/)
- [OpenV2G 官网](https://openv2g.sourceforge.net/)
