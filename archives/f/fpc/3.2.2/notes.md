# fpc 3.2.2 适配笔记（HarmonyOS PC / aarch64）

## 结论

- **目标**：aarch64-linux（FPC 3.2.2 无 `ohos` 目标）。
- **交付**：官方 aarch64-linux 发行（编译器 + RTL + 全部包单元）+ 上游源码 `rtl/` 子树 + 可重定位 `fpc` 启动器。
- **无第三方 conan 依赖**：配方不含 `requires`/`tool_requires`。

## 为什么是「组装官方发行」而不是「源码自举构建」

1. FPC 是自举编译器：从源码构建需要一个能运行的引导编译器，并需要 **目标平台的 GNU `as`/`ld`**。
2. 实测源码交叉构建（`make crossall CPU_TARGET=aarch64 OS_TARGET=linux PP=ppcx64`）在编译 aarch64 RTL 时失败：

~~~
aarch64-linux-as  -o .../rtl/units/aarch64-linux/prt0.o aarch64/prt0.as
make[5]: aarch64-linux-as: No such file or directory   → Error 127
~~~

   本机 WSL 无法安装 `binutils-aarch64-linux-gnu`（无 sudo），CI 的 OHOS worker 也以 clang/lld 为主、不保证有 GNU `as`。
3. FPC 官方 3.2.2 编译器二进制**静态链接**（`file` 实测 `statically linked`），aarch64 发行在 OHOS aarch64 可原生运行；
   仓库历史归档 `archives/f/fpc/3.2.2`（设备原生）也是走预编译包这条路。

因此本配方 pin 官方两份输入（源码 tarball + aarch64-linux 发行 tarball，均带 sha256），组装后交付。

## 打包与可重定位设计

- 官方发行分为外层 `fpc-3.2.2.aarch64-linux.tar` → 内层 `binary.aarch64-linux.tar` → `base.*` + `units-*` + `utils*` 多个 tarball；
  配方按 base → units → utils 顺序解包到统一 prefix，再整体安装进 conan 包。
- `bin/fpc` 被替换为 **shell 启动器**（官方 ELF driver 保留为 `bin/fpc-driver`）：启动器从自身路径推导包根，
  设置 `-Fu` unit 搜索路径，并强制 `-Aelf -Xi`（FPC 内部 ELF 写入器 + 内部链接器），使编译/链接不依赖宿主的 GNU binutils。
- `package_info()` 导出 `FPCDIR=<pkg>/share/fpc-3.2.2-src` 与 `PATH+=<pkg>/bin`，供下游 lazarus 使用。

## 上游测试（testsuite）

- 官方 aarch64-linux 发行**不含 `tests/`**，故从官方源码 tarball 取 `tests/` 执行。
- 2026-09-26 在 **x86_64 Linux 原生**（官方 x86_64 FPC 3.2.2，同一 3.2.2 源码）执行 `make full TEST_FPC=<fpc> -j8`：
  - `Total = 7908`；编译 4871（成功 3688 + 预期失败 1170 + 失败 9 + 本应失败却成功 4）；运行 3037（成功 3016 + 失败 21）；跳过 513。
  - 通过率：运行 **3016/3037 = 99.3%**；编译符合预期 **4858/4871 = 99.7%**。
  - 34 项偏差为宿主环境相关（缺 `libgcc`/`libz`/`__gxx_personality_v0` 等），非交付物缺陷；完整 `faillist`/`longlog` 见 task 目录 `logs/080-upstream-testsuite.log`。
- aarch64 交付物为官方上游发行，由 CI 的编译+运行与下游 `lazarus/4.8` 构建验证。

## 验证

- `test_package/test.sh`：`fpc -iV`、`fpc -iTP -iTO`、编译 `hello.pas`、执行产物（CI 原生 OHOS aarch64 上运行）。
- 本地 W3（WSL 交叉 profile，`tools.build:skip_test=True`）验证 `conan create` 出包；执行验证在 CI / 鸿蒙电脑。

## CI 源码下载（慢链路 + 源码缓存自播种）

两份输入合计约 190 MB。CI worker 到 `downloads.freepascal.org` 的链路实测只有
~10 KB/s（#62104/#62108/#62109），到 `downloads.sourceforge.net` 约 22 KB/s 且中途
断流（#62025 在 57 MB/138 MB 处 `IncompleteRead`）。因此配方不再直接对 https URL 调
`tools.files.get()`，而是先自己取回输入：

1. 先查 `DOWNLOAD_CACHE`（CI 导出 `/data/cache`）下的 `s/<sha256>`（Conan 源码下载
   缓存布局），命中即零网络；
2. 未命中时按候选 URL 表（官方 `downloads.freepascal.org` → 官方下载页登记备用
   `downloads.sourceforge.net`）下载：HTTP `Range` 分块 ×8 并发（单条流的限速不再
   约束整体吞吐）+ 每块重试/续传 + 组装后按 sha256 校验，通过后再原子 `os.replace`
   写入 `s/<sha256>`；
3. `tools.files.get()` 只用于解包本地缓存文件（`file://`，按真实文件名保留扩展名，
   因为 Conan 依据扩展名选择解压器）；
4. 分块临时文件保存在 `<cache>/parts/<sha256>/`，即使某次构建超时/断流，下一次构建
   也能从断点续传。

本机 WSL 冷缓存实测：`conan create` 全程零外网（先下载入缓存，复跑命中缓存），
`fpc -iV` = `3.2.2`，`hello from fpc on Linux/aarch64 = 903`，EXIT=0。

## 与历史归档的关系

旧 `archives/f/fpc/3.2.2`（2026-05-27）是设备原生预编译包，`source.url=file:///storage/...`、无 `conanfile.py`、从未发布到制品仓。
本 PR 将其重建为正式 conan 包（并发往 `fpc/3.2.2`）。
---

**编译结束**: 2026-09-26 01:09
**最终状态**: built
