# libuinputplus 0.1.4 适配笔记

## 基本信息
- **软件名**: libuinputplus（上游库名 libuInputPlus / CMake 目标 uInputPlus）
- **版本**: 0.1.4（上游 tag v0.1.4，commit 41865c0945b4d9d2f6bfc826e2804761a21a7d37）
- **构建系统**: CMake
- **上游仓库**: https://github.com/YukiWorkshop/libuInputPlus （已归档 read-only，MIT）
- **描述**: Linux uinput 内核接口的 C++11 封装，用于从用户态创建虚拟输入设备

## W0 依赖结论
| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| linux/uinput.h | - | OHOS SDK sysroot | UAPI 头，内部包含 linux/input.h、linux/input-event-codes.h |
| libc（open/ioctl/close/write/usleep） | - | musl | 系统调用，musl 全部支持 |

- 无第三方 Conan 依赖，无缺依赖、无拆分需求。
- 已在本机 DevEco Studio SDK（API 26, 26.0.0.105）sysroot 验证
  `usr/include/linux/uinput.h` 存在，且包含源码用到的全部定义：
  `struct uinput_setup`、`struct uinput_abs_setup`、`UI_DEV_SETUP`、
  `UI_ABS_SETUP`、`UI_SET_EVBIT/KEYBIT/RELBIT/ABSBIT/PROPBIT`、`UI_DEV_CREATE`。
- libevdev（1.13.3/1.13.7 已归档）证明 sysroot 的 linux/input.h、
  input-event-codes.h 在 CI worker 工具链上可用，同一结论可迁移。

## 适配要点

### 1. 无源码补丁
所有 Linux API（open/ioctl/close/write/usleep + UAPI 头）在 OHOS musl
sysroot 中齐备，源码零修改，`patches: {}`。

### 2. CMake 4.x 兼容（知识条目 E103）
上游 `cmake_minimum_required(VERSION 3.0)`，CMake ≥ 4 拒绝配置 < 3.5
的项目。按仓库既有惯例（actor-framework/aida/airspy 等）在 generate()
注入 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`，不打补丁。

### 3. v0.1.4 tag 的实际构建布局（修正记录）
⚠️ 教训：W1 首次分析误用了 master 分支的 CMakeLists（简化版）；v0.1.4 tag
的 CMakeLists 才是权威，真机 r3 暴露差异后修正：
- 显式 `add_library(uInputPlus SHARED ...)` + `add_library(uInputPlus_Static
  STATIC ...)`（同输出名），SOVERSION 0——包内同时产出 libuInputPlus.so 与
  libuInputPlus.a（HMDFS 上 soversion 符号链接链坍缩为单个 .so，-luInputPlus 正常）
- 头文件安装到 `include/uInputPlus/` 子目录，`uInputPlus.pc` 的 Cflags 指向
  该子目录（消费端平铺 `#include "uInput.hpp"`）——配方
  `cpp_info.includedirs = ["include/uInputPlus"]` 与之一致
- shared/fPIC 选项仅为符合仓库配方惯例保留；上游硬编码双目标，CI 只构建
  默认 shared=True 路径

### 4. 消费者集成
上游不导出 CMake targets（无 install(EXPORT)）。通过 package_info
属性提供 `cmake_file_name: uInputPlus` / `cmake_target_name:
uInputPlus::uInputPlus`，CMakeDeps 会生成包装 config，消费者
`find_package(uInputPlus)` + 链接 `uInputPlus::uInputPlus` 即可。
头文件安装到 include/ 根（uInput.hpp / uInputSetup.hpp / CommonIncludes.hpp）。

## 上游测试清点（R51 三步法）
1. **清点**：v0.1.4 源码树（12 个文件）无 tests/ 目录；CMakeLists.txt
   无 `add_test`/`enable_testing`；无 ctest/pytest 注册；.gitlab-ci.yml
   仅做编译检查。唯一可执行程序是根目录 `test.cpp`——交互式 demo，
   构造 `uInput(setup)` 会立即 `open("/dev/uinput")`，构建机无设备节点
   权限，无法作为 CI 测试运行。**上游确无测试套件**。
2. **可运行环境**：test_package 的回调模式测试无需任何设备权限，
   可在 CI/真机确定性地运行。
3. **回填**：test_package 40 个断言（断言数与 MANIFEST.yml 一致），
   结果见下方 Test evidence。r4 真机实测曾暴露 1 处测试自身错误预期
   （uInputSetup 默认构造后 Keys 为空，DefaultKeys 仅是带参构造的默认
   实参），已按真实 API 行为修正。

## test_package 设计
利用 `uInput::Init(callback, userp)` 回调模式：`Emit()` 改为调用回调而非
写设备文件，使 SendKey/SendKeyPress/RelativeMove/RelativeWheel/
AbsolutePosition 的完整事件序列可在无 /dev/uinput 环境下断言：
- extern 常量集（DefaultEventTypes/Keys/Rels/Abss）链接与内容
- uInputDeviceInfo / uInputAbsSetup / uInputSetup 构造与引用成员
- 事件序列与 SYN_REPORT 语义、零轴跳过行为

## 本机验证（W4，2026-09-27）
- `sha256sum` 复核源码归档与 conandata.yml 一致：
  `a537e156...97458` ✓
- conanfile.py / test_package/conanfile.py 通过 `py_compile` 语法检查 ✓
- conandata.yml / manifest.yaml / MANIFEST.yml 通过 YAML 解析 ✓
- 用本机 DevEco Studio OHOS clang（`--target=aarch64-linux-ohos` +
  sysroot API26）对库三源文件 + test_uinputplus.cpp 做交叉编译验证 ✓
  （编译细节与命令见提交说明；运行验证留待真机）
- 目录边界：改动仅 `archives/l/libuinputplus/` ✓

## Test evidence
- Local cross-compile (OHOS clang 15 + API26 sysroot): library sources and
  consumer test compiled and linked successfully.
- 上游测试套件：上游无测试（清点证据见上，R51）。
- test_package（40 断言，回调模式，无设备依赖）：40/40 通过。
- HarmonyOS PC shadow CI（隔离 job，2026-09-27）：passed。
  - exit code 0；排队等待 15 秒（全局锁）
  - L0_RESULT=pass（含 L0d/R34、L0j/R37 首版无冲突）
  - L1_RESULT=pass（test_package executed；L1e 破坏性反验证确认测试真依赖本包）
  - L2_RESULT=skip: no bin/ dir（纯库，正常）
  - L4_RESULT=pass: no patches；L5_RESULT=pass: lib/ has content
- 上游测试 100% 通过口径：上游无测试套件（0 项），故无"跳过/降级"项。
- Generated CI reports are not committed.

## Shadow CI 迭代记录（每轮必填）
| 轮次 | exit | 失败点 | 报错原文（摘要） | 根因 | 解法 |
|------|------|--------|------------------|------|------|
| r1 | 1 | L0 门禁 | `L0d: test() method has no self.run() call — likely a stub` | test() 仅用 cmake.test()，静态门禁要求 self.run | test() 中直接 self.run 执行测试二进制（env=conanrun） |
| r2 | 1 | conan create | `cmake: inaccessible or not found`（127） | 隔离 job repo 里的 CI profile 是陈旧副本，缺 `[buildenv] PATH=+(path)/data/service/hnp/bin` 注入 | 将 shadow 沙箱内 profile 刷新为当前 main 版本（沙箱操作，不动 PR 内容） |
| r3 | 1 | test_package 编译 | `fatal error: 'uInput.hpp' file not found` | W1 误用 master 分支 CMakeLists；v0.1.4 tag 实际将头文件装到 include/uInputPlus/ 子目录 | `cpp_info.includedirs = ["include/uInputPlus"]`，并修正 notes/manifest 中的布局描述 |
| r4 | 1 | test_package 运行 | `FAIL: uInputSetup defaults to DefaultKeys`（38/39 通过） | 测试自身预期错误：默认构造的 Keys 为空，DefaultKeys 只是带参构造的默认实参 | 按真实 API 行为修正断言（40 断言） |
| r5 | 0 | — | 全部门禁通过 | — | — |

## 编译命令（真机/shadow CI 参考）
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

真机隔离 job（单包排队，重任务错峰）：
```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job libuinputplus-0.1.4-<timestamp> \
  --package archives/l/libuinputplus/0.1.4 \
  --repo-source <existing-repo>
sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"
```

R40 备注：uinput 属外设/系统底层类库。编译通过 ≠ 适配完成——真机上
`/dev/uinput` 是否存在、普通用户是否有权限打开、UI_SET_* ioctl 是否被
内核接受，需在真机空闲窗口用回调模式之外的 demo（test.cpp）或最小
ioctl 探针验证；该验证依赖设备环境，不在本机前置范围内。
