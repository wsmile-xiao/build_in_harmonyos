# dbus-cxx 2.5.1 适配笔记

## 编译环境
- 构建系统: CMake（上游 cmake_minimum_required 3.12）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang++，C++17）
- 状态: built（local_verify 通过：双 profile conan create EXIT=0）

## 任务背景

- 平台任务 #13880（feat/dbus-cxx-2.5.1）
- 上游 https://github.com/dbus-cxx/dbus-cxx tag **2.5.1**（注意：无 `v` 前缀，
  `refs/tags/v2.5.1` 不存在，codeload 404；正确源为
  `https://github.com/dbus-cxx/dbus-cxx/archive/refs/tags/2.5.1.tar.gz`，
  sha256 848467b14db37710ac3ad31cc6474b2d65b9b24e6cdcbb7e88c7637c0ad7b388）
- dbus-cxx 2.x 是 DBus 协议的完整自研 C++ 实现：README 明示
  "a complete ground-up implementation of the DBus protocol, **without
  libdbus**"。源码级验证：dbus-cxx/ 下无任何 `#include <dbus/...>`（仅
  注释掉的历史 libdbus 调用残留在 connection.cpp 注释里）。
  **因此配方不依赖 dbus/libdbus 包**——仅 libsigc/3.0.6（sigc++-3.0）。

## W0 依赖核验

| 依赖 | 版本 | R35 核验 |
|---|---|---|
| libsigc | 3.0.6 | `conan download -r=ohpcd --only-recipe` EXIT=0（制品仓已发布） |
| dbus | — | **不需要**：dbus-cxx 2.x 无 libdbus 依赖（协议自研），源码 grep 证实 |

## 适配要点

**零补丁适配**：上游 CMakeLists 无平台硬编码，OHOS（CMAKE_SYSTEM_NAME=
HarmonyOS）交叉编译一遍过。仅 1 个无关警告（utility.cpp 的
std::thread::id 作 %08X 格式参数——上游代码风格问题，不影响功能）。

- CMake 变量: ENABLE_EXAMPLES/ENABLE_TOOLS/BUILD_SITE/BUILD_TESTING 全 OFF
  （tools 需 expat+libcppgenerate，examples/website 非库本体）
- C++17（libsigc++-3.0 要求，上游 set_property 已设）
- 头文件布局: 上游 install 到 include/dbus-cxx-2.0/{,dbus-cxx/}，
  package_info 暴露两个 includedir
- libsigc 传递依赖（transitive_headers/libs）：dbus-cxx 公共头直接
  `#include <sigc++/sigc++.h>`，消费者需要 sigc 头可见
- generators: CMakeDeps + PkgConfigDeps（上游用 pkg_check_modules 发现
  sigc++-3.0）+ generate() 内 CMakeToolchain 实例化（设 cache 变量）

## 本机验证（W3 双 profile）

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=default --build=missing   # EXIT=0
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 \
                 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing  # EXIT=0
```

## 上游测试（157 注册 / 103 执行 / 103 PASS / 54 环境豁免）

ctest 注册口径（unit-tests/CMakeLists.txt）：
- **157 项 = 154（unit-tests 主文件）+ 1（robustness，ENABLE_ROBUSTNESS_TESTS
  默认 OFF 不注册进默认形态... 实测 ctest -N 输出 Total Tests: 157）**
- 分布：test-callmessage 13 / test-messageiterator 52 / test-path 18 /
  test-signature 15 / test-validation 3 / test-unset-envvars 2 = **103 项
  纯本地**；其余 **54 项需 dbus-daemon**（dbus-wrapper*.sh /
  dbus-run-session 包装：connection 5 / object 3 / data 13 / signal 6 /
  introspection 8 / customaddress 1 / affinity 5 / filedescriptor 2 /
  recursive 2 / property 6 / robustness 未开 + tools-tests 未开）

本机实测（OHOS 交叉编译测试二进制后手工按 ctest 注册的精确参数跑）：

| 组 | 用例数 | 结果 |
|---|---|---|
| test-callmessage | 13 | 13/13 PASS |
| test-messageiterator | 52 | 52/52 PASS |
| test-path | 18 | 18/18 PASS |
| test-signature | 15 | 15/15 PASS |
| test-validation | 3 | 3/3 PASS |
| test-unset-envvars | 2 | 2/2 PASS（验证无 DBUS_SESSION_BUS_ADDRESS 环境时优雅失败） |
| **合计** | **103** | **103 PASS（100%）** |

需要 dbus-daemon 的 54 项豁免证据：
```
$ which dbus-launch dbus-run-session dbus-daemon
dbus-launch not found
dbus-run-session not found
dbus-daemon not found
```
OHOS 平台无 dbus-daemon 工具链（制品仓 dbus/1.14.10.x 配方只构建客户端库
libdbus-1，不产 daemon）。直接跑 daemon 类测试二进制的实测：
```
$ ./test-connection create_signal_proxy
DBus.Connection [ERROR] - Env `DBUS_SESSION_BUS_ADDRESS' not found, fail to open transport
Segmentation fault (exit 139)   # 连接 nullptr 后测试框架 deref
```
（test-unset-envvars 专项验证的正是这个无总线场景——它 PASS，因为断言
的就是优雅错误处理。）

## 消费者测试（test_package）

C++ 消费者真实调用上游公开 API：DBus::Path 构造/校验/分解/追加 +
DBus::Signature 校验 + DBus::CallMessage::create(4 参) +
MessageAppendIterator<<int32_t<<string（编组链，signature()=="is" 断言）+
DBus::Validator::validate_bus_name 正反例。含负向断言（非法路径/非法签名/
非法总线名必须被拒绝）。编译+链接通过；运行受限（OHOS 加载器 E488 系：
`_ZTISt12out_of_range: symbol not found` 等运行库符号缺失）按先例降级
compile+link 口径申报。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libdbus-cxx.so（soname libdbus-cxx.so.2） | 主库 |
| include/dbus-cxx-2.0/dbus-cxx.h + dbus-cxx/*.h（49 个） | 公共头 |
| lib/pkgconfig/dbus-cxx-2.0.pc + cmake/dbus-cxxConfig.cmake | 消费者配置 |
