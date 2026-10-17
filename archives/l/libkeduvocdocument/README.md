# libkeduvocdocument

## 简介

libkeduvocdocument（上游 CMake 工程名 `LibKEduVocDocument`）是 KDE 教育软件组的词表文档
库，导出 `libKEduVocDocument.so.5` 与 `KEduVocDocument` C++ API，供 Parley、KWordQuiz、
KHangman、Kanagram 读写词表文件。

支持格式：KVTML 2.0（读写）、KVTML 1.0（只读）、KVTML/KVTL、CSV（读写）、Pauker、
Vokabeln、WordQuiz（wql）、XDXF（只读）。

- 源码仓库：https://invent.kde.org/education/libkeduvocdocument
- 发布工程：KDE Gear 26.04.0（`v26.04.0` / commit `e5bc26b8d1da92b1823b2d8cd0aac1fbd697c387`）

## 依赖

- qtbase/6.11.1（`Qt6::Xml` PUBLIC 链接；autotests 需 `Qt6::Test`）
- ki18n/6.26.0（`KF6::I18n`）
- karchive/6.26.0（`KF6::Archive`）
- kio/6.26.0（`KF6::KIOCore`；KIOCORE_ONLY 形态即可满足）
- libxml2/2.15.3（OHOS SDK lld 链接期需要 `libxml2.so.16`）
- ecm/6.26.0（`tool_requires`）
- 传递：kconfig / kservice / kcrash / kcoreaddons（kcoreaddons 亦为测试期直接依赖）、gettext、zlib、xz、openssl

## 构建产物

- `lib/libKEduVocDocument.so.5.1.0`（SONAME `libKEduVocDocument.so.5`，SOVERSION 5）
- `include/libkeduvocdocument/*.h`（19 个，含 `keduvocdocument.h` 等 17 个导出头）
- `lib/cmake/libkeduvocdocument/LibKEduVocDocumentConfig.cmake` + `LibKEduVocDocumentTargets.cmake`

纯库包，无 `bin/` 可执行产物 ⇒ 不需要 `commands.json`。

## OHOS 适配

- 构建系统：cmake（CMake 3.16 + ECM + KF6 + Qt6）
- 编译器：clang 15.0.4（OHOS aarch64，libc++，cppstd=17）
- 补丁：2 个
  - `patches/0001-LibKEduVocDocumentConfig.cmake.in.patch` — 上游打包缺陷（平台无关）
  - `patches/0002-keduvocdocument-CMakeLists.txt.patch` — E537 可重定位链接（OHOS）

## OHOS 适配要点

1. **E537 生产者侧**：ohpcd 发布的 KF6 依赖库（karchive/ki18n/kcoreaddons/kconfig/kservice/
   kcrash）**没有 DT_SONAME**，直接用 `KF6::*` 导入目标链接会让 ld 把构建机的 Conan 缓存
   绝对路径写进产物的 DT_NEEDED。补丁 0002 改为按 basename 链接
   （`-l:libKF6*.so` + `target_link_directories`）并显式补 include 目录；产物 DT_NEEDED
   9 条全部为 basename。
   注意：CMake 4.1.2 下改写 `IMPORTED_SONAME` / `IMPORTED_NO_SONAME` **无效**（已用最小工程
   实测），且 KF6 目标只设置 `IMPORTED_LOCATION_<CONFIG>`，读 generic 属性会得到 NOTFOUND。
2. **E537 消费者侧**：已发布的 `kio/6.26.0` 二进制内嵌构建机绝对 DT_NEEDED
   （`/…/.cache/conan2/p/<hash>/p/lib/libKF6*.so`），musl 直接按绝对路径解析、`LD_LIBRARY_PATH`
   无法覆盖。配方在 `build()` 中把这些路径物化为指向当前缓存的兼容符号链接
   （akonadi 25.12.3 先例）。
3. **CMake 无 HarmonyOS 平台模块**（E092）：`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 手工补
   `-Wl,-soname,`，否则产物缺 DT_SONAME。
4. **上游测试注册**：`keduvocdocument/tests/CMakeLists.txt` 只调用 `ecm_mark_as_test()`
   （ECM 实现仅设 `EXCLUDE_FROM_ALL`，不 `add_test`），故 ctest 只有 8 项；配方额外显式运行
   `sharedkvtmlfilestest` 与 `converter`（上游样例 round-trip）。
5. **平台限制**：`saveAs()` 写入新建 `QTemporaryDir()`（0700）在 HarmonyOS 6.0 上会因
   autosave/lock 伴随文件创建失败而返回 `FileCannotLock`；写入 `QDir::tempPath()` 正常。

## 参考

- 适配笔记：`archives/l/libkeduvocdocument/26.04.0/notes.md`
- 验证报告：`archives/l/libkeduvocdocument/26.04.0/reports/conan-verify-report.md`
- 依赖分析：同工作区 `libkeduvocdocument-26.04.0-deps/DEPENDENCY-REPORT.md`
