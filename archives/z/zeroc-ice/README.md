# zeroc-ice（ZeroC Ice）

## 简介
ZeroC Ice 是高性能 RPC 中间件框架。本归档为其 C++ 版本 3.8.1：Ice 核心运行时（IceSSL 并入 Ice）、IceGrid（部署与管理）、IceStorm（发布/订阅）、Glacier2（防火墙穿越）、IceBridge、IceBox（服务容器）、DataStorm（3.8 新增数据分发服务）以及 Slice 编译器工具链（slice2cpp/slice2py/ice2slice 等）。

## OHOS 适配
- 自研 Makefile 构建（`make os=Linux`），命令行显式传 `CC=/CXX=`（conan buildenv 不生效）；`lib-suffix=` 置空（3.8 的单架构 Linux 分支会按 uname -m 推导出 lib64 后缀，交叉环境下必须显式清空）
- HMDFS 禁符号链接：SONAME 别名（libIce.so.38/libIce.so 等）全部改为真实文件拷贝（补丁 0001，Make.project.rules）
- musl/OHOS SDK 的 `<crypt.h>` 无函数声明且不定义 `__GLIBC__`：Glacier2 密码校验走手写 `extern "C"` crypt 声明并加互斥锁（补丁 0002）
- 应用沙箱 uid 无 /etc/passwd 记录：IceGrid Activator 对自身 uid 跳过 getpwuid_r 与组解析（补丁 0003）
- 测试驱动识别 `sys.platform == 'ohos'`（补丁 0004），上游 allTests.py 可直接在 OHOS 上驱动 C++ 测试矩阵
- OHOS 二进制签名：库文件保留 SDK 链接器自带 .codesign 段（探测式签名，剥离后 selfSign 不可用时禁止留空）
- vendor mcpp 官方 fork v2.7.2.20（制品仓原版 2.7.2 有循环 include 缺陷），slice2cpp 静态链接；OHOS 上 `uname` 为 HarmonyOS，mcpp Makefile 的 Linux 分支不触发，需显式传 `-fPIC` 等 flags
- 3.8 相对 3.7 的结构性变化：IceSSL/IceXML/IcePatch2/IceDB 不再是独立库（IceSSL 并入 Ice，IcePatch2 移除，IceDB 编入 icestormdb/icegriddb），新增 DataStorm 库与 ice2slice 翻译器

## 依赖
- bzip2 1.0.8.2、expat 2.8.2、openssl 3.5.6、lmdb 0.9.35、libedit 20240817（+传递依赖 ncurses 6.4）

## 功能验证
```bash
conan create archives/z/zeroc-ice/3.8.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# test_package: 链接 libIce 初始化 Communicator，输出 "Ice version: 3.8.1"
```
上游 C++ 测试矩阵 100 套闭环（96 通过 + 4 环境限制：Ice/logger、Ice/metrics、IceSSL/configuration、Glacier2/ssl），详见 `3.8.1/notes.md`。

## 参考
- 官网: https://github.com/zeroc-ice/ice
- 版本: 3.8.1（https://github.com/zeroc-ice/ice/archive/refs/tags/v3.8.1.tar.gz）
