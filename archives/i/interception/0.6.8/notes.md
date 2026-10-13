# interception-tools 0.6.8 适配笔记(HarmonyOS PC / aarch64)

## 基本信息

- 构建系统: **CMake**(上游单 CMakeLists.txt,4 个可执行目标)
- 上游版本: 0.6.8(GitLab v0.6.8 tag,interception 生态核心)
- 源 URL: `https://gitlab.com/interception/linux/tools/-/archive/v0.6.8/tools-v0.6.8.tar.gz`
  sha256 `84ced1c10bef7f00660704685c651c4241096cc9848c31f5a04f166e1450949d`(实测)
- 包类型: **application**(bin/udevmon、bin/intercept、bin/uinput)
- 补丁: **1 个** — `patches/0001-cmake-ohos-deps.patch`(仅 CMakeLists.txt 移植)
- 依赖(main 已发布组合): `libevdev/1.13.7`、`eudev/3.2.14`(提供 libudev)、
  `yaml-cpp/0.9.0`

## CMakeLists 移植补丁(0001-cmake-ohos-deps.patch)

上游交叉构建的三大阻断,全部为构建系统层,零业务源码改动:

1. **`cmake_minimum_required(VERSION 3.0)`** — 现代 CMake 对 <3.5 声明直接
   报错,升 3.10;
2. **udev/yaml-cpp 裸名链接** — 上游 `target_link_libraries(udevmon evdev
   udev yaml-cpp)` 用裸 `-l` 名,conan 依赖库不在默认链接搜索路径。libevdev
   上游本就 `pkg_check_modules(LIBEVDEV REQUIRED libevdev)`,补丁把 udev、
   yaml-cpp 统一成 `pkg_check_modules(UDEV/YAMLCPP REQUIRED …)`,链接改
   `${UDEV_LIBRARIES}`/`${YAMLCPP_LIBRARIES}`,与 libevdev 同法;
3. **mux 目标裁剪** — mux(多路复用器)需要 Boost.Interprocess;仓库
   boost 1.85/1.91 配方组件集(filesystem/iostreams/program_options/regex/
   thread)不含 interprocess,且 interprocess 无独立包。mux 是可选拓展
   (udevmon 单独即为核心守护),补丁移除 mux 的
   add_executable/链接/install 与 find_package(Boost REQUIRED)。

## 依赖解析

| 依赖 | 提供方 | 解析方式 |
|------|--------|----------|
| libevdev | libevdev/1.13.7 | pkg_check_modules(上游内置)+ PkgConfigDeps |
| libudev | eudev/3.2.14 | pkg_check_modules(补丁统一)+ PkgConfigDeps |
| yaml-cpp | yaml-cpp/0.9.0 | pkg_check_modules(补丁统一)+ PkgConfigDeps |

PkgConfigDeps 为三个依赖生成 .pc;configure 的 PKG_CONFIG_PATH 由
conanrun 环境注入。

## 平台构建要点

| 要点 | 原因 |
|------|------|
| `TMPDIR` 指到可写目录 | HarmonyOS `/tmp` 是只读 erofs(E002) |
| OHOS 下 ELF 重签名 | 按 libinput 同法对 bin/ 下 ELF 重签(保险) |
| `make -j`(默认并行) | 标准 CMake 构建,无顺序依赖 |

## 验证记录(本地,未交叉编译)

- 源码包 sha256 为 GitLab 归档下载实测;
- 补丁对 pristine 树 `git diff` 生成,`git apply --check` 通过(生成即对齐);
- 源码 musl 风险 grep 干净:无 program_invocation_short_name/rindex/
  strcasestr/get_current_dir_name;
- 实际构建与测试由 CI `conan create` 完成(本 PR 提交时待跑,结果见 PR)。

## test_package(L0c 真实执行测试)

eudev 3.2.14 同款 shell 脚本模式(`test_interception.sh`,共 6 项断言):

1. 定位 `bin/udevmon`、`bin/intercept`、`bin/uinput` 三个工具;
2. 各工具 `-h` 成功退出——三工具均 `print_usage(stdout) + EXIT_SUCCESS`
   (源码 605/29/450 行),动态依赖 libevdev/libudev/yaml-cpp 在运行时
   全部解析才算通过。

## 运行前提(OHOS 集成阶段确认,非构建问题)

- 内核 `CONFIG_INPUT`/uinput 模块、`/dev/input/event*` 设备节点;
- eudev(udevd)运行;
- udevmon 需 YAML 配置文件定义设备组合(用户态配置,不随包分发)。

## 交付物

| 路径 | 说明 |
|------|------|
| `bin/udevmon` | udev 事件监听守护 |
| `bin/intercept` | evdev 设备捕获工具 |
| `bin/uinput` | 虚拟设备注入工具 |
| `licenses/LICENSE.md` | GPL-3.0-or-later |
