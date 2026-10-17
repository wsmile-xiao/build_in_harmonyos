# libtypec 0.6.0 适配笔记

## 库简介

libtypec 是用户态访问 Linux USB Type-C / USB Power Delivery 子系统的 C 库，
通过 sysfs (`/sys/class/typec`) 与 debugfs (`/sys/kernel/debug`) 暴露连接器能力、
PDO、连接器状态、Alternate Mode 等。MIT 许可，作者 Rajaram Regupathy。

公开 API（libtypec.h）核心：`libtypec_init()` / `libtypec_exit()`，以及一组
`libtypec_get_*` 查询函数。

## 本轮完成范围（本机前置，未占真机）

- [x] W0 依赖发布检查
- [x] 源码 / 构建系统分析
- [x] Conan 配方 conanfile.py + conandata.yml
- [x] 实质 test_package（非空壳）
- [x] 静态核对：源码 URL/sha256、构建系统识别、依赖列表、测试断言
- [ ] 真机/CI conan create（单包排队，见末尾命令）

## W0 依赖检查

| 依赖 | 用途 | ohpcd 状态 |
|------|------|-----------|
| eudev/3.2.14 | 提供 libudev（`dependency('libudev', required:true)`） | ✅ 已发布（conan download 本地命中） |
| libc/libm/libpthread | 标准 POSIX | OHOS NDK 自带 |

结论：唯一外部依赖 eudev/3.2.14 已在制品仓，无需拆依赖库。

## 构建系统选择

上游 0.6.0 同时提供：
- `meson.build`：顶层只 `library('typec', ...)`，共享库 + 头文件，**不构建 utils**。
- `CMakeLists.txt`：`add_subdirectory(utils)` 额外构建 `lstypec`/`typecstatus`/
  `ucsicontrol`/`usbcview`（`usbcview` 依赖 gtk+-3.0）。

本配方选 **Meson**：
1. 纯库表面，无 bin/ 可执行文件 → 不需要 commands.json（R38 不触发）。
2. 不引入 gtk3。
3. eudev 的 pkg-config 名 `libudev` 与 meson `dependency('libudev')` 直接对接
   （PkgConfigDeps 生成 libudev.pc）。

## 源码 URL 与 sha256（已实测）

- 公开 GitHub `Rajaram-Regupathy/libtypec` 的 tag 最新只到 `libtypec-0.5.1`；
  main 分支 `CMakeLists.txt` 仍为 `0.5.1` 且无 meson.build。`ColinIanKing/libtypec`
  镜像 tag 列表完全相同。即 **0.6.0 未在公开 GitHub 打 tag**。
- 可公开校验的 0.6.0 源码为 Debian 的 orig tarball：
  `https://deb.debian.org/debian/pool/main/libt/libtypec/libtypec_0.6.0.orig.tar.gz`
  - sha256 = `c4f337d142594d50e75ae55e7bb7f28d5cb348a961d468b02b62fb58c4dbf837`
  - 解包后 `meson.build` 声明 `version: '0.6.0'`，与目标版本一致。
  - Debian 策略下 orig tarball 即未修改的上游发布包。
- PR 说明里需就此源 URL 例外（R39/PF7）：无公开 release tag，Debian orig 是唯一
  可固定校验的官方来源。

## 测试策略（R34/R51）

- 上游无自动化测试：全树 meson 无 `test()` 注册。
- 工具 `lstypec`/`typecstatus`/`ucsicontrol` 都直接遍历 `/sys/class/typec`，
  需要真实 Type-C 控制器，OHOS 上不存在该 sysfs 类，不可运行。
- test_package 选 `libtypec_init`：它在探测（缺失的）sysfs 后端 **之前** 就填充
  `session[LIBTYPEC_VERSION_INDEX] = "libtypec 0.6.0"` 及内核/OS 串。测试断言这
  三个串非空且版本串前缀正确——这是不依赖硬件的真实 API 调用，同时验证 .so 被
  OHOS 加载器接受。后端 init 返回负值（无硬件）属预期，不断言其为 0。

## 已知风险 / 待真机确认

1. **内核 UAPI 头缺失风险**：源码 include 了
   `<linux/magic.h>`、`<linux/types.h>`、`<linux/usbdevice_fs.h>`、`<linux/usb/ch9.h>`。
   OHOS NDK 不一定提供后两个 USB UAPI 头。若 conan create 报缺头，按单一职责
   补 `patches/0001-*.patch`（提供缺失结构体/宏的最小 fallback），不在 patch 里用
   `__OHOS__` 空壳 stub（R8）。
2. **运行时**：即使编译/链接通过，libtypec 功能本身需要 Linux typec 子系统；
   本包目标是"编译完成 + 加载/链接 smoke 通过"，不声称运行期功能完整（R40）。
3. ELF 签名：沿用 libdvbv5 的 `_sign_ohos_package_elfs`（llvm-objcopy 去 .codesign +
   binary-sign-tool 自签）。

## 真机构建结果（2026-09-26，设备 frp-tip.com:56267，aarch64 OHOS）

`conan create` 通过，test_package 在真机上运行成功：

```
libtypec OK: version='libtypec 0.6.0' kernel='HongMeng Kernel 1.12.0' os='(n/a)' (backend ret=0)
```

产物：`lib/libtypec.so.0.6.0` + 软链 `libtypec.so.0`、`libtypec.so`；
`include/libtypec.h`、`include/libtypec_config.h`。
（backend ret=0：该设备 sysfs 后端 init 未报错；os='(n/a)' 因 OHOS 无 /etc/os-release。）

### 本设备环境踩坑（非配方改动，记录给后续）

1. **meson 不在 PATH**：设备 meson 1.11.2 是 python 模块，无 `meson` 可执行脚本。
   已在 `$HOME/usr/local/bin/meson` 建包装：`exec python3 -m mesonbuild.mesonmain "$@"`。
2. **profile 工具链路径不对**：共享 profile `ohos-aarch64` 写死
   `/data/service/hnp/bin/clang`，本设备不存在；真实工具链在
   `$HOME/usr/local/bin/{clang,clang++,llvm-ar,llvm-ranlib,llvm-objcopy,binary-sign-tool}`。
   另建 profile `~/.conan2/profiles/ohos-libtypec`（include ohos-aarch64，覆盖
   compiler_executables 与 CONFIG_SHELL/SHELL）。
3. **/tmp 只读**：clang 无法写临时文件。需 `export TMPDIR=$HOME/tmp`。
4. **无系统 pkg-config**：以 `tool_requires("pkgconf/3.0.5")` 提供；其二进制名为
   `pkgconf`，配方 generate() 里设 `os.environ["PKG_CONFIG"]="pkgconf"` 让 meson 找到。
5. 内存：设备总 24GB、MemAvailable 7.4GB；用 `NINJAFLAGS=-j4` + `-c tools.build:jobs=4`
   限并行，未触发 OOM。

成功命令（在设备上）：

```bash
cd ~/tmp/libtypec-build
export TMPDIR=$HOME/tmp
env NINJAFLAGS="-j4" $HOME/.local/bin/conan create . \
  -pr:h=ohos-libtypec -pr:b=ohos-libtypec -c tools.build:jobs=4
```

## 下一步

- 真机验证已过（W3）。待 shadow CI / 审计通过后 upload 并提 PR。
- 注意：本配方用设备本地 profile `ohos-libtypec`（覆盖了工具链路径）；CI 标准
  runner 的 `ohos-aarch64` 路径若一致则无需覆盖，若不一致需在 CI profile 统一修正。

