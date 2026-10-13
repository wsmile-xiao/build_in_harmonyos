# libevdev 1.13.4 适配笔记(HarmonyOS PC / aarch64)

## 基本信息

- 构建系统: **meson**
- 上游版本: 1.13.4(Debian bookworm 源包 `1.13.4+dfsg-1` 的 orig)
- 源 URL: `https://deb.debian.org/debian/pool/main/libe/libevdev/libevdev_1.13.4+dfsg.orig.tar.xz`
  sha256 `be3456ab8289e53c9f13b6dfef10349b4f551f5d365cb58b7dd29d42488cd897`(实测)
- 补丁: **1 个** — `patches/0001-meson-make-librt-libm-optional.patch`
- 与 main 上已发布的 1.13.3 / 1.13.7 的关系: 本版本是积分赛依赖任务的
  指定版本提交,构建要点(平台头软链、AR/RANLIB、TMPDIR、SONAME 软链)
  与 1.13.7 配方保持一致,便于后续统一维护。

## 补丁说明(musl:librt/libm 可选化)

上游 `meson.build` 依赖段:

```meson
dep_lm = cc.find_library('m')
dep_rt = cc.find_library('rt')
```

`cc.find_library()` 默认 `required:true`,找不到即中止 `meson setup`。
OHOS PC 的 musl libc:

- 无独立 `librt.so`(glibc 的 librt 在 musl 里并入 libc);
- `libm` 同样并入 libc(musl 只有一个 libc.so);
- 库本体**不引用** librt 专有符号:`clock_gettime` 只出现在测试代码,
  musl 与 glibc ≥ 2.17 都由 libc 直接提供。

补丁改为 `cc.find_library(..., required: false)`,glibc 平台行为不变
(找得到照样链),musl 平台优雅降级为空依赖列表。

## 平台构建要点(承 1.13.7)

| 要点 | 原因 |
|------|------|
| `include/linux/harmonyos/` 头软链 | meson 把 OHOS 映射为 `host_machine.system()='harmonyos'`,上游按该名查 UAPI 头;HarmonyOS 用 Linux 内核,软链到 `../linux/` 即可 |
| `AR`/`RANLIB` 环境注入 | meson 否则回退到宿主 `ar`;从 profile `compiler_executables` 推导 `llvm-ar`/`llvm-ranlib` |
| `TMPDIR` 指到可写目录 | HarmonyOS `/tmp` 是只读 erofs(E002) |
| shared 时补 `.so` SONAME 软链 | HMDFS 上 symlink 步骤可能丢失,`-levdev` 会找不到 dev 软链 |
| `-Dtests=disabled -Ddocumentation=disabled` | tests 需要真实 /dev/input 设备;documentation 需要 doxygen,均非构建目标 |

## 验证记录(本地,未交叉编译)

- 补丁对 Debian orig 解包树 `git apply --check` **通过**(与 conan 构建
  时 `apply_conandata_patches` 同一 -p1 语义);
- 源码树 meson.build/头文件做过 musl 兼容性静态检查(8/8 通过,
  见提交记录;工具链无 OHOS 交叉环境,实际构建由 CI `conan create` 完成);
- sha256 为下载原包实测值。

## test_package(L1 消费者测试)

与 1.13.7 相同的 `test.c`:验证 `libevdev_event_type_get_name(EV_KEY)`、
`libevdev_event_code_get_name(EV_KEY, BTN_LEFT)`、`libevdev_new/free`
生命周期,均不需要真实设备。上游 meson test 套件需要 /dev/input,
构建机上如实跳过(`-Dtests=disabled`),不做 skip 掩盖。

## 交付物

| 路径 | 说明 |
|------|------|
| `lib/libevdev.so.2.3.0` + SONAME/dev 软链 | 共享库 |
| `include/libevdev-1.0/` | 公开头 |
| `lib/pkgconfig/libevdev.pc` | pkg-config 元数据(libinput 的依赖入口) |
| `bin/` 工具 | libevdev-tweak-device / mouse-dpi-tool / touchpad-edge-detector |
