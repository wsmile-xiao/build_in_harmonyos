# tslib 1.22 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-17
- 编译器: clang/clang++（OHOS SDK native，`/data/service/hnp/bin/clang`）
- 状态: built

## 编译步骤

1. `conan create` 由配方驱动：`get()` 下载官方源码（GitHub releases，sha256 校验）→
   `apply_conandata_patches()` 应用 HMDFS umask 补丁 →
   `_compiler_env()` 从 profile `tools.build:compiler_executables` 注入
   `CC/CXX/AR/RANLIB` → `CONFIG_SHELL=/bin/sh SHELL=/bin/sh ./configure
   --prefix=<package_folder> --build=aarch64-unknown-linux-gnu
   --host=aarch64-unknown-linux-gnu --enable-shared --disable-static` →
   `make -j2` → `make -j1 check`（结构性空跑，留档）→ `make install`。
2. 共享-only 是架构性选择：tslib 的 14 个过滤/输入模块是运行期 dlopen 的
   `.so` 插件（`<prefix>/lib/ts`），静态库无法支撑插件加载语义。
3. 设备端探索性编译先行（ws/tmp/tslib-1.22/explore）：configure → make -j2 →
   make install 全部通过，产物 libts.so.0.10.4 + 14 插件 + 11 工具 + ts.conf。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 深层通过后 `config.status: error: could not setup config files machinery`，`can't create ./conf*/subs1.awk: Permission denied` | HMDFS UID 映射使 `umask 077 && mktemp -d` 创建的 0700 临时目录对当前进程不可写（知识 E011，xz/tar/wget/tmux 等已确认同类） | 补丁 `patches/0001-configure-umask-022-for-hmdfs-temp-dirs.patch`：configure 内两处 `umask 077` → `umask 022`（mktemp 主路径与 `mkdir ./conf$$-$RANDOM` 回退路径都要改）；`git apply --check` 与 `patch -p1` 双工具在设备上对原始包验证通过 |
| 2 | 首轮 W3 conan create 报 `configure: error: no acceptable C compiler found in $PATH`（探测 aarch64-unknown-linux-gnu-gcc/gcc/cc 全部失败） | OHOS 适配版 conan 的 AutotoolsToolchain 不把 profile 的 `tools.build:compiler_executables` 映射为 `CC/CXX`（adplay/1.9 注释记录同坑，参照 jack/1.9.22 先例）；初稿把自定义 `Environment` 传给 `tc.generate(env=...)` 还会丢弃 toolchain 内部 env | 改用 adplay 模式：`_compiler_env()` 读 conf 后以 `env.vars(self).apply()` 运行期注入 `CC/CXX/AR/RANLIB`，configure/make 经 `self.run(..., env="conanbuild")` 执行 |
| 3 | `configure: error: cannot guess build type`（config.guess 2018-02-24） | 设备 `uname -s = HarmonyOS`（HongMeng Kernel 1.12.0），2018 年 config.guess/config.sub 均不识别 ohos | 显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（a52dec 等存量配方同款做法） |
| 4 | CMake 备选路径会静默跳过 10 个上游工具 | tests/CMakeLists.txt 以 `UNIX`/`LINUX`（`CMAKE_SYSTEM_NAME STREQUAL Linux`）门控工具构建，HarmonyOS 下均不成立，仅构建 ts_uinput | 改用 autotools 路径：全部 11 个工具 + 14 插件照常构建，无需改上游 CMake 逻辑 |
| 5 | 第二轮验证 G2 conan create 的 configure 报 `shell-init: getcwd ...`、`working directory cannot be determined`（同轮 W3 却通过——间歇性）；探索阶段 hnp bash 在 tar 解压目录亦报同错 | HMDFS 上 profile buildenv 注入的 hnp bash（CONFIG_SHELL）getcwd 能力随目录/时机间歇失效，污染 autoconf（E386 同族：shell 须能力实测） | configure 命令行前缀强制 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`（多目录能力实测干净的 POSIX shell；make 使用 Makefile 内置 SHELL=/bin/sh，不受环境变量影响） |

## 源码修改

- `patches/0001-configure-umask-022-for-hmdfs-temp-dirs.patch`：
  仅修改 `configure` 中临时目录创建的 umask（077→022，两处），
  无平台宏、无逻辑改动；`patch -p1` 与 `git apply --check` 干净应用已验证。

## 依赖版本

- 无外部依赖（W0 确认：`conan install --requires=tslib/1.22 --build=never` 于 ohpcd
  未命中，依赖清单为空；libdl 由系统 libc/libdl.a 提供，configure 自动探测）。

## 验证结果

探索性构建（设备 aarch64 真机，与 CI 同源 profile 工具链）：

```bash
CC=/data/service/hnp/bin/clang ./configure --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-gnu --prefix=$D/inst-auto   # umask 补丁应用后退出码 0
make -j2                  # 退出码 0
make install DESTDIR=...  # 退出码 0
```

产物清单（autotools 默认全集）：

- `lib/libts.so.0.10.4`（soname libts.so.0）
- `lib/ts/`：debounce/dejitter/evthres/iir/input/invert/linear/lowpass/median/
  pthres/skip/touchkit/variance/waveshare 共 14 个插件模块
- `bin/`：ts_calibrate、ts_conf、ts_finddev、ts_harvest、ts_print、ts_print_mt、
  ts_print_raw、ts_test、ts_test_mt、ts_verify（tests/）+ ts_uinput（tools/）共 11 个
- `etc/ts.conf`、man 手册、pkgconfig

真机冒烟运行（设置 `TSLIB_PLUGINDIR/TSLIB_CONF/LD_LIBRARY_PATH` 后）：

```bash
$ tests/ts_print_raw
ts_setup: Permission denied     # 二进制可执行、libts.so 加载、input 插件 dlopen 成功，
$ tests/ts_conf                  # /dev/input/* 受 SELinux 限制属预期，错误路径干净
ts_setup: Permission denied
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libts.so.0.10.4 | ~35 KB | 触摸屏访问库（ABI 0.10.4） |
| lib/ts/*.so ×14 | 各 4–14 KB | 过滤器与输入插件模块 |
| bin/ 工具 ×11 | 各 8–30 KB | 校准/打印/测试/虚拟输入等诊断工具 |
| etc/ts.conf | 3 KB | 模块加载配置示例 |

## 注意事项

1. 上游无自动化测试套件：任何 Makefile.am 均无 `TESTS/check_PROGRAMS`，
   `make check` 是 automake 结构性空跑；tests/ 下程序是需真实触摸屏+framebuffer
   的交互工具，不能当无头测试运行（详见 test_package/MANIFEST.yml）。
2. 消费者测试 `test_tslib_consumer.c` 不依赖硬件：校验
   `ts_libversion()` 版本契约与 `ts_open()` 对不存在设备的干净失败路径。
3. 库为 LGPL-2.1，tests/tools 下的工具程序为 GPL（上游 README 声明）；
   配方 license 字段按主库登记。
4. 运行期插件从编译期固化的 `<prefix>/lib/ts` 读取；配方以
   `--prefix=package_folder` 配置，消费侧无需额外设置 `TSLIB_PLUGINDIR`。

---

**编译结束**: 2026-09-17 15:38
**最终状态**: built
