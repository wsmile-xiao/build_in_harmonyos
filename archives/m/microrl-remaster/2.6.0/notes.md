# microrl-remaster 2.6.0 适配笔记

## 编译环境
- 构建系统: pure Makefile（无顶层构建系统；上游仅 examples/ 提供 Makefile 构建演示程序）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4（OHOS armv8 工具链，/data/service/hnp/bin/clang）
- 状态: published（conan-verify G0-G5 全部 PASS）

## 编译步骤

库构建（无 configure，直接编译单一 C 源）：
```bash
clang -c -Wall -O2 -std=gnu99 -I./src/include/microrl -DMICRORL_IGNORE_USER_CONFIGS -fPIC src/microrl/microrl.c -o libmicrorl.o
llvm-ar rcs libmicrorl.a libmicrorl.o
```

上游 Unix 演示程序构建（examples/Makefile 原生即指向该结构；CC 覆写为 clang）：
```bash
make -C examples CC=clang
# -> examples/microrl_test
```

Conan 验证（OHOS armv8 交叉 profile）：
```bash
python3 scripts/ohc-run.py conan-verify microrl-remaster 2.6.0
# -> G1/G2/G3/G4/L2/L4/L5 全 PASS，conan create 成功，test_package 2/2 通过
```

## 上游测试完整枚举台账（R51 申报表）

### 枚举范围与结论

上游 microrl-remaster 2.6.0 **没有独立测试框架**：无 ctest/Meson/autotools 测试注册，
无 TEST_CASE 断言宏，无 `make check`/`make test` 目标，无 tests/ 目录、无 pytest/脚本、
无 fixture/基准目录。源码中 grep 不到任何 `assert`/`TEST`/`check` 测试断言入口。

| 枚举项 | 类型 | 是否独立上游用例 | 结论 / 原因 |
|--------|------|------------------|-------------|
| `src/microrl/microrl.c` | 库源码 | 否 | 库实现，非测试 |
| `src/include/microrl/microrl.h` | 框架头文件 | 否 | 公开 API 头，非测试 |
| `src/include/microrl/microrl_config.h` | 框架头文件 | 否 | 配置头，非测试 |
| `src/include/microrl/microrl_user_config_template.h` | 模板头 | 否 | 用户配置模板，非测试 |
| `examples/example.c` | 嵌入式演示主程序 | 否 | 平台无关演示（AVR/Linux/STM32 共用），非断言测试 |
| `examples/unix_misc/unix_misc.c` | Linux PC 平台实现 | 否 | 演示配套（termios/stdio），非测试 |
| `examples/avr_misc/avr_misc.c` | AVR 平台实现 | 否 | 演示配套，非测试，无法在 PC 运行 |
| `examples/esp8266_example/` | ESP8266 PlatformIO 演示 | 否 | 演示工程，非测试，PC 无对应目标 |
| `examples/stm32_example/` | STM32CubeIDE 演示工程 | 否 | 演示工程（含 ST 库文件），非测试，PC 无对应目标 |
| `examples/Makefile` | 构建目标 microrl_test | 否（构建目标） | 仅演示可执行，无断言输出 |
| `examples/Makefile.avr` | avr-gcc 构建目标 | 否 | AVR 专用，PC 不可跑 |
| `examples/microrl_user_config.h` | 演示用配置 | 否 | 演示配置，非测试 |

### 独立上游用例统计（双口径）

- **source_declared_total = 0**：官方 tag 源码中无可复制枚举的独立 TEST_CASE/断言测试声明。
- **configured_executable_total = 0**：当前 OHOS 配置下无“测试用例”可执行实例化
  （examples/microrl_test 是演示程序，非断言测试；且不在 Conan 配方构建范围内）。
- **executed_passed_total = 0**：无独立上游测试用例可执行。
- **失败数 = 0；未运行/未实例化 = 0**（无测试声明的自然结果）。

全量通过率：因全量发现数为 0，通过率不适用；单独标注判定口径——
microrl 上游以“交互式演示程序”验证功能（R51 允许：上游确无测试须附清点证据，
本台账即清点证据：全树文件逐项分类如上）。

### 上游演示程序构建与冒烟运行（补充证据，非测试计数）

```bash
make -C examples CC=clang        # 退出码 0，产物 examples/microrl_test
printf 'version microrl\nhelp\n' | timeout 6 examples/microrl_test
# 输出 "> version microrl"（演示正确处理命令并回显版本），进程为 while(1) 交互循环，
# 无输入后由 timeout 终止（退出 124），属演示程序预期行为，非测试失败。
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create source() BadZipFile | 官方 codeload URL 以 tag 名 (v2.6.0) 结尾，Conan get() 无法从 URL 后缀推断归档格式 | source() 显式 `filename="microrl-remaster-2.6.0.tar.gz"` |
| 2 | build() 找不到 microrl.h | conan build 上下文中 cwd=源码根，include 路径误写 `-I../src/...` | 改为 `-I./src/include/microrl` |
| 3 | 消费者编译缺 microrl_user_config.h | microrl_config.h 无条件 `#include "microrl_user_config.h"`（除非 MICRORL_IGNORE_USER_CONFIGS） | package() 把上游模板复制为 `include/microrl/microrl_user_config.h` 默认空配置 |
| 4 | init-build 源码根误判为 examples/ | 上游顶层无构建文件，仅 examples/ 有 Makefile，init-build 根目录探测偏离 | 按官方 tarball 真实布局（src/、examples/、img/）校验并重建 work 目录 |

## 源码修改

无补丁（R8：patches/ 为空）。配方层处理全部在 conanfile.py 内完成：
- source() 显式 filename（URL 后缀 = tag 名，非归档扩展名）
- build() 直接 clang 编译 + llvm-ar 归档（上游无 configure/CMake）
- package() 打包 microrl.h/microrl_config.h/microrl_user_config.h(模板默认) + libmicrorl.{a,so} + LICENSE

## 依赖版本

- 无第三方依赖（纯 C 标准库）。W0 预检通过：无依赖需要发布检查。

## 验证结果

```bash
# 1) 库编译
clang -c ... src/microrl/microrl.c      # 退出码 0
llvm-ar rcs libmicrorl.a libmicrorl.o    # 退出码 0
# 2) 上游演示构建+冒烟
make -C examples CC=clang               # 退出码 0
examples/microrl_test                   # 交互演示运行正常
# 3) Conan 全门禁
ohc-run.py conan-verify microrl-remaster 2.6.0   # G0-G5 全 PASS
#    conan create 内 test_package: 2/2 tests passed（test_microrl_remaster + test_microrl_remaster_ohos）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 纯 Makefile 库配方（clang 编译 + llvm-ar 归档，静态默认） |
| conandata.yml | 官方 codeload URL + SHA-256 5d76ff200551ab3fa48bf466021cd5748dd2c5ae58c49b5e49ba4b8a34d858b6 |
| test_package/ | 消费者测试（真实调用 microrl_init/microrl_processing_input/microrl_get_version） |

## 注意事项

- 库为嵌入式风格纯 C（Apache-2.0），无平台相关代码（无 termios/OS 条件编译），OHOS 无需任何源码补丁。
- MICRORL_IGNORE_USER_CONFIGS 仅配方内部编译使用；对外打包提供默认 microrl_user_config.h（即上游模板），下游可自行覆盖。
- 非 CLI 库（package_info 仅 cpp_info.libs，无 bindirs/可执行产物），不创建 commands.json。
---

**编译结束**: 2026-09-23 04:10
**最终状态**: published
