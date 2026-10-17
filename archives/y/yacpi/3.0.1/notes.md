# YACPI 3.0.1 HarmonyOS 适配笔记

## 上游测试清点

上游源码包共含 10 个文件，没有 `tests/` 目录；Makefile 只有 `all`、`dist`、`options`、`install`、`uninstall`、`clean`、`love` 目标，不提供 `check` 或 `test`。因此本包如实声明没有上游自动测试，并由 `test_package` 对已打包程序执行消费者测试。

## 依赖

- `libacpi/0.2`：上游 ACPI 数据读取库；制品仓提供 OHOS aarch64 二进制。
- `ncurses/6.5`：终端 UI；制品仓提供静态宽字符 ncurses 库。

两项依赖在 `ohpcd` 上以 `conan download` 取得了匹配 HarmonyOS 6.0、aarch64、clang 15 的 recipe 与二进制包。

## 适配内容

- 移除 `scaling_cur_freq` 或 `scaling_max_freq` 不可用时的硬失败路径，分别回退读取 `cpuinfo_cur_freq`、`cpuinfo_max_freq`。
- `check_acpi_support()` 不支持时，跳过 libacpi 设备初始化，继续输出可用 CPU 信息；将 ACPI 状态初始化为不支持，并零初始化共享状态，避免缺少设备时读取未初始化字段。
- 在 Conan 配方中将上游 Makefile 的编译、链接和 strip 命令接入 make 变量，以使用 Conan 提供的 clang、ncursesw 和 libacpi 路径。
- 版本补丁由仓库 `refresh-patch --auto` 自动生成，并在 HarmonyOS 真机上验证可应用。

## HarmonyOS 真机行为

测试设备为 HarmonyOS 6.0，HongMeng Kernel 1.12.0，aarch64，clang 15.0.4。设备没有 `/proc/acpi`、`/sys/bus/acpi` 或 `/sys/firmware/acpi`，也没有电池、热区或风扇 sysfs 项；因此这些传感器数据不可用。设备提供 `/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_cur_freq` 和 `cpuinfo_max_freq`，测试会实际读取这两个节点并核对 YACPI 输出的 MHz 值。

## 验证结果

- HarmonyOS 6.0 aarch64 真机 `conan create`：通过；使用 OHOS Clang 15.0.4，依赖为 `libacpi/0.2` 和 `ncurses/6.5`。
- Conan `test_package`：4/4 通过。实际运行已签名的包内 `yacpi`；核对 `-v` 版本、无 `scaling_*` 时 CPU 频率回退与设备 `cpuinfo_min/max_freq` 范围、缺少 ACPI 时仍能输出 CPU 频率。
- 仓库 aarch64 本地 CI `ci/conan/build_and_test.sh archives/y/yacpi/3.0.1`：退出码 0，1/1 包通过；G0、L0、L1、L5 均通过，R34 反向验证确认消费者测试确实依赖包内二进制。
- `scripts/ohc-run.py graph validate`：退出码 0，全部检查通过；报告的既有知识图谱警告不阻断校验。

CI 有非阻断提示：L2 探测 `--version`/`--help`，而上游只提供 `-v`（已由消费者测试验证）；L4 的正则把补丁上下文中未修改的安全 `fgets` 误命中为 `gets`。编译器也报告上游 `yacpi.c:326` 的 `!ac->ac_state == P_AC` 逻辑括号警告，本移植未改动该上游逻辑。预下载器未找到设备上的 `curl`，随后 Conan 自身成功下载并校验上游源码，构建与测试不受影响。
