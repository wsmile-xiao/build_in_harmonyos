# acsccid 1.1.13 适配笔记

## 编译环境
- 构建系统: autotools（configure/make，自带生成的 configure，无需 autoreconf）
- 编译日期: 2026-08-07
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- 目标平台: HarmonyOS PC (aarch64, os=OHOS arch=armv8)
- 状态: built（conan-verify G0-G4 PASS，未上传远程）

## 编译步骤

1. **W0 依赖检查**：libusb/1.0.27 已发布 ohpcd；pcsc-lite/2.4.0 由子任务1本地适配（conan 缓存 binary 就绪，include/PCSC/ 头文件 + libpcsclite.pc）。
2. **init-build**：`python3 scripts/ohc-run.py init-build acsccid 1.1.13 --url <sourceforge> --tar tar.bz2`，源码解压到 `~/builds/acsccid-1.1.13.work`。
3. **E007 config.guess/sub 补丁**：`perl scripts/patch-autotools-ohos.pl config/config.guess config/config.sub`。
4. **依赖环境注入**：`conan install --requires=libusb/1.0.27 --requires=pcsc-lite/2.4.0 -g=PkgConfigDeps -g=AutotoolsDeps ...` 生成 libpcsclite.pc / libusb-1.0.pc，`PKG_CONFIG_PATH` 指向生成目录。
5. **configure**：`./configure --prefix=... --enable-usbdropdir=/usr/local/pcsc/drivers`。首次失败：conftest 运行时缺 libpcsclite.so.1/libusb-1.0.so.0 → 注入 `LD_LIBRARY_PATH=<conan 缓存 lib 目录>`；随后 `usbdropdir` 为空（pcsc-lite .pc 未提供该变量）→ 显式 `--enable-usbdropdir`。
6. **make -j1**：成功产出 `src/.libs/libacsccid.so`（含全部 IFDH* 导出符号 + .codesign 自签段）。
7. **make check**：上游未注册测试目标，空操作（见 test-report.md）。
8. **staging 验证**：`make install DESTDIR=$TEST_PREFIX` → `pcsc/drivers/ifd-acsccid.bundle/Contents/HarmonyOS/libacsccid.so` + Info.plist。
9. **conan 配方**：conanfile.py（AutotoolsToolchain + PkgConfigDeps + AutotoolsDeps + E077 ELF 重签）+ conandata.yml（三源 URL 列表）+ test_package（dlopen 驱动 bundle 校验 IFD 符号）。
10. **conan create + conan-verify**：全链路 PASS（G0-G4），test_package 输出 `acsccid 1.1.13 OK: dlopen + IFD symbols verified`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cannot run C compiled programs` | conftest 链接了 libpcsclite.so.1/libusb-1.0.so.0，运行时 LD_LIBRARY_PATH 未包含 conan 缓存库目录 | 注入 `LD_LIBRARY_PATH` 指向依赖 lib 目录 |
| 2 | `use --enable-usbdropdir=DIR` | 上游通过 `pkg-config libpcsclite --variable=usbdropdir` 取值，pcsc-lite 的 .pc 未提供该变量 | 显式传 `--enable-usbdropdir=/usr/local/pcsc/drivers` |
| 3 | `config.status: subs1.awk: Permission denied`（E167） | config.status 用 `mktemp -d ./confXXXXXX`（umask 077）动态建临时目录，HMDFS 上写入被拒 | 保留 mktemp+umask 077；失败时回退固定目录 + umask 077 + chmod 700，补丁 p-configure.patch |
| 4 | test_package dlopen 失败：`libpcsclite.so.1 not found` | bundle 内 libacsccid.so 依赖 pcsc-lite 动态库，dlopen 进程未带其 lib 路径 | test_package 命令内联 `LD_LIBRARY_PATH`（conan run env 列表在 OHOS 环境未生效） |
| 5 | test_package dlopen 失败：`log_msg: symbol not found` | IFD 驱动依赖 pcscd 宿主符号 log_msg/log_xxd | test 程序提供 stub + `-Wl,-E` 导出到动态符号表 |

## 源码修改

| 补丁 | 内容 |
|------|------|
| p-guess.patch | config.guess 增加 `__OHOS__`/HarmonyOS 检测，输出 `aarch64-unknown-linux-ohos` |
| p-sub.patch | config.sub 识别 `ohos-linux` tuple |
| p-configure.patch | configure 优先 mktemp；HMDFS 失败时固定目录 + umask 077 + chmod 700（E167） |

## 依赖版本

- libusb/1.0.27（ohpcd 已发布）
- pcsc-lite/2.4.0（子任务1 本地适配，conan 缓存）

## 验证结果

```bash
conan create archives/a/acsccid/1.1.13 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → acsccid/1.1.13: Package created
# test_package: dlopen ... libacsccid.so → acsccid 1.1.13 OK: dlopen + IFD symbols verified

python3 scripts/ohc-run.py conan-verify acsccid 1.1.13
# → G0/G1/G2/G3/G4 全 PASS，可标记 published
```
