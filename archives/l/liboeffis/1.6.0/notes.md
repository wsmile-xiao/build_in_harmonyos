# liboeffis 1.6.0 — OHOS 适配笔记

## 基本信息
- **软件名**: liboeffis
- **版本**: 1.6.0
- **上游**: https://gitlab.freedesktop.org/libinput/libei
- **许可证**: MIT
- **构建系统**: meson
- **适配日期**: 2026-09-30

## 关键发现

### liboeffis 不是独立库
liboeffis 是 libei 1.6.0 项目的第三子组件（XDG RemoteDesktop portal DBus helper）。
libei 1.6.0 构建三个库：
- libei（客户端）— 独立任务面 archives/l/libei
- libeis（服务端）— 独立任务面 archives/l/libeis/1.6.0
- liboeffis（portal helper）— 本任务面

### 依赖关系
- sd-bus provider: systemd 261.1（ohpcd 已发布，提供 libsystemd）
- 通过 `-Dsd-bus-provider=libsystemd` 显式指定
- systemd 261.1 包无 `.pc` 文件 → `generate()` 中手写 `libsystemd.pc` 并注入 `PKG_CONFIG_PATH`

## OHOS 平台适配

### 1. musl 解析 DT_NEEDED 不跟随符号链接
OHOS musl 不跟随符号链接解析 `DT_NEEDED`，systemd 包的
`libsystemd.so.0 -> libsystemd.so.0.44.0` 无法被解析。
- `build()`：`_flatten_systemd_libs()` 把实体文件摊平到 `<build>/systemd-libs/`
- `test()`：把 `liboeffis.so.1` / `libsystemd.so.0` 摊平到运行时目录，经 `LD_LIBRARY_PATH` 注入

### 2. meson install 的 RPATH 重写产物在 OHOS 不可加载（关键）
`meson install` 的 depfixer 会重写 ELF 的 RUNPATH：把链接期写入的
`$ORIGIN/../systemd-libs` 抹掉并填充占位字节。经该重写产出的共享对象在 OHOS
上无法被 musl 动态链接器加载：

```
$ dlopen(liboeffis.so.1)
FAIL: Error loading shared library liboeffis.so.1: Permission denied
```

而构建目录中**未经重写**的同一对象可以正常 `dlopen`（两个文件体积相同、md5 不同）。

**解法**：`package()` 中 `_restore_build_shared_libs()` 用构建目录产物覆盖
meson install 安装出的 `.so`，保证交付的共享对象可被 OHOS musl 加载。

> 排查记录：曾误判为「SELinux 阻止加载 appdat 上下文 .so」并在 test_package 中
> `if os == "OHOS": return` 跳过运行时——该结论已被证伪（`LD_LIBRARY_PATH` 在
> OHOS 上生效，同目录同上下文的 libsystemd.so.0 可正常加载），且 CI 使用同一
> `ohos-aarch64` profile（`os=OHOS`），跳过逻辑会导致测试在任何环境都不执行。

### 3. musl tmpfile() 与只读 /tmp
`0001-test-tmpfile-portable.patch`：`/tmp` 在 OHOS 沙箱只读且 musl 的 `tmpfile()`
硬编码 `/tmp` 忽略 `$TMPDIR` → 改为在 `$TMPDIR` 下创建唯一文件并立即 unlink。

## 鸿蒙特有测试（消费者用例）
`test_package/src/test_package.c` 是**具名端到端消费者用例**（可执行程序
`test_liboeffis`，真实链接 `liboeffis.so` 并调用公共 API），覆盖：
1. `oeffis_new` / `oeffis_ref` / `oeffis_unref` 生命周期（引用计数语义）
2. `oeffis_get_fd` / `oeffis_get_eis_fd`（连接前返回 -1 / `ENODEV`）
3. `oeffis_create_session_on_bus`（无效 busname）→ `oeffis_dispatch` + `oeffis_get_event`
   得到 `OEFFIS_EVENT_DISCONNECTED`
4. `oeffis_get_error_message` 返回具体错误串

OHOS 无 XDG RemoteDesktop portal，测试使用无效 busname 触发上游文档化的错误路径
（与上游 `test_failed_connect` munit 用例同一思路）。断言失败 ⇒ 非零退出 ⇒
`conan create` 失败，是真实门禁。

实测输出：
```
=== liboeffis consumer test ===
[1] lifecycle: new/ref/unref
[2] get_eis_fd before connection
[3] failed connect: invalid busname
    error_message: Failed to init dbus: No medium found
=== all assertions passed ===
```

## 上游测试
`meson test` 共 3 个套件，全部通过（`Ok: 3 / Fail: 0`）：
- `libei:dtdcheck`
- `libei:unit-tests-utils`（内部 36/36）
- `libei:unit-tests-oeffis`（内部 2/2：`test_init_unref`、`test_failed_connect`）

合计 39 项断言（1 + 36 + 2）。**该数字是本任务面裁剪配置下的注册数**：
`-Dlibei=disabled -Dlibeis=disabled` 使 `unit-tests-ei`、`unit-tests-eis`、
`eierpecken` 三组不注册（属各自任务面，非静默删除）；python 套件
（`oeffis-pytest`）需 pytest + dbusmock + structlog，`-Dtests=auto`
下 meson 自动跳过，不注册用例。

## 补丁说明
1. **0001-test-tmpfile-portable.patch**：musl `tmpfile()` → `$TMPDIR` 唯一文件（立即 unlink）
2. **0002-vendor-munit-subproject.patch**：`subprojects/munit.wrap` 是
   wrap-git(revision=head)，CI 离线不可拉取 → vendor munit 三文件
   （`meson.build` / `munit.c` / `munit.h`）并强制 `install: false`，
   使交付包只含 liboeffis。

## 构建配置
- `-Dliboeffis=enabled`
- `-Dlibei=disabled`
- `-Dlibeis=disabled`
- `-Dsd-bus-provider=libsystemd`
- `-Dtests=auto`
- `-Ddocumentation=[]`

## 验证结论
| 门禁 | 结果 |
|---|---|
| `conan create` | PASS（含上游测试 + 消费者用例真实运行） |
| 上游 meson test | 3/3（36 + 2 子项全过） |
| 消费者用例 | PASS（真实运行，exit=0） |
| `conan-verify` G0–G4 | PASS |
| W3 本地 CI | PASS |
| finish | built |
---

**编译结束**: 2026-10-01 00:45
**最终状态**: built
