# c-periphery 2.5.0 — HarmonyOS PC 适配笔记

## 版本核验

- 任务板任务 #5157 `feat/c-periphery-2.5.0`；上游 `vsergeev/c-periphery` 确认存在
  tag `v2.5.0`（`git ls-remote --tags` 核验），版本正确，无占位版本问题。
- 同名 open 任务 `feat/c-periphery-1.0.0`（任务板 #4017）为机器生成占位版本，
  上游无 v1.0.0 之后直接接 v1.0.1~v1.0.3、v1.1.x 等序列——以本归档 v2.5.0 为准。

## 源码信息

- 上游: https://github.com/vsergeev/c-periphery
- 官方 URL: https://github.com/vsergeev/c-periphery/archive/refs/tags/v2.5.0.tar.gz
- SHA256: `065d304d289a691bf2f685f3d80ff9dc26ba69bb2d463b2f279397908f5ec9ae`
- 许可证: MIT

## 构建系统

- CMake >=3.19（首选，conanfile.py 采用）；CMakeLists 自带完整 install 规则：
  库 → lib/、头文件 → include/periphery/、pkg-config → lib/pkgconfig/、CMake export config。
- CMake 自动探测 `linux/gpio.h`（check_source_compiles / check_symbol_exists）：
  v2 → v1 → sysfs 回退。OHOS sysroot 的探测结果以设备端 conan create 日志为准
  （无该头文件时仅回退 sysfs GPIO，不阻塞构建）。
- `git describe` 取 commit id 带 `ERROR_QUIET`，tarball 无 .git 时 COMMIT_ID 为空串，
  不影响构建。

## 上游测试

- `tests/*.c` 共 8 个 C 测试程序（serial/gpio/gpio_sysfs/led/pwm/spi/i2c/mmio），
  全部需要真实外设硬件；CMake 未注册 CTest（`ctest -N` 为 0），只有自定义 `tests` 目标。
- 配方策略：`BUILD_TESTS=ON` + `cmake --build --target tests` 完成编译链接（编译级证据，
  字面命令进日志）；不执行、不伪造通过。HMBS_UPSTREAM_TEST_RESULT：
  discovered=8 / executed=0 / skipped=8，discovered 数字取自源码树枚举。
- 消费者验证：test_package/test_periphery.c，4 断言（periphery_version=="v2.5.0"、
  serial_open 无效路径失败、serial_errno 置位、serial_errmsg 非空），无硬件可复现。
- open 失败后不调用 serial_close（fd 未初始化，上游无此用法保障）。

## OHOS 适配点

1. 零外部依赖、纯 C99（`-std=gnu99 -pedantic`），无平台分支代码，预期无需补丁。
2. `-lpthread`：musl 将线程集成进 libc，链接 stub 即可（设备端验证确认）。
3. 库类型产物（.a/.so），无可执行文件 → 无 commands.json（R38）。
4. R26：periphery 非系统同名库，shared 选项默认 OFF（静态），不污染 /lib、/lib64。

## 设备验证（已完成 2026-08-30）

- 设备：HarmonyOS PC（aarch64），conan 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`。
- 命令（与 CI 同源，提交 7bb38fc96e）：
  `conan create archives/c/c-periphery/2.5.0 -pr:h=<绝对路径 profile> -pr:b=<绝对路径 profile> --build=missing --build="c-periphery/*"`
- 结果：**通过**。日志 `.ci_logs/conan_build_c-periphery_2.5.0.log`，包 ID
  `4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`，产物 libperiphery.a + include/periphery/*.h
  + lib/cmake/periphery/ + pkgconfig，全日志 0 ERROR。
- 上游 tests 目标：8 个测试程序（serial/gpio/gpio_sysfs/led/pwm/spi/i2c/mmio）全部
  编译链接通过（`Built target test_*`）。
- test_package 消费者测试：4 断言全 PASS（periphery_version==v2.5.0；serial_open
  无效路径失败 code=2 errno 2 ENOENT；serial_errno 置位；serial_errmsg 非空）。
- HMBS 证据（日志行 204）：
  `HMBS_UPSTREAM_TEST_RESULT={"status": "skipped", "framework": "c-periphery-upstream-tests", "command": "cmake --build <build> --target tests", "discovered": 8, "executed": 0, "passed": 0, "failed": 0, "skipped": 8}`
- **linux/gpio.h 探测结果**：`HAVE_GPIO_CDEV_V2 - Failed`（v1 同样不可用）→ OHOS 内核
  uapi 头不含 gpio cdev 接口，c-periphery 以 **legacy sysfs GPIO** 模式构建（预期回退路径，
  不阻塞）。设备无 GPIO cdev 支持属内核配置差异，已如实记录。
- 适配修复记录：首轮 test_package 失败于 CMakeDeps 目标名（cmake_file_name 设了
  自定义 `periphery` 但 target 默认用包名）→ 按 c-ares 先例将 file_name/target_name
  统一为 `c-periphery`/`c-periphery::c-periphery`（提交 7bb38fc96e）。
- 注意：conan create 相对路径 `-pr:h=ci/conan/profiles/ohos-aarch64` 不会按 CWD 解析
  profile 文件（落到 default profile，缺 os.version 直接 Invalid）——必须用绝对路径，
  CI 脚本用的正是绝对路径。
