# ZeroC (Ice)

## 简介
ZeroC Ice 是高性能 RPC 中间件框架，包含 Ice 核心运行时、IceGrid（部署与管理）、IceStorm（发布/订阅）、Glacier2（防火墙穿越）、IceBridge、IceBox（服务容器）以及 Slice 编译器工具链（slice2cpp 等 25 个命令行工具）。

## OHOS 适配
- 自研 Makefile 构建（`make os=Linux`），命令行显式传 `CC=/CXX=`（conan buildenv 不生效）
- HMDFS 禁符号链接：SONAME 别名（libIce.so.37/libIce.so 等）全部改为真实文件拷贝（6 个补丁中的 Make.project.rules）
- musl 无 `<crypt.h>`：Glacier2CryptPermissionsVerifier 手写 `extern "C"` crypt 声明并加互斥锁保护非重入调用
- 应用沙箱 uid 无 /etc/passwd 记录：IceGrid Activator 对自身 uid 跳过 getpwuid_r
- OHOS 二进制签名：库文件保留 SDK 链接器自带 .codesign 段（探测式签名，剥离后 selfSign 不可用时禁止留空）
- vendor mcpp 官方 fork v2.7.2.20（制品仓原版 2.7.2 有循环 include 缺陷），slice2cpp 静态链接

## 依赖
- bzip2 1.0.8、expat 2.8.2、openssl 3.5.6、lmdb 0.9.35、libedit 20240817（+传递依赖 ncurses 6.4）

## 功能验证
```bash
conan create archives/z/zeroc/3.7.10 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# test_package: 链接 libIce 初始化 Communicator，输出 "Ice version: 3.7.10"
```
上游 C++ 测试矩阵 93 套闭环（88 通过 + 4 平台限制 + 1 上游跳过），详见 `3.7.10/reports/r51-test-matrix.md`。

## 参考
- 官网: https://github.com/zeroc-ice/ice
- 版本: 3.7.10（https://github.com/zeroc-ice/ice/archive/refs/tags/v3.7.10.tar.gz）
