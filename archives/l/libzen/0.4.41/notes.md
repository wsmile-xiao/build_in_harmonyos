# libzen 0.4.41 适配笔记

## 编译环境
- 构建系统: cmake（入口 `Project/CMake/CMakeLists.txt`，tarball 顶层无 CMakeLists）
- 编译日期: 2026-09-27
- 编译器: OHOS 交叉 clang 15（/data/service/hnp/bin/clang++，aarch64-linux-ohos）
- 构建方式: conan 配方 `conan create`（os=OHOS, arch=armv8, Release）
- 状态: built

> 历史说明：2026-05-20 曾有一次设备端手工 cmake+make 编译（产物装
> `/storage/.../usr/local`，交付预编译 tarball），无 conan 配方且当时
> manifest 误标 published。2026-09-27 制品仓复核确认 ohpcd 无 libzen
> 配方，本次补齐完整 conan 配方并修正状态。

## 源码

- 下载源: https://github.com/MediaArea/ZenLib/archive/refs/tags/v0.4.41.tar.gz
- sha256: `45d5173fa0278f5264daa6836ae297aa303984482227d00b35c4f03929494c8f`
- 与 mediaarea.net 官方发布包内容等价（两源 Thread.cpp 逐文件 sha 一致）；
  mediaarea.net 直链在 CI Worker 不可达（libmediainfo/25.07 已实测），
  故 conandata 用 GitHub 源。
- 源码布局：`Project/CMake/CMakeLists.txt` 通过 `../../Source` 相对引用
  `Source/ZenLib/`，故配方 `get(strip_root=True)` 保留整树、
  `cmake.configure(build_script_folder="Project/CMake")`。

## 补丁

| 补丁 | 内容 | 根因 |
|---|---|---|
| 0001-Source-ZenLib-Thread.cpp.patch | `Thread::ForceTerminate()` 将 `pthread_cancel` 声明为 **weak 弱符号**并在调用前判空（libc 探针，两处 hunk：文件头 include 区声明 + ForceTerminate 内判空调用） | OHOS musl 的 libpthread **无 `pthread_cancel` 符号**（`nm -D` 无符号 + 交叉链接探针 `undefined symbol: pthread_cancel` 实证）。weak 声明使有该符号的 POSIX libc 仍绑定真函数、保持上游取消语义；OHOS 等无符号 libc 上解析为 NULL、跳过调用（协作式终止仍可经 `RequestTerminate()` 完成）。**不引入任何平台条件编译宏**（R8：补丁默认禁平台宏，弱符号 libc 探针属合法例外）。 |

补丁文件格式：两处最小 unified-diff hunk，**CRLF 行尾**（与上游 Thread.cpp
源行尾一致）。选 CRLF 的原因：实测 CRLF 是唯一同时通过 conan `patch_ng`
（apply=True，字节级校验）与 `git apply --check`（exit 0）的变体；LF 版
`git apply` 报 "patch does not apply"。无时间戳（规避 conan 2.29 的
1970→/dev/null 静默空转坑）。原 603 行 `/dev/null` 整文件补丁已替换
（diff -ruN 形式对 patch_ng 有 /dev/null 新文件约定风险）。

## 构建关键参数

| 参数 | 值 | 原因 |
|---|---|---|
| BUILD_SHARED_LIBS | OFF（默认） | 与仓库主流一致；shared 亦支持 |
| CMAKE_POSITION_INDEPENDENT_CODE | ON | fPIC 静态库 |
| ENABLE_UNICODE / LARGE_FILES | ON | 上游默认值显式化，保证跨主机确定性 |
| CMAKE_POLICY_VERSION_MINIMUM | 3.5 | 上游 `cmake_minimum_required(3.1.0)` 与 CI CMake 4.x 不兼容（CMake 4 移除 <3.5 兼容） |

依赖：**无第三方依赖**。requirements() 为空是设计结果：上游 CMake 仅
`find_package(Threads)`（-lpthread，系统库，package_info 以
system_libs 声明）+ 可选 PkgConfig（仅生成 .pc，缺失不致命，且 package
步骤移除上游 .pc，消费者走 conan 生成物）。

## 上游测试体系

- 上游**无测试框架**：全仓无 `add_test`/ctest/CxxTest，CMake、Makefile.am、
  configure.ac 均未纳入任何测试。
- 唯一"测试"文件 `Source/Example/ZenLib_Test.cpp`（47 行 demo）：
  未被任何上游构建纳入，末尾 `system("PAUSE")` 为 Windows 交互等待，
  OHOS 非交互 CI 下会挂死 → **不可直接运行**，故不静默照搬。
- test_package 采用自研功能断言（Ztring UTF-8 编解码、ZtringListList
  解析、File 存在性等，覆盖核心 API），并在 MANIFEST.yml 中如实记录
  上游测试受限原因。

## HarmonyOS 风险面排查结论

| 项 | 结论 | 证据 |
|---|---|---|
| pthread_cancel | 唯一必须补丁点 | 见上 |
| SSE2 / emmintrin.h | 无风险 | `ZENLIB_MEMUTILS_SSE2` 全源码无 #define，SSE2 分支永不编译 |
| system()/fork/exec | 库本体 0 处 | 仅不可用的 Example demo 有 |
| 非线程安全 API | 上游已适配 | 0.4.39 起 gmtime_r/localtime_r 路径（CMake 探测 HAVE_GMTIME_R 等） |
| __ANDROID_API__ 条件宏 5 处 | OHOS 未定义该宏，走标准 UNIX 分支，行为正确 | grep 全量核对（Dir/File/Thread.cpp、int128s/u.h 各 1 处） |

## 验证

本地 `conan create`（--profile=ohos-nip4，os=OHOS, arch=armv8, Release）已端到端全绿：
下载（GitHub tag 源，sha256 校验）→ apply_conandata_patches → CMake 交叉编译
（clang 15，库本体 100%）→ 打包 → test_package 编译运行。

test_package 18/18 断言全部通过：
- Ztring：空/非空、From_Unicode→To_Unicode、From_Local→To_Local、
  From_UTF8→To_UTF8（CJK）、UTF-8 size() 字符计数、From_Number(int64u)、
  operator+=、operator=
- ZtringListList：3 行解析、Read(1,1)、Read(0) 整行
- File::Exists 真/假；FileName::Extension_Get
- Thread：Run==Ok、Entry 在 worker 线程完成、RequestTerminate 结束运行态、
  Sleep no-crash（受保护 Sleep 经公开包装方法 SleepMs 触发，覆盖 OHOS 守卫路径）

绿色日志留档于 `reports/libzen-0.4.41-conan-create.log`（reports/ 目录为
gitignore，不随 PR 提交，供复现核验）。最终以 CI 门禁结果为准。
