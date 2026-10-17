# libusbsio 2.1.13 OHOS 适配笔记

## 上游与等价性证据链（审核答辩材料）

任务指定的上游 `https://github.com/Intronics/libusbsio`（tag v2.1.13）在 GitHub 上**已删除**
（HTTP 404；`api.github.com/users/Intronics` 账号仍存在但公开仓库数为 0）。
NXP 官网下载页当前仅提供 Rev 2.2.1（2026-06-25）且需 NXP 账号登录（Azure B2C）。
PyPI `libusbsio` 2.1.13（NXP 官方 Michal Hanak 发布，2024-10-14）的 sdist/whl 仅含
Python 绑定与**预编译**二进制，无 C 源码。

### 等价性判定（为什么 monwarez/libusbsio@8577280 == 2.1.13 的 C 库）

1. **版本演进链**（strings 提取自 PyPI whl 内嵌官方产物）：

   | PyPI 包版本 | linux_x86_64/libusbsio.so | Win x64/libusbsio.dll |
   |---|---|---|
   | 2.1.10 / 2.1.11 | NXP LIBUSBSIO **v2.1c**（2022-01/02 构建） | v2.1b |
   | 2.1.12 | v2.1c | v2.1d |
   | 2.1.13 | **v2.1c** | v2.1e（Oct 2024） |

   NXP 的包版本号（2.1.x）是 **Python wrapper 版本**；内嵌 C 库独立用 v2.1a-e 字母修订。
   Linux 平台的 C 库在 2.1.10→2.1.13 间**从未变更**（v2.1c），只有 Windows DLL 更新到 v2.1e。

2. **字节级证据**：PyPI 2.1.13 whl 与 2.1.11 内嵌的 Linux so **逐字节相同**（MD5 一致）：
   - linux_x86_64: `dd144d618c11a627fb163c89a5a7becb`
   - linux_aarch64: `91fcf0e7b5469aaaba6cd99e60bb4fdc`
   （本适配目标即 Linux/OHOS aarch64——正是未变更的平台）

3. **源码对应**：monwarez/libusbsio@8577280（2023-05-27 推送的公开快照，fork:false，Nitrokey
   社区为 Nitrokey 3 固件更新维护）的 `src/lpcusbsio.c` 中
   `g_LibVersion = "NXP LIBUSBSIO v2.1c ..."` —— 与 2.1.13 whl Linux so 的版本串完全一致。

4. **API 面对应**：快照源码头文件声明的 `LPCUSBSIO_*`（11 函数）+ `HIDAPI_*`（8 函数）与
   2.1.13 whl so 的导出符号集完全一致（nm -D 对照）。

5. **Windows v2.1e 差异声明**：2.1.13 独有的 v2.1e 修订只存在于 Windows DLL，其源码仅在
   已删除的 GitHub 仓库与 NXP 登录墙后。本适配目标平台（HarmonyOS PC aarch64）对应
   Linux 产物线，不受影响。

结论：以 monwarez/libusbsio@8577280 作为 2.1.13（Linux/OHOS 产物线）的**等价源**，
conandata.yml 指向其 GitHub codeload 归档（pinned commit + sha256）。

## 构建适配

- **上游构建系统**：纯 makefile（Linux 段：`CC -Iinclude -Isrc/hid_api/hidapi -fPIC -c
  src/lpcusbsio.c src/hid_api/linux/hid.c` → ar/共享链接）。配方内直接复现该编译
  （2 个编译单元），编译器取自 profile conf `tools.build:compiler_executables`（R33）。
- **依赖修正**：上游 makefile 的 Linux 段用 `pkg-config libudev`。OHOS 无 systemd
  libudev → 使用本仓库制品仓 `libudev-zero/1.0.4`（drop-in 静态 libudev，API 面完整
  覆盖 hid.c 所需的 15 个枚举相关函数）。**任务原始背景中的"前置 libusb"不成立**：
  Linux hidraw 后端不链接 libusb（makefile 注释里的 libusb 提示面向 FreeBSD 段）；
  官方预编译 so 的 NEEDED 仅为 libudev.so.1 + libc.so.6。
- **零补丁**：OHOS SDK sysroot 自带 `linux/hidraw.h`（bionic kernel header，含
  HIDIOCGRDESC/HIDIOCSFEATURE 等全部所需 ioctl），交叉编译零警告通过。
- **R26 判定**：OHOS 系统无同名 libusbsio 系统库，非 system-name 库 → 默认共享
  （`libusbsio.so`，带 `-Wl,-soname` 保证 L5 DT_SONAME 门禁）。
- 产物：`libusbsio.so` + 头文件 `lpcusbsio.h`/`lpcusbsio_protocol.h`；cpp_info.libs=["usbsio"]。

## 上游测试与 CI 环境限制申报（clancyxie 口径：能跑的跑，跑不了的逐项定性）

### 上游测试资产与注册数口径

上游测试资产三层：
1. **python/test/ unittest 套件**——文件级 def test_ 计数 **44**（test_00_lib 12 +
   test_10_spi 8 + test_20_i2c 15 + test_30_gpio 9）；test_20_i2c.py 的 Echo 用例被
   TestI2C_XFER/_WriteRead/_WriteRead_MultipartRead/_WriteRead_MultipartWrite 子类
   继承重定义，`unittest discover` 按类展开后实际注册 **52**（本机实测 `Ran 52
   tests`）。申报 N=52（unittest 实际注册口径），44/52 推导关系在 PR 正文写明。
2. **test/testapp/ 交互式 C 硬件测试程序**（5 菜单项，无自动化注册）——不计入 N。
3. C 库本体无 ctest/add_test 注册。

### 52 用例的执行方式与逐项定性

上游 Python 套件 52 用例**全部**在 setUp 里 `LIBUSBSIO()` 构造 → `ctypes.CDLL()`
dlopen 加载 so。**OHOS 应用域 SELinux 对 dlopen 未签名 so 返回 EACCES**（本机五
种加载方式实测全拒：全路径/相对路径/soname 短名/LD_PRELOAD/memfd+proc/self/fd；
而链接期 NEEDED 加载正常——test 二进制真跑全过）。处置：52 用例断言逻辑**逐组
移植为链接期绑定的 C driver**（test_package/test_upstream_suite.c，上游源码零
改动），真跑结果：

- **16 PASS**（可移植断言）：test_00_lib 的 8 个无设备路径用例（枚举真走
  libudev-zero 全路径返回 0、版本串前缀 "NXP LIBUSBSIO v2"、Open 无设备返回
  NULL 干净失败、错误态契约）+ SPI_OpenOptions bitfield 编码（3 断言）+
  I2C NormalTransferOptions 位编码（3 断言）+ GPIO GetNumGPIOPorts 符号契约
- **36 SKIP**（设备绑定断言，逐项带上游 Python 用例 ID 输出在 CI 日志）：
  GetNum{I2C,SPI,GPIO}Ports/GetMaxDataSize 的 n>0 断言（4，需 open device）+
  SPI 7（探针 SPI 口 + SIOTEST 回环固件）+ I2C 14（探针 I2C echo 目标）+
  GPIO 8（探针 GPIO 引脚）
- 0 FAIL

**设备依赖本质**：NXP LPC-Link2/MCU-Link 是 USB-HID 物理桥接探针（VID 0x1fc9），
SPI/I2C/GPIO 传输断言需探针上运行 SIOTEST 回环固件——CI 沙箱（OHOS buildbot
worker）与本机均无此硬件。

### testapp（C 交互程序）执行情况

OHOS aarch64 交叉编译通过 + 真机运行无设备路径（枚举 → "No USBSIO bridge device
found" → 干净退出 exit 0）。

### 鸿蒙特有测试（test_libusbsio.c，6 断言）

1. 公共 API 面可链接可调用 2. GetVersion 版本串契约 v2.1c 3-4. GetNumPorts
（LPCLink2/MCULink）无设备环境真走枚举路径 5. GetLastError 错误态契约
6. Error(NULL) 宽字符错误文本

## 踩坑记录

- Intronics/libusbsio 上游消失是本任务最大坑：任务 URL 404，NXP 官网下架旧版。
  等价源判定必须做产物级（MD5）而不是仓库级判断——PyPI whl 内嵌 so 是官方产物
  指纹。
- GitHub 匿名 API 搜索对 fork 不敏感（monwarez 是 fork:false 的手动快照，搜 "libusbsio
  fork" 结果为 0），找等价源时需用 SWH origin search 等间接渠道。
- HMDFS 大小写折叠：主仓库同时存在 `libXext/` 与 `libxext/` 两个目录（历史遗留），
  任何 worktree 的 git status 都会报这两个目录的幽灵 M——提交时只 add 白名单目录
  即可隔离，勿全局 git add -A。
