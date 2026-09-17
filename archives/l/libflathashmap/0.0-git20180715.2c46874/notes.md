# libflathashmap 0.0-git20180715.2c46874 适配笔记

## 基本信息

- 上游仓库：https://github.com/skarupke/flat_hash_map
- 上游提交：`2c4687431f978f02a3780e24b8b701d22aa32d9c`（2018-07-15）
- 官方源码归档：GitHub 固定上游提交 `2c4687431f978f02a3780e24b8b701d22aa32d9c`
- 源码 SHA-256：`606aef45bb69d2fd8247b872919dc01607fe4477df28d6e0b4e686b1b6651980`（三次独立下载校验一致）
- 源码类型：header-only C++14 库，共 3 个公开头文件
- 许可证：BSL-1.0（许可证声明内嵌于每个上游头文件）
- 构建依赖：无
- 运行依赖：无

## 上游测试清点

对官方源码归档执行 `ci/tools/extract_upstream_tests.sh`，并人工复核完整文件清单。归档仅包含 `flat_hash_map.hpp`、`bytell_hash_map.hpp`、`unordered_map.hpp`，没有 `test/`、`tests/`、示例测试、构建脚本或测试入口，因此上游正式测试总数为 0。

## OHOS 适配

配方使用 Conan 2 header-library 模式直接安装三个头文件，并导出 CMakeDeps 目标 `libflathashmap::libflathashmap`。包 ID 与 OS、架构和编译器无关，但消费者仍以 OHOS/aarch64、clang 15、libc++ 配置编译和运行。

补丁 `0001-bytell_hash_map.hpp.patch` 为 `bytell_hash_map.hpp` 增加其实际使用的标准头 `<limits>`。这消除了对 libc++ 传递包含的依赖，使该公开头文件能够被独立包含；补丁不含平台宏，也不改变容器行为。

## 测试范围

消费者测试注册并运行 4 个独立 CTest 用例，共 37 个显式断言：

1. `test_flat_hash_map`：`flat_hash_map` 和 `flat_hash_set` 的插入、查找、删除、复制、移动、保留容量与迭代。
2. `test_bytell_hash_map`：`bytell_hash_map` 和 `bytell_hash_set` 的同类核心操作，同时验证头文件可独立包含。
3. `test_unordered_map`：`unordered_map` 和 `unordered_set` 的链式桶实现及核心容器语义。
4. `test_ohos`：由 Conan 目标设置强制要求 `os=OHOS` 与 `arch=armv8`，验证 64 位、小端 ABI，并对 `flat_hash_map` 执行 1024 项插入、查询和删除；非原生 Linux 宿主通过 QEMU 执行，并要求 `QEMU_LD_PREFIX` 指向包含 `lib/ld-musl-aarch64.so.1` 的 aarch64 运行时根目录。

## 验证命令

```bash
source ../docs/environment/activate.sh
python3 scripts/ohc-run.py conan-verify libflathashmap 0.0-git20180715.2c46874
CI_PACKAGES=archives/l/libflathashmap/0.0-git20180715.2c46874 zsh ci/conan/build_and_test.sh
python3 scripts/ohc-run.py review libflathashmap 0.0-git20180715.2c46874
python3 scripts/ohc-run.py graph validate
```

## 验证结果

- 官方源码完整测试清点：0/0（上游未提供测试）
- 新增消费者测试：4/4 通过
- 显式断言：37/37 通过
- HarmonyOS 专项测试：1/1 通过
- Conan 配方、SHA256、补丁应用、安装产物及消费者 CMake 目标：全部通过

---

**编译结束**: 2026-09-14 10:04
**最终状态**: built
