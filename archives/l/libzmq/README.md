# libzmq

## 简介
libzmq 是 ZeroMQ 的核心消息库（C++ 实现、C API），提供高性能异步消息层，
支持 inproc/ipc/tcp/pgm 等传输与 pub-sub、push-pull、req-rep、dealer-router 等模式。
cppzmq、zmqpp、uwsgi-logzmq 等绑定与扩展均以其为底层。仓内已有 `zeromq/4.3.5`
（同名上游的先期归档包名），本目录以官方仓库名 `libzmq` 提供同版本配方。

## OHOS 适配
- 构建系统：CMake（上游双构建系之一）。CMake 4.x 需补丁升级三处
  `cmake_minimum_required`（主工程 2.8.12/3.0.2、tests 2.8.1、unittests 2.8.1 →
  3.5...3.27），并为 `ZMQ_HAVE_BUSY_POLL` 的测试注册加源文件存在性守卫
  （release tarball 不含 test_busy_poll.cpp）。
- 默认形态零外部依赖：ENABLE_CURVE=OFF、WITH_LIBSODIUM=OFF、WITH_OPENPGM=OFF、
  WITH_NORM=OFF、WITH_VMCI=OFF、ENABLE_WS=OFF、WITH_DOC=OFF。
- 构建/CI 环境即 HarmonyOS PC（aarch64）本机：上游 ctest 套件在 build() 阶段
  真跑；4 个依赖 AF_UNIX bind 的测试因 OHOS SELinux 沙箱策略（EPERM）排除，
  见 notes.md 豁免清单。

## 依赖
- 无运行时外部依赖（pthread/rt 由 OHOS musl 提供）

## 功能验证
```bash
conan create . -pr:h=<ohos-aarch64 profile> -pr:b=<同> --build=missing
# build() 内自动执行上游 ctest（96/100 通过 + 4 项平台限制豁免）
```

## 参考
- 官网: https://zeromq.org
- 源码: https://github.com/zeromq/libzmq
