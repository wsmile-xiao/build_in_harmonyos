# str 1.0.0 适配笔记

## 编译环境
- 构建系统：header-only（Conan package_type=header-library）
- 编译日期：2026-09-04
- 编译器：clang/clang++
- 目标：HarmonyOS PC arm64

## 上游测试用例核验
- 上游默认入口：`test/Makefile` 的 `run`，仅编译并运行 `test/main.c`。
- 实际测试函数：4 个（`test_std`、`test_float`、`test_m`、`test_json`）。
- 实际断言：188 个：43（标准格式化）+ 128（浮点，42 个 `TEST_FLOAT` 宏调用各含 3 个断言，另有 2 个显式断言）+ 7（自定义格式）+ 10（JSON）。
- `footprint.c`、`main.ino`、`syscalls.c` 是嵌入式 footprint/Arduino/系统调用辅助源码，不属于默认 `make run` 测试用例。

## 适配后测试
- `test_package/test_str.c`：6 个断言，覆盖 `xsnprintf` 格式化及 `json_get_num`、`json_get_str`。
- 适配未修改上游测试；仅新增 Conan 消费者 smoke test。
- 由于该包是单头文件库，无独立编译产物；Conan create 负责验证头文件和消费者编译。

## 依赖版本
- 运行时/编译依赖：无。
- W0 `conan download str/1.0.0 -r=ohpcd --only-recipe` 未能完成，Conan 返回 `system acceleration policy not enabled`；这是当前设备制品仓访问工具策略限制，不是“依赖缺失”结论。该包本身无依赖。

## 验证结果
- 上游：`CC=clang make clean run`，4 个测试函数、188 个断言全部通过（输出 `SUCCESS`）。默认 `make clean run` 因设备未安装 `cc` 失败，已使用设备现有 `/data/service/hnp/bin/clang` 完成等价验证；原因属于工具未装，非上游功能失败。
- Conan：`conan create ... -s:h os.version=6.0 -s:b os.version=6.0 --build=missing` 成功，配方打包 `str.h` 与 `LICENSE`，test_package 编译并运行成功（6/6 断言通过）。
- W0：`conan download str/1.0.0 -r=ohpcd --only-recipe` 返回 `system acceleration policy not enabled`，记录为设备制品仓访问策略限制；本包无编译/运行依赖。
