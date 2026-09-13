# bruteforce-luks — OpenHarmony 编译档案

## 软件简介
bruteforce-luks 用于找回 LUKS 加密卷的密码，支持按字符集暴力枚举与按字典文件匹配两种模式，可指定线程数、密码长度与前后缀。

## 功能概述
- 暴力枚举：按字符集与长度范围逐个试密码
- 字典模式：按文件逐行试密码
- 多线程解密（`-t`）、进度打印（`-v`/USR1 信号）、会话存档与恢复（`-w`）

## OHOS 适配要点
- autotools 构建；tag 归档无 `configure`，需先跑 `autogen.sh` 生成
- 硬依赖系统 `libcryptsetup`（`configure` 探测；无 Conan 包可声明，不写 `requires`，缺库时 `build()` 探针报 R36 下一步）
- mktemp wrapper + `--build=aarch64-unknown-linux-gnu`（沿用 bash/5.3 方案）
- 上游 1.4.0 无测试套件，`test_package` 以二进制冒烟测试覆盖（2 断言）

## 依赖关系
- 系统库：libcryptsetup（系统库，无 Conan 包；需先单独立项适配 `archives/c/cryptsetup` 并发布）、libpthread、libm

## 参考资料
- [上游仓库](https://github.com/glv2/bruteforce-luks)
- [man 手册](https://github.com/glv2/bruteforce-luks/blob/master/doc/bruteforce-luks.1)
