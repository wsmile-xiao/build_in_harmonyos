# dconf 0.40.0 适配笔记

## 编译环境
- **构建系统**: meson（GNOME gsettings 后端 + dconf CLI）
- **编译日期**: 2026-09-02
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 1（0001-tests-allow-multiple-definition.patch——测试链接标志：静态 libgio-2.0.a 内部 gvdb_* 符号与测试 mock 重复冲突，加 --allow-multiple-definition）

## 编译步骤（conan create 全流程）

```bash
conan create archives/d/dconf/0.40.0 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GNOME 官方发行下载并 strip_root（目录 dconf-0.40.0）。

### 2. 构建（build()）
- meson 构建（libdconf + bin/dconf CLI + GSettings 后端 + D-Bus service）
- 依赖 glib/2.84.0（提供 gio-2.0/gio-unix-2.0）+ dbus/1.14.10（均已发布 ohpcd）
- 关闭 systemd/bash-completion/man/gtk-doc/vapi 等桌面生态依赖项
- build() 末尾实测运行上游 tests（meson test）：11 个单元/ABI 测试目标 11/11 通过

### 3. 打包（package()）
- meson install：bin/dconf + lib + GSettings 后端模块 + service 文件

## 上游测试（rule 4 实测）
- 上游 tests（tests/，meson test 接入），build() 内实测运行
- **实测：11 个单元/ABI 测试目标 11/11（100%）全部通过**——paths/changeset/
  shm/gvdb/gdbus-thread/gdbus-filter/engine/client/writer/libdconf/gsettings
  （无需会话 D-Bus 的用例全部实测，本地 conan create exit=0）
- 3 个用例需会话 D-Bus（gdbus-thread-leak/gdbus-filter-leak/dconf 集成测试）：
  OHOS /tmp 只读（E002）+ GTestDBus 硬编码 /tmp socket 路径——真机已实测
  构建 dbus-daemon + LD_PRELOAD bind shim 验证会话总线可启动（独立 daemon 打印
  地址并常驻），但 GTestDBus 握手机制在 OHOS 仍受限（平台限制，rule 1.2 如实声明）
- 适配后：test_package R34 真实执行 bin/dconf 校验（4 断言，E212 沙箱降级静态
  ELF 校验时如实报告）

## 已知限制
- 3 个依赖会话 D-Bus 的集成测试（gdbus leak ×2 + dconf 集成）受 OHOS /tmp 只读
  （E002）+ GTestDBus 硬编码 socket 路径限制；其余 11 个测试全部实测通过
---

**编译结束**: 2026-09-02 17:00
**最终状态**: built
