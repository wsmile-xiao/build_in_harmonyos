# libical 4.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27
- 状态: verified

## 遇到的问题与解决方案
- 缺少 glib，禁用 GLIB 绑定
- 作为 `KF6::CalendarCore` 的前置依赖，补充 Conan recipe，并使用
  `find_package(LibIcal)` 验证官方 CMake config 可被下游消费。
- 关闭 Java、GLib/GObject/Vala、文档、示例、VZIC、ICU 和 BerkeleyDB
  路径，只保留 Akonadi calendar 链需要的 iCalendar/vCard C 库。
- 启用内置 timezone 数据，避免依赖当前 OHOS 包配置中不存在的系统
  zoneinfo 树。
- 补充 OHOS 共享库链接规则，并在安装后签名生成的 ELF 文件，保证
  `LibIcal` CMake 包可以被后续库消费。
- 2026-08-31 本地 Windows/GCC 预验证时，Conan `perl/5.42.2` 仅支持
  Linux/OHOS native，Windows 改用 `PERL_EXECUTABLE` 指向 Git for
  Windows 自带 Perl。
- 2026-08-31 本地 Windows/GCC 预验证时，MinGW GCC 8 会在上游
  OpenSSF hardening flags 上触发编译器 ICE；补丁仅在 Windows 跳过该
  hardening include，OHOS 仍保留原路径。
- 2026-08-31 本地 Windows/GCC 预验证时，固定 CMake/Ninja/CTest 绝对路
  径并限制 `tools.build:jobs=2`，避免 PATH 差异和本机高并发构建。
- 2026-08-31 修复 `builtin_timezones` 的 zoneinfo 相对路径，使
  `build/Release/bin` 下的 CTest 可以找到 `../../zoneinfo`。

## 验证
- 源码 SHA256:
  `7c1d8b780ce305a8823e5824ec4d7eb05d85ae8f808836b495aa37b0c3d08337`
- OHOS `conan create` 验证通过。
- 上游 CTest: 48/48 通过；没有注册测试被跳过。
- Conan `test_package`: 1/1 通过。
- 直接消费验证:
  `PASS: libical generated VEVENT summary` 和
  `PASS: libicalvcard generated FN property`。
- Full reference:
  `libical/4.0.1#c3550e38c733b3e318a242004f1aea9d:01d92cf349a0dd98ff915f4bd99a04430171517f#d1e40e9a4fd6831e4cf98ecab1b45a0f`。
- Windows/GCC 本地预验证命令:
  `conan create archives/l/libical/4.0.1 -pr:h=win-gcc -pr:b=win-gcc -c tools.cmake:cmake_program=H:/OpenHarmonyOsCompetition/.tools/conan-venv/Scripts/cmake.exe -c tools.build:jobs=2 --build=missing`
- Windows/GCC 本地预验证结果: PASS；上游 CTest 48/48 通过，Conan
  `test_package` 1/1 通过，直接消费输出包含 `PASS: libical generated
  VEVENT summary` 和 `PASS: libicalvcard generated FN property`。
- Windows/GCC 本地 Full reference:
  `libical/4.0.1#fcef42f989aea9633317bd6e4506b913:e70bbcdf386d71b60ea84c0fc5a87a197dae018f#2f1ec4538c86addf538f2e21e518a978`。
- 2026-08-31 端口检查: `33332` 与 `56267` 均连接拒绝，本轮未重新跑
  OHOS 真机构建。

## Upstream Tests Not Run

无。`BUILD_TESTING=ON` 执行了完整上游 CTest，48/48 通过。

## 交付物
| 文件 | 说明 |
|------|------|
| libical-4.0.1-ohos-aarch64.tar.gz | 预编译包 |
