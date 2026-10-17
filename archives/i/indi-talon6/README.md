# indi-talon6

## 软件描述
indi-talon6 是 INDI 生态中面向 **Talon6 天文台滑动屋顶（Roll Off Roof）控制器** 的驱动，编译为可执行文件 `indi_talon6`（类 `Talon6 : public INDI::Dome`）。Talon6 是用于远程天文台自动化的屋顶控制/安全系统，本驱动提供开（unpark）/关（park）/中止、绝对位置同步与状态读取等能力。

## 功能概述
- **屋顶控制**：`INDI::Dome` 契约的 open/close/abort/park/unpark
- **绝对位置**：按 ticks 同步屋顶绝对位置、支持 Go To 位置
- **安全条件**：Safety Conditions 与状态读取（Version 1.0 起）
- **固件版本**：读取设备固件版本（Version 0.2 起）
- **连接方式**：走 INDI 自带串口连接插件（`connectionplugins/connectionserial.h`）

## OHOS 适配

### 构建方式
- **CMake 源码构建**：源码取自 **indi-3rdparty 单体仓库**（驱动位于 `indi-talon6/` 子目录），pin 到 commit `945fbe12…`（与制品仓 `libindi 2.2.2.1` 同代）
- **必须保留整棵仓库树**：子目录 `CMakeLists.txt` 会把 `../cmake_modules` 追加进 `CMAKE_MODULE_PATH`（`include(CMakeCommon)`、`find_package(INDI)` 都依赖它）
- **只构建本驱动**：`cmake.configure(build_script_folder="indi-talon6")`，单体仓内其余驱动不参与

### 关键攻坚点
1. **仓内 `FindINDI.cmake` 走 `INDI_ROOT` 提示**：`generate()` 里把依赖包的 `package_folder` 注入 `INDI_ROOT`，使 finder 命中预构建 libindi（不依赖系统安装）
2. **Nova 没有 finder/config**：上游与 libnova 包都不提供 Nova 的 CMake config，而本驱动 `find_package(Nova REQUIRED)` —— 在本包 generators 目录内**生成私有 `NovaConfig.cmake`**（路径全部取自 libnova cpp_info 的绝对路径，R49 私有前缀），并用 `Nova_DIR` 指向它
3. **libnova 头目录需显式注入**：indi 头链 `indidome.h → libastro.h → <libnova/utility.h>`，而上游 CMakeLists 只用 `${NOVA_LIBRARIES}` 链接、不把 `NOVA_INCLUDE_DIRS` 加进 include 路径 → 用 `tc.extra_cflags/extra_cxxflags` 注入 `-I<nova_inc>`（与 libindi 配方注入 fftw 头的做法一致，R33 合规）
4. **`INDI_DATA_DIR` 会被 `find_path` 定成依赖包的绝对路径**：`FindINDI.cmake` 的 `find_path(INDI_DATA_DIR … share/indi)` 在 `INDI_ROOT`（= libindi 包）下找到了数据目录，导致 `install(FILES … DESTINATION ${INDI_DATA_DIR})` 把驱动 XML **写进 libindi 的包目录** → 在 toolchain 预置 `INDI_DATA_DIR = share/indi`（相对路径）修正
5. **DT_NEEDED 需含 `libindiclient`**：`find_package(INDI REQUIRED)` 不带组件时默认组件为 `driver + align`，DT_NEEDED 只记 `libindidriver`/`libindiAlignmentDriver`，而它们从 libindiclient 引入的 `tty_write_string` 等符号会令 musl loader 解析失败 → 补丁请求 `client` 组件（同 indi-aok 的同类修法）
6. **`package_info()` 需注入运行期搜索路径**：libindi 以静态优先发布，Conan 不会把它的 `lib` 放进运行环境，而驱动动态链接 libindi 的 `.so` —— 故 `prepend_path("LD_LIBRARY_PATH", …)`，否则消费者无法加载驱动

### 与 Linux 的差异
- 无源码级差异（INDI 驱动本身跨平台）；差异集中在**打包与运行环境**：Nova finder 需自造、libindi 的 `.so` 搜索路径需显式注入
- 本适配沙箱对 OHOS 共享对象/未签名 ELF 的加载受限，消费者校验会把这部分记为 SKIP

## 依赖关系
- **构建/运行期**：`libindi/2.2.2.1`、`libnova/0.16`（均已合入制品仓）
- 上游 Debian 打包声明的 `zlib1g-dev` 驱动源码并未直接使用；`cmake/cdbs/debhelper` 属 Debian 打包工具，由 Conan/CMake 替代

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 2.0-20221222160901 | built | 2026-10-07 | indi-3rdparty 单体仓驱动子目录范式（复用 indi-aok 同快照做法） |

## 参考资料
- 上游仓库: https://github.com/indilib/indi-3rdparty
- Talon6 产品页: http://observatoriosspag.es/Whats_TALON6.htm
