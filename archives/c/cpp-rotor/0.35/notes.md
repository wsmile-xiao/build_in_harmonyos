# cpp-rotor 0.35 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++ (v15.0.4, /data/service/hnp/bin)
- 平台: HarmonyOS PC aarch64 (os=OHOS, armv8, libc++, C++17)
- 状态: built

## 编译步骤

1. 官方 tag v0.35 (commit 1203a914) 归档下载: `https://github.com/basiliscos/cpp-rotor/archive/refs/tags/v0.35.tar.gz`
2. conan install 依赖: `conan install --requires=boost/1.84.0 -pr:a=ci/conan/profiles/ohos-aarch64 --build=missing -g CMakeDeps -g CMakeToolchain`
3. CMake 配置: `cmake .. -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release -DROTOR_BUILD_TESTS=OFF -DROTOR_BUILD_ASIO=OFF -DROTOR_BUILD_EV=OFF -DROTOR_BUILD_WX=OFF -DROTOR_BUILD_FLTK=OFF`
4. 编译: `make -j4` → 产出 librotor.a / librotor_thread.a
5. staging 安装: `make install DESTDIR` 到测试 prefix

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 制品仓 boost/1.90.0.4 配方裁剪，无 date_time 组件 | 裁剪版配方 _components 不含 date_time，CMakeDeps 无 Boost::date_time 目标 | 改用完整配方 boost/1.84.0（导出全部组件目标） |
| 2 | boost/1.91.0/1.91.0.1 包缺 lockfree 头文件 | 裁剪配方按组件导出头文件，lockfree 不在组件列表 | 同上，使用完整配方 boost/1.84.0 |
| 3 | 上游 CMakeLists find_package(Boost COMPONENTS date_time system regex) | rotor 链接 Boost::date_time/system/regex | boost/1.84.0 提供全部三个目标；Boost.System 1.69+ header-only 无库文件属正常 |

## 源码修改

无补丁（本次适配不修改上游源码，仅生成 Conan 配方与测试）。

## 依赖版本

- boost/1.84.0（制品仓完整配方，含 date_time/system/regex 组件目标与 lockfree 头文件）

## 验证结果

```bash
# Adapt 编译（本地门禁）
cmake .. -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake ... && make -j4
# → [100%] Built target rotor / rotor_thread

# 上游测试（upstream_tests 门禁，Catch2 v2 兼容环境）
ctest → 25/25 tests passed, 0 failed（007-plugins … 143-thread-shutdown_flag）

# test_package 消费者测试（conan create 内执行）
./test_cpp-rotor → "hello from cpp-rotor" / "cpp-rotor 0.35 consumer test: OK"
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，requires boost/1.84.0 |
| conandata.yml | 官方源 v0.35 + sha256 |
| test_package/ | 消费者实质测试 + MANIFEST |
| manifest.yaml | 版本元数据 |

## 注意事项

- 制品仓 boost 有裁剪版（1.90.0.4/1.91.0.x）与完整版（1.84.0/1.90.0 配方）之分；依赖 Boost 组件的下游库应使用完整配方版本
- Boost.System 自 1.69 起为 header-only，无 libboost_system 库文件属正常现象，CMake 仅需要其头文件
---

**编译结束**: 2026-09-03 11:43
**最终状态**: built
