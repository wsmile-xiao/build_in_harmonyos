# qmic

[qmic](https://github.com/linux-msm/qmic)（linux-msm 项目，BSD-3-Clause）—— Qualcomm MSM Interface
（QMI）的 IDL 编译器：把 `.qmi` 接口描述编译成 C 源码与头文件。

## 简介

QMI 是高通 SoC 上 modem/外设与主控之间使用的消息协议，接口用 `.qmi` 文本描述（package、const、
struct、request/response/indication 消息及其 TLV 成员）。`qmic` 读入该描述并生成两份产物：

- `qmi_<package>.c` — 消息编解码实现
- `qmi_<package>.h` — 类型、常量与消息结构声明

用法：IDL 从 **stdin** 读入，`-a` 选择 accessor 后端、`-k` 选择 kernel 后端，产物写到**当前目录**。

```bash
qmic -a < my_service.qmi    # 生成 qmi_my_service.c / qmi_my_service.h
```

## 功能概述

- 解析 `.qmi` IDL：package/const/struct/request/response/indication，`required`/`optional` 成员、定长与变长数组、TLV 编号
- 数值字面量：十进制、八进制、十六进制（含 `0X`），64 位范围校验、越界与非法字面量报错
- 语义检查：重复常量/结构体成员/消息成员名、重复成员编号、重复 package 声明、缺 package 声明、超长 token
- 两种代码后端：`-a` accessor（用户态解析）、`-k` kernel（内核风格）

## OHOS 适配要点

- **纯 POSIX C，零依赖**：4 个 `.c` + 2 个 `.h`，手写 Makefile，无 configure/CMake；`CC`/`CFLAGS` 经 make 命令行注入即可全量接管，构建系统无需补丁。
- **唯一源码补丁**：`parser.c` 的 `yyerror()` 用 glibc 专有的 `program_invocation_short_name` 拼错误前缀，
  OHOS musl 不声明该符号（编译期 `use of undeclared identifier`）。补丁改用 `__progname`——glibc、musl、
  OHOS libc 都导出，且上游未改动的 `qmic.c` 本就用它打印 Usage，行为等价。补丁**不含平台条件编译**，
  非 OHOS 平台不受影响。
- **上游测试形态**：`tests/` 下 18 个 `.qmi` 语料（7 accept / 11 reject），但**没有测试运行器**——Makefile
  无 `check`/`test` 目标，也没有 CI 或脚本。期望基线在上游未修改源码上双平台实测确立。

## 依赖关系

- 编译依赖：无（仅 C 标准库）
- 运行依赖：无（单一静态可执行文件 `bin/qmic`）

## 构建与验证

```bash
# OHOS aarch64 构建
conan create archives/q/qmic/1.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# test_package: 消费者语料一致性（22 断言）+ 鸿蒙平台专项（10 断言）

# 配方验证
python3 scripts/ohc-run.py conan-verify qmic 1.0
```

## 参考资料

- 上游仓库: https://github.com/linux-msm/qmic
- 上游 tag: v1.0
- 相关规范: Qualcomm QMI IDL（libqmi 生态，同仓归档见 `archives/l/libqmi`）
