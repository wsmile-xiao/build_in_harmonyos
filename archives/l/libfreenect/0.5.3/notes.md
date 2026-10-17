# libfreenect 0.5.3 适配笔记

## 基本信息
- 上游: https://github.com/OpenKinect/libfreenect  (tag v0.5.3)
- 许可证: Apache-2.0 OR GPL-2.0
- 构建系统: CMake (cmake_minimum_required 2.6)
- 硬依赖: libusb-1.0 (本仓库 libusb/1.0.27)

## 上游构建系统分析
- 主库: `add_library(freenect SHARED ...)` + `freenectstatic STATIC`（同名 `libfreenect.so/.a`）
- 同步包装: `wrappers/c_sync` → `libfreenect_sync.so/.a`（链接 freenect + pthread）
- 示例: `examples/`（camtest/wavrecord 仅需 freenect；其余 glview/regview 等需 GLUT+OpenGL）
- fakenect: 模拟 USB 库，非必需
- 头文件安装到 `include/libfreenect/`

## 依赖对接（关键）
上游 `cmake_modules/Findlibusb-1.0.cmake` 用 `find_path`/`find_library` 写死
`/usr/include`、`/usr/lib`，且文件顶部 `if(LIBUSB_1_LIBRARIES AND LIBUSB_1_INCLUDE_DIRS)`
命中复数 cache 变量即短路返回。因此配方 `generate()` 直接把 conan libusb 包的
include 目录与库文件路径写入 `LIBUSB_1_INCLUDE_DIRS` / `LIBUSB_1_LIBRARIES`，
绕过硬编码路径，不打源码补丁。

## 平台适配决策
- E092: `CMAKE_SYSTEM_NAME=Linux`（CMake 不认识 OHOS，需 UNIX 才走 install 规则）
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 2.6 与 CMake 4.x 兼容）
- `BIG_ENDIAN=FALSE`（跳过 test_big_endian 交叉 try_run）
- 关闭 BUILD_EXAMPLES / BUILD_FAKENECT（无 GLUT/OpenGL、无需 mock）
- BUILD_REDIST_PACKAGE=ON（只装 fwfetcher.py，不运行 python 烧录固件）
- OHOS 共享库走 `binary-sign-tool` 签名（同 libusb/airspyhf）

## 上游测试清点 (R51)
上游无 `tests/` 目录、无 ctest 注册、无 `make check` 目标；examples 为示例程序，
需物理 Kinect + 显示环境。结论：上游无可运行自动化测试套件。
本仓库以 test_package 真实调用 `freenect_init/freenect_num_devices/freenect_shutdown`
作为消费者侧 smoke 验证。

## 真机验证结果（2026-09-23，10.62.178.77）
- `conan create` 通过：包 `352df8be…`，产物 `libfreenect.so/.a`、
  `libfreenect_sync.so/.a`、`pkgconfig/`、头文件 `include/libfreenect/` 齐全。
- test_package 实跑 `./test_freenect`：`freenect_init() rc=-99`（无 Kinect/无 USB 枚举，
  预期），输出 `LINK-OK (device absent)`。
- 真机用 profile **`ohos-aarch64-fixed`**（含 `os.version=6.0`、
  `tools.build:compiler_executables`、`tools.cmake:cmake_program`）；
  普通 `ohos-aarch64` 会报 `settings.os.version value not defined`。
- 编译限并发 `-c tools.build:jobs=1`（真机仅剩 ~600MB 空闲内存，8 并发会 OOM）。

### 真机踩到并修复的问题
1. **HMDFS 不支持符号链接**（避坑指南 §15）：上游给 .so 设了
   VERSION/SOVERSION，CMake 建 `libfreenect.so.0.5.3→.so.0.5→.so` 软链报
   `Permission denied`。配方 `source()` 用 `replace_in_file` 去掉
   `src/CMakeLists.txt` 与 `wrappers/c_sync/CMakeLists.txt` 的 VERSION/SOVERSION，
   产扁平 `libfreenect.so`/`libfreenect_sync.so`。
2. 非交互 SSH 不加载 PATH，需 `export PATH=/data/service/hnp/bin:$HOME/usr/local/bin:$PATH`，
   `TMPDIR=$HOME/tmp`（/tmp 只读）。

## 已知限制 / 下一步
1. OHOS 沙箱 libusb 无法访问 `/sys/bus/usb/devices`（SELinux errno=13），
   无物理 Kinect 时 `freenect_init` 返回 -99；这是平台/硬件限制，非编译问题。
   真机/真实硬件上再验证设备枚举与数据流。
2. 远程 W0：`libusb/1.0.27` 已在本机 conan 缓存命中（profile 匹配），
   远程 `conan download … -r=ohpcd --only-recipe` 可在 CI 侧确认。
3. 真机 conan create 已通过；下一步走 shadow CI / 提 PR（标题
   `feat(libfreenect): 0.5.3 编译完成`）。
