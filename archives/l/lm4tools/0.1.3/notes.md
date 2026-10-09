# lm4tools 0.1.3 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，非 autotools；无 configure）
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos，OHOS 原生)
- 状态: built

## 编译步骤

```bash
# 源码: https://github.com/utzig/lm4tools/archive/refs/tags/v0.1.3.tar.gz（经镜像下载到 .downloads/）
# 依赖: conan install --requires=libusb/1.0.27 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
P=/storage/Users/currentUser/.conan2/p/libus04e54d4f229a5/p   # libusb 包目录

# lm4flash：Makefile 走 pkg-config 路径，OHOS 下可用（pkg-config 由 profile 提供时）；
# 本机显式传 CFLAGS/LDFLAGS 规避 pkg-config 缺失：
cd lm4flash && make CC=clang CFLAGS="-Wall -O2 -I$P/include/libusb-1.0" LDFLAGS="-L$P/lib -lusb-1.0"

# lmicdi：Makefile 仅识别 Darwin/FreeBSD/Linux，OHOS 上 uname=HarmonyOS 三个分支全不命中，
# libusb 变量为空 → 必须显式传 LIBUSB_CFLAGS/LIBUSB_LIBDIR/LIBUSB_LIBS：
cd lmicdiusb && make CC=clang LIBUSB_CFLAGS="-I$P/include/libusb-1.0" LIBUSB_LIBDIR="$P/lib" LIBUSB_LIBS="-lusb-1.0"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lmicdiusb/Makefile 在 OHOS 上 libusb 变量全空，链接 undefined reference | `ifeq ($(shell uname),Linux)` 不匹配 HarmonyOS | 命令行显式传 LIBUSB_CFLAGS/LIBUSB_LIBDIR/LIBUSB_LIBS，不改源码 |
| 2 | lm4flash 首次构建报 clang Error 127 | CI profile 的 tools.build:compiler_executables 指向 /data/service/hnp/bin/clang，本机不存在 | 改用本机 /storage/Users/currentUser/usr/local/bin/clang |
| 3 | conan 包内 libusb-1.0.pc 的 prefix=/usr/local，直接 PKG_CONFIG_PATH 会指向错误路径 | libusb 配方生成 .pc 未重定位 | 配方中不用运行时 .pc，改为 conan 依赖路径直接拼接（见 conanfile.py） |
| 4 | GitHub 直连下载超时 | 网络环境 | tarball 经 ghfast.top 镜像下载到 .downloads/；**conandata.yml 保持官方 URL + 真实 sha256**（file:// 本地路径会泄漏环境且 CI 必败，DRAFT-aghermann-1.1.2 明令禁止），本地离线复验改用 conan download cache 种子：全局缓存以 sha256 为文件名，把 tarball 复制为 `~/.conan2/d/xx/e8064...1627` 即可让 conan get() 命中而不触网 |
| 5 | conan-verify G2 首跑报 `NameError: name 'lmicdiusb_dir' is not defined` | 配方 build() 中变量名为 lmicdi_dir，cwd 引用误写 lmicdiusb_dir | 修正为 lmicdi_dir，重跑 G2 PASS（证据：reports/conan-create.log） |
| 6 | conan-verify G1 首跑缺 export_sources()/补丁调用检查项 | G1 模板要求 CLI 包也声明空补丁管道 | 配方补 export_conandata_patches() + apply_conandata_patches()（conandata 无 patches 段时为 no-op） |

## 上游测试清点（R51 证据）

上游 **无任何测试**：
- 三个 Makefile（顶层、lm4flash/、lmicdiusb/）的全部目标仅为 `all/clean/debug/install/release/lmicdi`，**无 check/test 目标**；`make check` 报 `No rule to make target 'check'`。
- 源码树内 `find . -iname "*test*" -iname "*CTest*"` 无任何测试文件；无 configure/autotools/meson 测试钩子。
- Debian/Homebrew/Nix 等发行版打包也仅做安装检查，无测试注册（lm4flash 仅 `-V` 冒烟）。

因此"上游正式测试"为 **0 项**，以本笔记清点记录为准；适配侧重 test_package + HarmonyOS 专项测试补齐。

## 依赖版本

- libusb/1.0.27（conan 制品仓 ohpcd，OHOS AArch64）
- 无其他依赖（lm4flash 纯 C + libusb；lmicdi 纯 C + libusb + POSIX socket）

## 验证结果

### 手动模式 B 构建（2026-09-29，本机 HarmonyOS aarch64 原生）

```bash
$ file lm4flash lmicdi
lm4flash: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
lmicdi:   ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ lm4flash -V
LM4Flash version 0.1.3 - Flasher for Stellaris Launchpad ICDI boards   # exit 0
$ lm4flash -h   # 打印 usage，exit 0
$ lm4flash      # 无参数 → usage + EXIT_FAILURE（exit 1）
$ lmicdi        # 无 ICDI 设备：libusb_init 或设备枚举后断言退出（exit 134）——需真实 USB 设备，CI 无法验证
```

### conan-verify（R51 证据，2026-09-29T12:34:01）

```
G1 配方完整性 PASS（name/version/source/build/package/package_info/
   export_sources/补丁调用/conandata/test_package/MANIFEST 全过）
G2 conan create PASS → lm4tools/0.1.3@ohpcd/stable:
   38577a0deab15c351da8cbee20fd103a393e622b#400d7ac143cc6ed1b30353eeac155daf
   Packaged 2 files: lm4flash, lmicdi（日志 reports/conan-create.log）
G3 系统同名库隔离 PASS（无 lib/ 目录，纯可执行包）
G4 产物完整性 PASS
L2/L4/L5：无 cache 路径场景跳过（本机 conan-verify 驱动形态）
test_package 实跑（conan create 内）：
   Layer 1 ohos_abi_check.py ×2 二进制：A1-A9 全过（18/18）
     lm4flash sha256=cbcd406a7c4486dd...  lmicdi sha256=4fc731beea2fa625...
   Layer 2 test_lm4tools.sh：F1-F13 全过（13/13）
     LM4TOOLS_FUNCTIONAL={"discovered": 13, "passed": 13, "failed": 0}
```

**硬件依赖边界（不伪造）**：F6/F8/F9/F11-F13 断言的是"无设备时干净失败"，
真实刷写/调试成功路径需 Stellaris LaunchPad ICDI 板卡（USB VID:PID
1cbe:00fd），本环境与 CI 均无此硬件，不做任何"硬件通过"声明。

## 交付物

| 文件 | 说明 |
|------|------|
| lm4flash | 固件烧写 CLI（bin/lm4flash） |
| lmicdi | GDB-USB 调试桥 CLI（bin/lmicdi） |

## 路径判定：A（无知识库扩展）

对 libusb、USB 设备访问、系统接口与 CLI 构建过程的差异逐一排查，结论是**全部命中既有知识条目，无真正通用的新方案**，故走路径 A，不做 graph add：

| 差异点 | 分析 | 既有覆盖 |
|--------|------|----------|
| lmicdiusb Makefile 按 uname 三分支（Linux/Darwin/FreeBSD）选 libusb 链接规则，OHOS 全不命中 | 与 pev/libpe 的 PLATFORM_OS 落空同族：命令行变量覆盖（本案直接注入 LIBUSB_CFLAGS/LIBUSB_LIBDIR/LIBUSB_LIBS，比覆盖平台变量更贴近目标） | DRAFT-E640-harmonyos-uname-makefile-platform-os |
| conan 包内 libusb-1.0.pc 的 prefix=/usr/local 未重定位，PKG_CONFIG_PATH 指向错误路径 | .pc 未重定位家族的常规形态；解法也是常规的"不用 .pc，改用 cpp_info 直接拼路径" | E006/E028 一族 |
| USB 设备访问本身（/dev/bus/usb、hotplug、usbfs） | 运行期行为完全由已发布的 libusb/1.0.27 承载，lm4tools 无自有系统调用封装，无新差异面 | libusb 包自身知识 |
| CLI 构建过程 | 纯 make 变量注入 + PREFIX 安装，无 configure/cmake 新形态 | 无（常规操作） |

## 注意事项

- **硬件依赖边界**：lm4flash 的烧写/校验、lmicdi 的设备枚举与 JTAG 通信均需真实 Stellaris LaunchPad（USB VID:PID 1cbe:00fd），测试环境无设备，只能验证"可执行文件/链接/参数解析"，不得伪造硬件通过结果。
- lmicdiusb 上游含 macOS 专属 `-framework` 分支与 lm4f120icdi Xcode 工程，OHOS 适配只构建 lm4flash + lmicdi 两个 CLI。
- lmicdi 的 `main()` 在 libusb_init 失败时走 `ASSERT(rc == 0)` 直接 abort——这是上游行为，保留不改。
