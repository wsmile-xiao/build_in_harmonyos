# readerwriterqueue 1.0.7 适配笔记

## 编译环境
- 构建系统: cmake（上游 INTERFACE 库，header-only）
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）/ clang++ 同参替代 g++（设备未装 g++）
- cmake: 4.1.2 / make: GNU Make 4.4.1（-j1）
- 状态: built

## 编译步骤

1. 上游源码：`https://github.com/cameron314/readerwriterqueue/archive/refs/tags/v1.0.7.tar.gz`
   SHA-256 `532224ed052bcd5f4c6be0ed9bb2b8c88dfe7e26e3eb4dd9335303b059df6691`（标签 v1.0.7 = 8b2176698e9bdaba653cdc20c32b54737a934b47）。
2. 原生 CMake 探索（最小参数，零补丁）：`cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=<tmp>` → configure/build/`make install` 全部 exit 0；头文件安装至 `include/readerwriterqueue/`（atomicops.h、readerwriterqueue.h、readerwritercircularbuffer.h + LICENSE.md），与配方 package() 路径一致。
3. 上游单元测试（设备无 g++，Makefile 硬编码 g++，用 clang++ 同参替代）：
   `clang++ -std=c++11 -Wsign-conversion -Wpedantic -Wall -DNDEBUG -O3 -g tests/unittests/unittests.cpp tests/common/simplethread.cpp -o unittests -pthread -lrt -Wl,--no-as-needed`
   运行 `./unittests`：17/17 用例 passed，"All tests passed"（exit 0）。
4. 上游压测 stabtest（无限循环设计，编译同上）：
   `timeout 100 ./stabtest` → 受控观察 100s，完成 Test#0..#39 共 40 轮，`ERROR DETECTED` 计数 0，按设计截断非失败。
5. Conan 打包：`conan create` + test_package 消费者测试（见 reports/ 与 PR 数据）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 Makefile 硬编码 `g++`，设备 `command -v g++` 无此命令 | 设备仅提供 clang 工具链 | 以 clang++ 使用与 Makefile 完全相同的参数集编译同一组源文件；编译、运行结果均正常，已记录于 test_package/MANIFEST.yml |

## 源码修改

无补丁。1.0.7 在 OHOS (aarch64) 原生 configure/build/install 及上游测试全部通过，无需修改上游源码。

## 依赖版本

无第三方依赖（header-only，仅依赖 C++11 标准库与 pthread/rt 系统库）。

## 验证结果

```bash
# 上游 unittests（统计单位：minitest REGISTER_TEST 用例）
./unittests   # 17 个用例全部 passed, exit 0
# 上游 stabtest（非用例制，受控观察）
timeout 100 ./stabtest  # 40 轮 Test#0..#39, ERROR DETECTED=0
# 上游原生 CMake
cmake && make -j1 && make install  # 全部 exit 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| include/readerwriterqueue/*.h | 3 个头文件 | header-only 包内容（无二进制产物） |

## 注意事项

- 上游 unittests 二进制结束时会等待 ENTER（stdin 关闭时直接退出，不影响自动化 exit code）。
- stabtest 为无限循环压测，自动化验证必须使用 timeout 有界运行，以"无 ERROR DETECTED"判定通过。
- 1.0.6 → 1.0.7 上游差异：CMake 安装目标新增 CPack 配置与 `readerwriterqueueConfigVersion.cmake` 的 ARCH_INDEPENDENT；头文件 API 无破坏性变化，配方结构可直接沿用 1.0.6。
---
**编译结束**: 2026-09-04
**最终状态**: built
