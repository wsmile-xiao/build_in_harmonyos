# FPC - Free Pascal Compiler

## 简介

FPC (Free Pascal Compiler) 是一个开源的Pascal编译器，支持多种目标平台和架构。

## 版本历史

| 版本 | 状态 | 发布日期 | 说明 |
|------|------|----------|------|
| 3.2.2 | published | 2026-05-27 | 预编译包，支持aarch64-linux |

## 特性

- 自举编译器（使用Pascal编写）
- 支持多种目标平台（Linux, Windows, macOS等）
- 支持多种CPU架构（x86_64, aarch64, arm等）
- 完整的RTL（运行时库）
- 支持Objective Pascal扩展

## 鸿蒙平台注意事项

1. **ELF签名机制**: 所有二进制文件必须签名才能执行
2. **自举编译限制**: 新生成的编译器需要立即签名才能继续编译
3. **推荐使用预编译包**: 避免复杂的自举编译流程

## 编译信息

### 3.2.2版本

- **编译方法**: 使用预编译bootstrap包
- **预编译包大小**: 17.3MB
- **包含组件**:
  - ppca64: aarch64编译器
  - fpc: 前端脚本
  - RTL单元文件

## 使用示例

```pascal
program HelloWorld;
begin
  WriteLn('Hello from FPC on HarmonyOS!');
end.
```

编译命令:
```bash
ppca64 -Fu/usr/local/lib/fpc/3.2.2/units/aarch64-linux/rtl hello.pas
./hello
```

## 参考链接

- 官方网站: https://www.freepascal.org/
- 源码下载: https://sourceforge.net/projects/freepascal/
- 文档: https://www.freepascal.org/docs.html