# mlddc 1.0 适配笔记

## 上游信息
- 上游仓库: https://github.com/OS2World/APP-INTERNET-mlddc
- 上游源码版本: MLDDC 3.2.0（生态补丁版本 1.0，上游无官方 tag）
- 功能: Monolith (ml.org) 动态 DNS 服务客户端（1997 年，纯 C）

## 编译环境
- 构建系统: 直接 clang 编译（Makefile 等价），无 configure
- 编译器: clang（hnp 工具链）
- 状态: 成功

## 编译要点
- CFLAGS 追加 `-fgnu89-inline`：netio.h 中 `inline extern void Disconnect(...)` 
  在 C99 语义下会被 mlddc.c 与 netio.c 两个 TU 各自实例化，产生
  `ld.lld: error: duplicate symbol: Disconnect`；gnu89-inline 语义下
  inline 定义不产生外部符号，与 1997 年 gcc 编译行为一致。

## 运行验证
- 无输入运行: 输出版本 banner + "Invalid user data"，退出码 10（预期错误路径）
- deactivate 模式（echo d | mlddc）: 退出码 0

## 测试
- test_package: fork+exec 运行包内 mlddc，断言无输入退出码 10
  （证明程序可执行、链接正常，非崩溃/加载失败）
