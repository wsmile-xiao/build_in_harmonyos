- **三方库名称**：libisofs
- **上游版本**：1.5.6
- **上游仓库地址**：https://files.libburnia-project.org/releases/libisofs-1.5.6.tar.gz（libburnia 官方发布源；开发仓库 http://libburnia-project.org）
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 tarball 无 test/ 目录；Makefile.am 中单元测试被上游注释禁用（ticket 147: "The test code does not use the API"） |
| 集成测试 | 0 | 无 ctest/pytest 注册；`make check` 无注册目标（Nothing to be done for 'check'） |
| 其他测试 | 0 | — |
| **合计** | **0** | 上游未提供可运行测试 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无测试，未新增单测 |
| 集成测试 | 0 | 不变 | 上游无测试 |
| 鸿蒙特有测试 | 0 | 新增 | — |
| **合计** | **0** | **不变** | — |

> 注：适配后验证由 test_package 消费者测试承担（见「补全测试用例说明」），非上游单测。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：test_package 消费者测试 1 个（test.c），实际调用 libisofs API：iso_lib_version()（运行时版本与头文件 iso_lib_header_version_major/minor 一致性校验）、iso_init()、iso_finish()。
> - **补全原因**：上游库仅包含 demo 示例（Makefile.am 中单测被上游注释禁用），无正式测试框架；按 R51 三步法清点后，以消费者视角测试验证库可链接、API 可用。
> - **新增测试文件清单**：
>   1. `archives/l/libisofs/1.5.6/test_package/test.c` — 消费者测试：iso_lib_version/iso_init/iso_finish 实际调用 + 版本一致性断言（assertion_count=3）
>   2. `archives/l/libisofs/1.5.6/test_package/CMakeLists.txt` — CMake 构建 + CTest 注册；含 HarmonyOS unknown platform 下 find_library 前缀/后缀声明

## 验证结果

- 编译状态：通过（conan create exit 0；conan-verify G0-G4 全部 PASS；W3 本地 CI 模拟 build_and_test.sh 100% 通过）
- 上游测试用例通过率：0/0（上游无测试）
- 新增测试用例通过率：1/1（100%，CTest: `1/1 Test #1: test_libisofs ... Passed 0.03 sec`）

## 补充说明

1. **OHOS 平台三元组**：libisofs 上游 config.guess（2012 版）无法识别 HarmonyOS uname 输出、config.sub 无 ohos 系统条目。配方在 OHOS 下显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`，并携带补丁：
   - `0001-config.sub.patch`：config.sub 的 KERNEL-OS 组合列表与有效 OS 列表各加 `linux-ohos*`（POSIX 兼容方式，R8 允许 config.sub 修复，无平台宏）。
   - `0002-configure.patch`：config.status 临时目录创建 umask 077→002。HMDFS 上 umask 077 建出 owner-only(2700) 目录，非 owner 的组内成员进程无写权限，config.status 报 `cannot create ./confXXXXXX/subs1.awk: Permission denied`（等价知识 E011）。直接以 patches 修改生成文件 configure 的理由：autotools 依赖的 aclocal-1.14 在构建环境缺失，无法从 configure.ac 重新生成 configure。
2. **zlib 依赖**：zisofs filter 使用 zlib（compress2/uncompress/compressBound），静态归档不捆绑符号，`cpp_info.system_libs=["z"]` 供消费者链接 -lz。
3. **CMakeDeps find_library 修复（路径 B 知识草稿）**：CMake 无 Platform/HarmonyOS.cmake，`CMAKE_FIND_LIBRARY_SUFFIXES` 为空导致 CMakeDeps 报 `Library 'libisofs' not found in package`。test_package/CMakeLists.txt 在 HarmonyOS 下显式声明 `CMAKE_FIND_LIBRARY_SUFFIXES=".so;.a"` 与 `CMAKE_FIND_LIBRARY_PREFIXES="lib;"`。正式图谱无此条目，新增草稿 `knowledge/drafts/DRAFT-libisofs-1.5.6-cmake-unknown-platform-find-library-suffix.kv/.md`（路径 B）。
4. **R51 上游测试申报**：清点证据见 notes.md 申报表（上游无 test/ 目录、单测被注释禁用、make check 无注册目标）；实测 make check exit 0（无目标）。
5. 静态库构建（--enable-static --disable-shared），纯库类型无需 commands.json（R38）。
