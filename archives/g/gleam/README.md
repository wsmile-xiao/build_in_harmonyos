# Gleam

## 描述
Gleam是一个静态类型的函数式编程语言，运行在Erlang虚拟机（BEAM）上。

## 特性
- **静态类型**：强大的类型系统，编译时类型检查
- **函数式编程**：支持函数式编程范式
- **BEAM生态系统**：与Erlang/Elixir生态兼容
- **多平台编译**：可编译到Erlang和JavaScript
- **内置工具链**：包含编译器、构建工具、格式化器和包管理器

## 版本信息
当前版本：1.17.0-r0

## 部署方式
使用Alpine Linux musl动态链接二进制部署（预编译musl binary方式）

## 运行时依赖
- libc.musl-aarch64.so.1
- libgcc_s.so.1
- Erlang/OTP（用于编译后的Gleam程序运行，编译器本身不需要）

## 官方网站
https://gleam.run/

## 许可证
Apache-2.0