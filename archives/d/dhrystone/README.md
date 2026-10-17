# Dhrystone

Dhrystone 是用于测量整数运算和编译器表现的命令行基准程序。
2.1 版本保留原始计算流程、字符串操作和两个独立编译单元。

## 使用

```sh
dhrystone --version
printf '160000000\n' | dhrystone
```

迭代次数从 stdin 读取，范围为 1 到 INT_MAX-10。程序使用用户 CPU 时间；
少于两秒时会提示增加运行次数，此时输出仅可用于正确性检查。
虚拟机测量不能代表 HarmonyOS PC 实机性能；跨编译器比较须遵循上游 RATIONALE。

## HarmonyOS 适配

支持 HarmonyOS 6.0 的 AArch64 构建和 x86_64 虚拟机验证。
修复旧式 C 声明和指针输出，使用运行时查询的进程计时刻度。
Conan 管理构建与安装；无第三方库依赖，仅使用系统 libc。
消费者测试校验完整参考值、输入边界及鸿蒙加载器/临时目录运行行为。

## 来源

- [Netlib 官方归档](https://www.netlib.org/benchmark/)
- [Dhrystone 2.1 原始源码及说明](https://www.netlib.org/benchmark/dhry-c)

归档未附独立 SPDX 许可证，配方保留作者原始说明及头部，标记为 LicenseRef-Dhrystone。
