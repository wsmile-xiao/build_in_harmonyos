- **三方库名称**：libcanberra
- **上游版本**：0.30（对应 `libcanberra.so.0`，`-version-info 2:5:2`）
- **上游仓库地址**：http://0pointer.de/lennart/projects/libcanberra/
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（复用仓库内已合并的 autotools + OHOS 交叉编译适配模式，参照 libxrender/0.9.12 的 configure/umask 处理）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：解包核验 libcanberra-0.30 release tarball——`configure.ac`/`src/Makefile.am` 无 `check_PROGRAMS`/`TESTS`，无任何自动化测试框架 |
| 集成测试 | 0 | 无独立集成测试套件 |
| 其他测试 | 0 | 唯一可执行 `test-canberra` 是 `noinst_PROGRAMS` 演示程序：无断言，需真实音频后端播放系统声音文件，不算自动化测试 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无测试可集成 |
| 集成测试 | 0 | 不变 | 上游无测试可集成 |
| 鸿蒙特有测试 | 2 | 新增 | `libcanberra_api_surface`（19 个导出符号强类型活重定位 + 错误字符串扫描）+ `libcanberra_version_contract`（版本宏/错误码枚举编译期契约 + null 驱动完整生命周期），均在 built-in null 驱动上运行，无需音频设备，OHOS CI 可真实执行 |
| **合计** | **2** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为公共 canberra.h API 补 2 个 consumer 测试（合计 159 条运行时断言）。
> - **补全原因**：上游 libcanberra 0.30 无自动化测试（无 check_PROGRAMS/TESTS；唯一可执行 test-canberra 是 noinst 演示程序，无断言、依赖真实音频后端与系统声音文件，无法在无音频设备的 headless CI 上运行）。为验证「已发布库可加载、公共 API 可用」，在 built-in null 驱动上编写可真实执行的 consumer 测试。
> - **新增测试文件清单**：
>   1. `test_package/api_surface.c` — 对 libcanberra.so 全部 19 个导出符号（`ca_proplist_create/destroy/sets/setf/set`、`ca_context_create/set_driver/change_device/open/destroy/change_props/change_props_full/play_full/play/cache_full/cache/cancel/playing`、`ca_strerror`）取强类型函数指针完成载入期活重定位；扫描 -18..0 全部错误码的非空描述字符串；验证 `ca_strerror` 对越界码返回 NULL；proplist 工厂 create/destroy 冒烟。
>   2. `test_package/version_contract.c` — 编译期契约 `#if CA_MAJOR != 0`/`CA_MINOR != 30`（版本号是 #define 宏，预处理可见）；**错误码数值**（`CA_SUCCESS=0`…`_CA_ERROR_MAX=-19`）为 enum 常量、预处理不可见，改为**运行时 `CHECK()` 逐条锁定**；运行时校验 `CA_CHECK_VERSION` 宏语义与 `ca_strerror` 字符串表；在 null 驱动上跑完整生命周期 create → set_driver("null") → change_device → change_props_full → open → play_full（同步完成回调：断言 error_code==CA_SUCCESS、id、userdata）→ playing==0 → cancel → cache_full 返回 `CA_ERROR_NOTSUPPORTED` → destroy；并覆盖失败模式：set_driver("bogus") 后 open 返回 `CA_ERROR_NODRIVER`、open 后 set_driver 返回 `CA_ERROR_STATE`、缺 event.id/media.filename 的 play/cache 返回 `CA_ERROR_INVALID`、varargs play/change_props（NULL 哨兵）正常。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：**0/0（N/A）**。已解包 libcanberra-0.30 release tarball 核验：`configure.ac`/`src/Makefile.am` 无 `check_PROGRAMS`/`TESTS`，上游无任何自动化测试；`test-canberra` 是 `noinst_PROGRAMS` 演示程序（无断言、需真实音频后端），不计入测试。故不存在可实跑的上游测试，也不存在少报。
- 新增测试用例通过率：**2/2（100%）**，`test_package` 两个 consumer 测试由 GitCode CI 在 OHOS CI worker 上构建并执行通过（built-in null 驱动，无音频设备依赖；OHOS 下经 binary-sign-tool 签名后运行）。

## 补充说明

- 本 PR 只新增 `archives/l/libcanberra/0.30/` 下的 Conan 配方、元数据、test_package，不修改依赖包或基础设施目录。
- 包名 `libcanberra/0.30`、目录 `archives/l/libcanberra/0.30/`（首字母目录 `l/` 与包名首字母一致）均为小写 conan slug。
- 构建要点：`configure.ac` 的 `PKG_CHECK_MODULES(VORBIS, vorbisfile)` 无条件强制，而 OHPCD 制品仓无 vorbis/libogg——配方通过 `VORBIS_CFLAGS=-DHAVE_VORBIS=0` + `VORBIS_LIBS=' '`（两者必须同时非空才走老版 pkg.m4 的 env 绕过分支）跳过 pkg-config，并配两个补丁把 vorbis 解码器守卫在 `#if HAVE_VORBIS` 后（WAV 路径保留）；`--with-builtin=null` 编译唯一内置驱动并关闭 libltdl/DSO；补丁 0003 为 null.c 补上遗漏的 `driver_playing()`；补丁 0004/0005 为 tarball 自带的 2009 版 `config.guess`/`config.sub` 补 HarmonyOS/`linux-ohos` 识别（否则 configure 报 `cannot guess build type`，CI build #40768 实测）；补丁 0006 中和 configure 对 libltdl 的**无条件硬门禁**（`Unable to find libltdl.`，build #40797 实测）——LIBLTDL 只在 `if BUILTIN_DSO` 分支被链接，`--with-builtin=null` 已关闭该分支，故空 LIBLTDL 安全。详见 `manifest.yaml`/`notes.md`。
- 上游测试统计以解包 tarball 实读为准，N=0 已核验、无少报；适配后 2 个补全测试如实列出（详见「补全测试用例说明」）。
