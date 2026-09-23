# openhmd 0.3.0.1 适配笔记（HarmonyOS PC / OHOS aarch64）

## 1. 概览

| 项 | 值 |
|---|---|
| 三方库 | OpenHMD（`openhmd`） |
| 适配版本 | `0.3.0.1`（上游 tag `0.3.0`，适配改进版，源码零改动） |
| 上游仓库 | https://github.com/OpenHMD/OpenHMD |
| 构建系统 | CMake（≥3.15 语法；上游声明 `cmake_minimum_required(VERSION 3.1)`） |
| 依赖 | `hidapi/0.14.0`（OHOS 预编译包已发布，libusb 后端） |
| 产物 | `libopenhmd.a` + `include/openhmd.h`（静态，非系统同名库，保持上游默认） |
| 补丁 | 0（无源码补丁） |
| 平台代码 | `src/platform-posix.c`（pthread / clock_gettime）OHOS 原生可用 |

## 2. 为什么是 0.3.0.1（而不是 0.3.0）

`archives/o/openhmd/0.3.0/` 已存在（PR #8409 已合入 main），制品仓也已发布
`openhmd/0.3.0`。按 R37 + CI 门禁 L0j：同版本 + 配方有改动会被直接 fail。因此本次
改进以 **0.3.0.1** 版本号发布，源码仍取上游 tag 0.3.0（sha256 与 0.3.0 完全一致）。

## 3. 本次改进（相对 0.3.0）

### 3.1 上游测试：从「手工复刻」变为「原样执行」

- 0.3.0 的 `test_package/test.c` 是**手工重声明 openhmd 内部符号 + 复刻内部断言**
  （`ovec3f_*` / `oquatf_*` 内部数学 API 的非导出符号），并不编译、不运行上游测试源；
  这种方式既不消费打包产物，也无法随上游实现演进。
- 0.3.0.1 在 `conanfile.py` 的 `build()` 末尾，用**独立小 CMake 工程原样编译并运行
  上游 `tests/unittests/` 的全部 11 个用例**（`main.c` / `vec.c` / `quat.c` /
  `highlevel.c` 四文件零修改），被测对象是本次刚构建出的 `libopenhmd.a`；
  结果以 `HMBS_UPSTREAM_TEST_RESULT=<json>` 上报，未全绿即 `build()` 失败。
  该做法符合 `docs/ADAPTATION_GUIDE.md` 适配检查清单「build() 末尾执行上游测试」。

  上游 `tests/unittests` 是 autotools 目标（`tests/Makefile.am: bin_PROGRAMS = unittests`），
  不在上游 CMake 构建图内；本配方用一个内联生成的小 `CMakeLists.txt` 复现其编译关系
  （include 路径 `include/` + `src/`，链接 openhmd 库 + hidapi + m + pthread，
  与静态目标一致地定义 `OHMD_STATIC`），**测试源码本身不做任何修改**。

  覆盖率护栏：配方内声明 `UPSTREAM_TEST_CASES = 11`，实测用例数不符时显式失败，
  避免上游测试集变更后静默漏测。

### 3.2 test_package：从「内部符号复刻」变为「公共 API 消费者测试」

`test_package/test.c` 全部只包含公共头文件 `<openhmd.h>`，真实打开 dummy 驱动的
HMD 设备并读取/写入属性，7 个消费者用例：

| # | 用例 | 覆盖的公共 API |
|---|---|---|
| 1 | `test_ctx_create_probe_destroy` | `ohmd_ctx_create` / `ohmd_ctx_probe` / `ohmd_ctx_get_error` / `ohmd_ctx_destroy` |
| 2 | `test_device_list_metadata` | `ohmd_list_geti`（`OHMD_VENDOR`/`OHMD_PRODUCT`/`OHMD_DEVICE_CLASS`/`OHMD_DEVICE_FLAGS`）、`ohmd_list_gets` |
| 3 | `test_device_open_close` | `ohmd_list_open_device_s`（按设备类打开）、`ohmd_list_open_device`、可重开性、`ohmd_close_device` |
| 4 | `test_device_properties` | `ohmd_device_getf`/`geti`：屏幕尺寸/分辨率、镜片间距、IPD、投影 zNear/zFar、左右眼 FOV 与宽高比 |
| 5 | `test_device_control_metadata` | `OHMD_CONTROL_COUNT` / `OHMD_CONTROLS_HINTS` / `OHMD_CONTROLS_TYPES` / `OHMD_CONTROLS_STATE` |
| 6 | `test_shader_source_strings` | `ohmd_gets`（`OHMD_GLSL_DISTORTION_{VERT,FRAG}_SRC`、GLES 变体） |
| 7 | `test_device_settings_and_pose_roundtrip` | `ohmd_device_settings_create/seti/destroy`、`ohmd_device_setf`/`getf` 姿态回环、`ohmd_ctx_update` |

用例 7 的姿态回环（含 dummy 驱动的 180° 旋转修正语义）与用例 3 的
`ohmd_list_open_device_s` 覆盖了 0.3.0 未触达的公共 API 面。

### 3.3 鸿蒙特有测试：OHOS 装载器与 hidapi 依赖闭包契约（本轮新增）

`test_package/test.c` 末条 `test_ohos_loader_dependency_contract`，共 4 组断言，
全部确定性、无需 HMD 硬件：

| 组 | 断言 | 为什么是鸿蒙特有 |
|---|---|---|
| 1 | `dlopen("libhidapi-libusb.so", RTLD_NOW)` 成功 | OHOS 制品仓动态库只发布**不带版本号**的 `.so`（实测 `libhidapi-libusb.so` 在、`.so.0` 不在），与 glibc 发行版约定不同；`RTLD_NOW` 立即绑定全部符号，等价于一次性验证 `hidapi → libusb-1.0` 整条传递依赖闭包可解析 |
| 2 | openhmd 各 hidapi 后端驱动源码**活动代码**实际引用的 13 个入口 API + 生命周期 `hid_init` 全部 `dlsym` 可解析（14/14） | 驱动在**运行期**才解析 `hid_*` 符号，缺符号时链接期不报错、运行期才 `symbol not found`——本地适配期真实踩过（`libusb_handle_events: symbol not found`） |
| 3 | `dladdr(hid_enumerate)` 返回非空路径且含 `hidapi` | 排除「符号解析成功但落在空壳/错误模块」，确认 OHOS 装载器映射的是制品仓发布的真实实现 |
| 4 | `hid_init()` 可调用且不崩溃，返回受控值（0=libusb 后端可用 / -1=环境无 `/dev/bus/usb` 访问） | OHOS 无 udev/systemd 服务，且 CI 沙箱常无 USB 设备节点——返回值随环境变化，属环境差异而非依赖闭包缺陷，断言按值域接受 |

实测输出：

```
    dlopen(libhidapi-libusb.so, RTLD_NOW) -> ok
    hidapi 入口符号可解析: 14/14
    dladdr(hid_enumerate) -> /…/lib/libhidapi-libusb.so
    hid_init() -> 0（本机 libusb 后端可用；CI 沙箱无 /dev/bus/usb 时为 -1，均属正常）
consumer test: ohos_loader_dependency_contract          ok
```

> **踩坑（CI 实测）**：`hid_init()` 的返回值**与环境相关**——设备上有 `/dev/bus/usb` 访问
> 时返回 0，CI 沙箱内返回 -1（libusb 后端初始化失败）。首版用例断言 `rc == 0`，本机过、
> CI 红（build-51367）。已改为按值域断言 `rc == 0 || rc == -1` 并把语义写进输出，
> 因为该用例要验证的是**依赖闭包在运行期可用**（符号可解析 + 入口可调用），
> 而非宿主是否插着 USB 设备。

计数口径：该用例只在「鸿蒙特有测试」一栏计 1，**不重复计入消费者 7 例**（避免虚增）；
本次合计 = 上游 11 + 消费者 7 + 鸿蒙特有 1 = 19。

## 4. 关键适配点（零补丁的实现方式）

1. **hidapi 依赖注入**：上游 `cmake/FindHIDAPI.cmake` 是 module 模式
   （`find_path`/`find_library`），与 conan `CMakeDeps` 生成的 config 模式包
   （`hidapi-config.cmake`）不互通；上游 `CMakeLists.txt:48` 消费的是
   `${HIDAPI_INCLUDE_DIRS}` / `${HIDAPI_LIBRARIES}`。因此在 `configure` 时直接注入
   四个 cache 变量（`HIDAPI_LIBRARY` / `HIDAPI_LIBRARIES` / `HIDAPI_INCLUDE_DIR` /
   `HIDAPI_INCLUDE_DIRS`），其中单数变量即 `find_*` 的结果变量，令 Find 模块跳过搜索。
2. **头文件布局**：上游驱动源码平铺 `#include <hidapi.h>`，而 conan hidapi 包头文件
   位于 `include/hidapi/hidapi.h`；注入的 include 目录自动探测到嵌套的 `hidapi/` 层。
3. **CMake 策略下限**：上游 `cmake_minimum_required(VERSION 3.1)` 在 CMake 4.x 下被拒，
   用 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 官方兼容开关）传参解决，无需补丁。
4. **示例程序**：`OPENHMD_EXAMPLE_SIMPLE` / `OPENHMD_EXAMPLE_OPENGL` 置为 False
   （示例依赖 SDL/OpenGL，交叉编译环境不构建）。
5. **库类型**：openhmd 非系统同名库，保持上游默认静态（`BUILD_SHARED_LIBS` 由
   `shared` 选项驱动）；上游对静态目标 PUBLIC 加 `-DOHMD_STATIC`，本配方透传该默认。

## 5. 踩坑记录

| 现象 | 根因 | 处置 |
|---|---|---|
| 上游测试二进制启动即 `Error relocating libhidapi-libusb.so: libusb_handle_events: symbol not found` | 测试可执行文件动态链接 hidapi（→libusb），运行时 `LD_LIBRARY_PATH` 只含 hidapi 目录 | `_runtime_libdirs()` 递归收集依赖图（含传递依赖）的 `libdirs`/`bindirs` 注入运行时环境 |
| 消费者测试编译报 `unknown type` 指向注释行 | 注释文本里出现 `ovec3f_*/oquatf_*`，其中 `*/` 提前闭合了块注释 | 改写注释文本，避免出现 `*/` |
| `ohmd_gets(dev, OHMD_GLSL_... )` 编译报「int ↔ 指针不兼容」 | `ohmd_gets` 是**全局字符串** API：`int ohmd_gets(ohmd_string_description, const char**)`，与设备无关；`OHMD_GLSL_*` 属于 `ohmd_string_description` | 改为 `ohmd_gets(OHMD_GLSL_DISTORTION_VERT_SRC, &vert_src)`，并补 GLES 变体 |
| `ohmd_ctx_get_error(ctx) == NULL` 断言失败 | 新建上下文的错误串是空串而非 NULL | 断言放宽为 `err == NULL \|\| err[0] == '\0'` |
| `ipd > 0` 断言失败 | dummy 驱动未显式设置 IPD（设备默认值） | 放宽为 `ipd >= 0`（`lens_sep` 确为 0.0635 保留 `> 0`） |
| `OHMD_JOYSTICK_RIGHT` / `OHMD_GLSL_DISTORTION_VERT_SRC_CODE` 不存在 | 0.3.0 头文件中无这些枚举 | 改为合法范围检查与公共 API 语义检查 |

## 6. 本地复现命令

```bash
git clone --depth 1 --branch 0.3.0 https://github.com/OpenHMD/OpenHMD /tmp/OpenHMD-0.3.0
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64
```

## 7. 限制与说明

- 运行时验证限于 dummy 驱动（无需真实 HMD 硬件）；`hidapi` 后端与各真实驱动
  （Rift/Deepoon/WMR/Vive/NOLO/3Glasses/External）的代码路径在编译期全部参与构建。
- 上游 `tests/unittests` 的 highlevel 用例（打开/关闭设备）即通过 dummy 驱动执行库内
  完整路径（`ohmd_list_open_device*` → 驱动 `open` → `close`）。
- **适配完整性（R40 自查）**：本库属 VR/HMD 外设领域，但上游是平台无关的纯 C 实现
  （`platform-posix.c` 在 OHOS 直接可用），本次为零补丁适配，不存在 stub/`return 0`
  式占位代码；平台相关面（OHOS 装载器命名约定、hidapi → libusb-1.0 依赖闭包解析）
  由 3.3 节鸿蒙专用用例实测覆盖。
- **未覆盖面（需人工确认）**：真实 HMD 硬件（各 `hid_*` 后端）的端到端行为、真机
  权限/udev 替代路径，本环境无对应硬件，只能确认到「符号可解析 + 初始化成功」这一层。
---

**编译结束**: 2026-09-12 14:02
**最终状态**: built
