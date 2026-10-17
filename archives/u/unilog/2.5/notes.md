# unilog 2.5 适配笔记

## 编译环境
- 构建系统: CMake (minimum 3.5)
- 编译日期: 2026-09-18
- 编译器: clang 15 (OHOS SDK)
- 状态: built

## 编译步骤

```bash
tar xf unilog_2.5.orig.tar.xz
cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TEST=ON
cmake --build build -j1
ctest --output-on-failure   # 3 tests: test_demo, test_exception, test_exception_print
cmake --install build --prefix=/usr
```

Conan 流程: `conan create archives/u/unilog/2.5 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(glog) 找不到 | OHOS 非标准路径 | Conan CMakeToolchain 生成 glogConfig.cmake，通过 CMAKE_PREFIX_PATH 自动定位 |
| 2 | Boost system/filesystem 缺失 | 上游 src/CMakeLists 显式 find_package | requires boost/1.85.0，Conan 注入 BoostConfig.cmake |
| 3 | 源码包下载超时 | archive.ubuntu.com 直连慢 | conandata.yml 配置 Tsinghua/Aliyun 镜像优先，官方 URL 回退 |

## 依赖版本

- glog/0.7.1
- boost/1.85.0 (提供 system/filesystem)

## 验证结果

```bash
# 上游测试 3/3 通过 (ctest)
HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"ctest","command":"ctest --output-on-failure","discovered":3,"executed":3,"passed":3,"failed":0,"skipped":0}
# test_package 1/1 通过
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"ctest","discovered":1,"passedCount":1}
```

## 交付物

| 文件 | 说明 |
|------|------|
| libunilog.so.2.5.0 + soname | 共享库 |
| include/UniLog/*.hpp | 头文件 |
| share/cmake/unilog/* | CMake config |

## 注意事项
- 日志输出默认到 ./log，需应用侧调用 UniLog::setUniLogPath 配置落盘路径
- UNI_LOG_NDEBUG 在 Release 自动定义，Debug 保留详细堆栈
