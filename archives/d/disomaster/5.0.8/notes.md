# disomaster 5.0.8 适配笔记

## 编译环境
- 构建系统: CMake（上游为 qmake，改为 CMake）
- 编译器: clang / clang++
- 状态: prepared（等待 OHOS 真机验证）

## Scope

disomaster 是 deepin 开发的 Qt 封装库，提供光盘操作功能（刻录、擦除、检查、ISO 读写等）。

- 上游仓库: https://github.com/linuxdeepin/disomaster
- 版本: 5.0.8
- 许可证: GPL-3.0-or-later
- 上游构建系统: qmake
- 上游依赖: Qt5 Core, libisoburn (>= 1.2.6)

上游 `libdisomaster/disomaster.cpp` 直接调用 libisoburn C API（`isoburn_*`, `burn_*` 系列函数）。
鸿蒙平台上只有 xorriso 可执行文件（来自 PR !831），没有 libisoburn 开发头文件，
因此需要用 QProcess 调用 xorriso 命令行替代。

## Dependency reuse

### xorriso 预构建包

- 来源 PR: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/831
- 包名: libisoburn-1.5.8.pl02-ohos-aarch64
- URL: https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/libisoburn-1.5.8.pl02-ohos-aarch64.tar.gz
- SHA256: 3b3308d0d2830cb6ccf688e4a8a182477c93c132c65b1dece9f062f9df7876ee
- 内容: `bin/xorriso`（静态链接可执行文件，无开发头文件）

xorriso 预构建包安装在 disomaster 包的 `bin/` 目录中。通过 `runenv_info` 设置：
- `PATH`: 包含 `bin/` 目录
- `DISOMASTER_XORRISO`: 指向 xorriso 可执行文件路径

DISOMaster 运行时优先从 `DISOMASTER_XORRISO` 环境变量获取 xorriso 路径，
其次从 PATH 查找 `xorriso`。

## Implementation

### QProcess CLI 后端

补丁 `0001-xorriso-cli-backend.patch` 创建新文件 `libdisomaster/disomaster_cli.cpp`，
完全替代上游的 `libdisomaster/disomaster.cpp`（不再编译原文件）。

#### xorriso 命令映射

| DISOMaster 方法 | xorriso 命令 |
|----------------|-------------|
| `acquireDevice(dev)` | `xorriso -dev <dev> -end` |
| `getDeviceProperty()` | `xorriso -dev <dev> -toc -list_speeds -end` |
| `commit(opts, speed, volId)` | `xorriso -dev <dev> -speed <N>k -volid <name> -overwrite off -joliet on/off -rockridge on/off -map <src> <dst> ... -close on/off -commit -end` |
| `erase()` | `xorriso -outdev <dev> -blank as_needed -end` |
| `checkmedia()` | `xorriso -dev <dev> -check_media -end` |
| `dumpISO(path)` | `xorriso -outdev <dev> -check_media use=outdev data_to=<path> -end` |
| `writeISO(path, speed)` | `xorriso -as cdrecord -v dev=<dev> blank=as_needed speed=<N>k <path>` |

#### 输出解析

- `Media current: <type>` -> MediaType 枚举（CD-ROM, CD-R, CD-RW, DVD+R 等）
- `Media status : is blank` -> formatted = true
- `Media summary: N sessions, N data blocks, Nk data, Nm free` -> datablocks, data, avail
- `Volume id : '<name>'` -> volid
- `Write speed : Nk Nx` -> writespeed 列表
- `Media region : N N <-|slow|0>` -> checkmedia 质量统计（good/slow/bad 比例）
- `N% fifo|done` -> 进度信号 jobStatusChanged(Running, N)
- `N of N MB written` -> 进度信号
- `Nx.` -> 当前速度 getCurrentSpeed()

#### 信号发射

- 操作开始: `jobStatusChanged(Running, 0)`
- 进度更新: `jobStatusChanged(Running, percentage)`
- 操作完成: `jobStatusChanged(Finished, 100)` 或 `jobStatusChanged(Failed, 0)`

## Build

### CMake 构建系统

上游使用 qmake（`disomaster.pro` / `libdisomaster.pro`），改为自定义 CMakeLists.txt。

构建流程：
1. 下载上游源码 + xorriso 预构建包（OHOS）
2. 应用补丁创建 `disomaster_cli.cpp`
3. 使用 qt5-qtbase 的 `moc` 工具从 `disomaster.h` 生成 `moc_disomaster.cpp`
4. CMake 配置 + 编译 `disomaster_cli.cpp` + `moc_disomaster.cpp`
5. 链接 Qt5::Core，OHOS 平台添加 `-stdlib=libc++`

关键 CMake 变量（由 CMakeToolchain cache variables 传入）：
- `DISOMASTER_SOURCE_DIR`: 源码目录路径
- `DISOMASTER_MOC_SOURCE`: 生成的 moc 源码路径

### moc 生成

`disomaster.h` 包含 `Q_OBJECT`、`Q_ENUM(JobStatus)` 和信号声明，需要 moc 生成元对象代码。

conanfile.py 的 `build()` 方法中：
1. 从 `qt5-qtbase` 依赖获取 `bin/moc` 路径
2. 运行 `moc -I<qt5_include> -I<source>/libdisomaster disomaster.h -o moc_disomaster.cpp`
3. 生成的 `moc_disomaster.cpp` 路径通过 `DISOMASTER_MOC_SOURCE` 传入 CMake

## Tests

### 上游测试

上游 `tests/testdisomaster.cpp` 包含 6 个测试，全部需要物理光驱：

| 测试 | 描述 | 需要 |
|------|------|------|
| test_getDevice | 获取光驱并检查介质属性 | DISOMASTERTEST_DEVICE + 光驱 |
| test_writeFiles | 暂存文件并刻录到光盘 | DISOMASTERTEST_DEVICE + 可写介质 |
| test_erase | 擦除可重写光盘 | DISOMASTERTEST_DEVICE + 可重写介质 |
| test_isoWrite | 写入 ISO 镜像到光盘 | DISOMASTERTEST_DEVICE + 可写介质 |
| test_checkMedia | 读取介质区域并计算质量比例 | DISOMASTERTEST_DEVICE + 可读介质 |
| test_dumpISO | 转储光盘到 ISO 镜像 | DISOMASTERTEST_DEVICE + 可读介质 |

CI 环境无法执行上游测试（无物理光驱，且部分测试会修改光盘内容）。

### test_package

`test_package/` 包含 3 个文件：

1. **test.cpp** - 34 个非破坏性断言的消费者测试
   - 构造/析构、初始状态、暂存文件、设备属性缓存
   - 未获取设备时拒绝操作
   - 使用 fake_xorriso 执行所有光盘操作
   - JobStatus 信号验证、checkmedia 质量比例、getCurrentSpeed

2. **fake_xorriso.c** - 模拟 xorriso 命令行行为的 C 程序
   - 验证 DISOMaster 传递的参数列表格式
   - 输出模拟的 xorriso 响应（介质属性、进度、质量等）
   - 不执行任何真实硬件操作

3. **conanfile.py** - 运行 xorriso -version 和 test_disomaster

## Known limitations

- xorriso 预构建包为静态链接可执行文件，无开发头文件，无法直接链接 libisoburn
- 使用 QProcess 调用 xorriso CLI 替代 libisoburn C API，性能略低于直接调用
- 进度信号基于 xorriso 输出解析，实时性取决于 xorriso 输出频率
- 上游 6 个测试均需要物理光驱，CI 环境无法执行
- `EjectDisc` 选项尚未实现（上游也标记为 not used yet）
- `JolietAndRockRidge` 选项映射为同时启用 Joliet 和 Rock Ridge（上游标记为 not used yet）
