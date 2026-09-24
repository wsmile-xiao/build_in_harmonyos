# intrusive_shared_ptr 1.13 测试报告

## 结论

HarmonyOS/OHOS AArch64、Clang 15 环境下全部测试通过。

| 测试层级 | 总数 | 通过 | 失败 | 跳过 |
|----------|-----:|-----:|-----:|-----:|
| 上游 doctest 用例 | 110 | 110 | 0 | 0 |
| 上游 doctest 断言 | 1454 | 1454 | 0 | 0 |
| Conan test_package 程序 | 2 | 2 | 0 | 0 |
| test_package 运行时检查 | 18 | 18 | 0 | 0 |

## 上游测试

- 测试目录：`test/`
- 测试源文件：14 个 `.cpp`
- 构建产物：`test-17-headers`、`test-20-headers`（Clang 15 仅支持 17/20 标准，
  上游按编译器特性自动枚举变体）
- C++17 结果：55/55 test cases、727/727 assertions，状态 `SUCCESS`。
- C++20 结果：55/55 test cases、727/727 assertions，状态 `SUCCESS`。
- 合计结果：110/110 test cases、1454/1454 assertions，0 失败、0 跳过。
- 配方分别构建两个官方测试目标，再以绝对路径运行对应可执行文件，避免原生
  `/bin/sh` 不从当前目录查找裸命令名。
- 未修改上游测试源码、注册、断言或预期结果；上游指定的 `doctest/2.5.2`
  由 Conan 测试依赖离线提供（FetchContent source override + FULLY_DISCONNECTED）。

## 消费者测试

- `test_intrusive_shared_ptr` 通过 `find_package(isptr 1.13 CONFIG REQUIRED)` 和
  `isptr::isptr` 消费安装产物，构造、复制、生命周期及弱引用相关 10/10 项检查通过。
- `test_intrusive_shared_ptr_ohos` 编译期限定 `__OHOS__`，验证 AArch64 64 位 ABI、
  无锁 `intptr_t` 原子以及原子 `refcnt_ptr` 的 load、CAS、store 和生命周期，
  8/8 项检查通过。

## 补充验证

- 官方与本地交叉预检两套 Conan profile 均完成配置、构建、安装和运行测试。
- `conan-verify`：G0、G1、G2、G3、G4、L2、L4、L5 全部 PASS。
- W3 本地 CI：总体 100% 通过；L0、L1、L4、L5 通过，header-only 库无二进制库，
  对应制品层检查按规范不适用。
- 最终包仅含 7 个公开头文件、许可证、CMake/pkg-config 元数据、上游测试结果和
  实验性模块源，不含构建缓存或下载源码。
