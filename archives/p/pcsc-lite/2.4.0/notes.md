# pcsc-lite 2.4.0 编译笔记

## 编译信息

- 软件名称: pcsc-lite
- 版本: 2.4.0
- 编译日期: 2026-08-07（首次归档 2026-05-25，本次补齐 conan 配方与验证）
- 构建系统: meson（autoreconf 在鸿蒙上因宏缺失失败，已弃用 autotools）
- 编译器: clang 15.0.4（`aarch64-linux-ohos`）
- 平台: HarmonyOS PC aarch64

## 源码获取

- 官方源码: `https://pcsclite.apdu.fr/files/pcsc-lite-2.4.0.tar.xz`
  - ⚠️ 2.4.0 已随 2.5.0/2.5.1 发布从官方服务器下架，返回 404。
  - 实际下载自 Debian snapshot 权威镜像
    `https://snapshot.debian.org/archive/debian/20251019T203802Z/pool/main/p/pcsc-lite/pcsc-lite_2.4.0.orig.tar.xz`。
- SHA256: `22307017a99e123dbecb991136783beca07966f1376d74d9ad0004ba5f81c4f1`
- conandata.yml 的 `sources.url` 为 URL 列表：官方源优先、Debian 镜像兜底。

## 构建系统适配

- 源码含 `meson.build` + `meson.options` + `meson_options.txt`（后两者为符号链接对）。
- **meson_options.txt 是 meson.options 的符号链接**。手动复制源码树时（HMDFS 的
  copytree 会把符号链接物化为普通文件）会出现两份独立文件，meson ≥1.5 报错
  `meson.options and meson_options.txt both exist, but are not the same file`。
  - 手动构建时删除其中之一即可；conan `get()` 的 tarfile 提取保留符号链接，不受影响。
- **meson 探测不到归档器**：`Detecting archiver via: llvm-ar ... No such file`。
  conan 的 `MesonToolchain` 生成的 native file 不含 ar/ranlib，而 PATH 上无 `llvm-ar`。
  解决：在 `generate()` 中把 ar/ranlib 全路径注入 `conan_meson_native.ini`（同 cairo 配方做法）。

## 配置选项

```
meson setup build --prefix=... \
  -Dlibsystemd=false -Dlibudev=false -Dlibusb=true -Dpolkit=false \
  -Dusb=true -Dserial=true
```

## 编译问题

### 问题 1: pthread_cancel 未实现
- 错误: `undefined symbol: pthread_cancel`（或链接失败）
- 原因: HarmonyOS 未实现 pthread_cancel
- 解决: meson `has_function('pthread_cancel')` → `HAVE_PTHREAD_CANCEL`；源码用功能宏守卫，
  不可用时整段 if/else 退化为 stop-polling（`TAG_IFD_STOP_POLLING_THREAD`），避免仅打日志不杀线程
- 补丁: `patches/0002-meson-have-pthread-cancel.patch`、`patches/0001-src-eventhandler.c.patch`

### 问题 2: meson install 重写 rpath → 链接器自签失效
- 现象: 安装后的 `pcscd` 执行报 `Operation not permitted`
- 原因: meson install 重写 ELF（rpath 处理）使链接器自签的 `.codesign` 失效，鸿蒙拒绝加载
- 解决: `package()` 中对包内所有 ELF（sbin/pcscd、lib/*.so*）剥 `.codesign` 后
  用 `binary-sign-tool sign -selfSign 1` 重签（参考 cairo 配方 `_sign_shared_libs`）

### 问题 3: libusb pc 文件路径错
- conan libusb 包的 `libusb-1.0.pc` 里 prefix 硬编码为 `/usr/local`，不指向 conan 缓存实际路径
- 解决: 配方用 `PkgConfigDeps(self).generate()` 生成指向 conan 包路径的 `libusb-1.0.pc`，meson `dependency('libusb-1.0')` 即可命中

## 依赖

- libusb/1.0.27（conan 包，已发布到 ohpcd 远程，无需适配）
- dl、pthread（系统提供）

## 上游测试

见 `reports/test-report.md` 摘要：

- `meson test` → 上游无 test() 目标，报 "No tests defined"（上游现状）
- `pcsc-wirecheck` ABI 自检 → **PASS**（"Checking ABI... OK"）
- `pcscd --version` → **PASS**
- pcscd 启动 / testpcsc / UnitaryTests → **平台限制**：鸿蒙沙箱禁止 AF_UNIX socket bind
  （EPERM，独立最小复现确认），且无 /run/pcscd、无读卡器硬件
- test_package 消费者验证 → **PASS**（SCardEstablishContext 返回预期 SCARD_E_NO_SERVICE）

## ELF 签名

- 工具: `/data/service/hnp/bin/binary-sign-tool`，模式 `self-sign`
- 结果: 包内 pcscd 与所有 .so 均含 `.codesign` 段，`pcscd --version` 可执行

## 知识提取

### L1 平台真理
- pthread_cancel 在 HarmonyOS 上未实现
- 鸿蒙沙箱/SELinux 禁止 AF_UNIX socket `bind()`（EPERM），IPC 类守护进程无法在本平台启动
- `/run` 目录不存在且无权限创建
- ELF 必须在链接后/install 重写后重新签名才能执行
- meson ≥1.5 对 `meson.options`/`meson_options.txt` 双文件（非同一文件）报错

### L2 模式经验
- meson 构建系统在鸿蒙上更可靠（避开 autotools 宏问题）
- meson 构建需在 native file 注入 ar/ranlib（conan MesonToolchain 不含）
- conan PkgConfigDeps 可解决依赖 .pc 文件 prefix 路径错误
- meson install 后需批量重签 ELF

### L3 本版笔记
- 使用 meson 替代 autotools
- 配置选项：禁用 systemd/polkit，启用 libusb/serial
- 补丁 0002/0001：HAVE_PTHREAD_CANCEL 功能检测 + stop-polling 回退

## 质量门禁

- G0 干净构建: PASS（conan create 干净构建）
- G1 配方完整性: PASS
- G2 conan create: PASS（pcsc-lite/2.4.0 构建成功）
- G3 系统同名库隔离: PASS（无冲突）
- G4 产物完整性: PASS（pcscd, libpcsclite.so.1, libpcsclite_real.so.1, libpcscspy.so.0, include/PCSC/*.h）
- L2/L4/L5: 通过（conan-verify）

---
**编译结束**: 2026-08-07
**最终状态**: built（配方已验证，未上传远程）
---

**编译结束**: 2026-08-07 12:38
**最终状态**: built
