# dconf 0.40.0.1 适配笔记

> 本版本（0.40.0.1）为 0.40.0 的适配修复版（R37：制品仓同版本多 revision 会 409，
> 修复必须递增后缀）。源码、补丁、构建配置与 0.40.0 完全一致，唯一差异：
> **package() 内对包内全部 ELF 做 OHOS 签名（binary-sign-tool selfSign）**。

## 0.40.0.1 修复说明

OHOS 动态链接器对未签名共享库拒绝 dlopen（E073/E131 类）。制品仓已发布的
dconf/0.40.0 包 `libdconf.so.1` 未做 OHOS ELF 签名，导致消费方（libkysdk-desktop
3.0.1.0，PR #12668）CI 运行期拒载：

```
Error loading shared library libdconf.so.1: (needed by .../libkysdk-shortcut.so.2)
Error relocating .../libkysdk-shortcut.so.2: dconf_client_new: symbol not found
```

本版本在 `package()` 末尾（OHOS 下）遍历 package_folder 对全部真实 ELF 文件
（跳过 symlink）执行 `binary-sign-tool sign -selfSign 1`（与 acme-client/alsa-lib
配方同模式）。实测：签名前 `dlopen libdconf.so.1` → Permission denied；签名后
→ OK，`dconf_client_new` 符号可解析。

## 编译环境
- **构建系统**: meson（GNOME gsettings 后端 + dconf CLI）
- **编译日期**: 2026-09-30
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 1（0001-tests-allow-multiple-definition.patch——测试链接标志：静态 libgio-2.0.a 内部 gvdb_* 符号与测试 mock 重复冲突，加 --allow-multiple-definition）

## 编译步骤（conan create 全流程）

```bash
conan create archives/d/dconf/0.40.0.1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GNOME 官方发行下载并 strip_root（目录 dconf-0.40.0）。

### 2. 构建（build()）
- meson 构建（libdconf + bin/dconf CLI + GSettings 后端 + D-Bus service）
- 依赖 glib/2.84.0（提供 gio-2.0/gio-unix-2.0）+ dbus/1.14.10（均已发布 ohpcd）
- 关闭 systemd/bash-completion/man/gtk-doc/vapi 等桌面生态依赖项
- build() 末尾实测运行上游 tests（meson test）：13 个目标，11 个通过
  （2 个 leak 用例需会话 D-Bus，平台限制，见下）

### 3. 打包（package()）
- meson install：bin/dconf + lib + GSettings 后端模块 + service 文件
- OHOS 下对包内全部 ELF 做 selfSign（本版本新增）

## 上游测试（rule 4 实测）
- 上游 tests（tests/，meson test 接入），build() 内实测运行
- **实测（2026-09-30）：13 个 meson test 目标，11 通过 / 2 失败（84.6%）**——
  paths/changeset/shm/gvdb/gdbus-thread/gdbus-filter/engine/client/writer/
  libdconf/gsettings 全部通过；gdbus-thread-leak/gdbus-filter-leak 失败，
  原因：GTestDBus 需 spawn `dbus-daemon` 会话总线守护进程，OHOS 环境
  /tmp 只读（E002）且 GTestDBus 硬编码 /tmp socket 路径（平台限制，
  与本次签名改动无关——改动仅 package() 后处理）
- 适配后：test_package R34 真实执行 bin/dconf 校验（4 断言，E212 沙箱降级静态
  ELF 校验时如实报告）

## 已知限制
- 2 个依赖会话 D-Bus 的集成测试（gdbus leak ×2）受 OHOS /tmp 只读（E002）+
  GTestDBus 硬编码 socket 路径限制；其余 11 个测试全部实测通过
---

**编译结束**: 2026-09-30 21:30
**最终状态**: built
