# c-sig 3.8 适配笔记（libsigc++ 3.8.0）

## 0. 身份鉴定（重要）

任务名 **c-sig / 版本 3.8**。全生态排查后确认 c-sig 即上游 **libsigc++ 3.8.0**：

- conan-center 有 `libsigcpp/3.8.0`（版本逐字吻合，3.8 系最新）；本仓库已适配同库旧版
  `archives/l/libsigc/{2.10.8,2.12.1,3.0.6}`，唯独 3.x 最新版缺位；ohpcd 制品仓无
  c-sig/*、无 libsigcpp/*（与"待适配竞赛目标"一致）。
- 精确名 "c-sig" 在以下生态均不存在独立包/仓库：conan-center、Alpine、Homebrew、
  MacPorts、AUR、Fedora、Gentoo、vcpkg、FreshPorts、pkgsrc、Gitee、Codeberg、
  GitCode、GitHub（C 语言 912 个候选全扫 + 全语言精确名过滤，仅 2 个 0 star 无关
  同名仓库）。
- 结论：任务表的 "c-sig" 是 libsigc++（C++ signals 库）的简写。包名按硬性约束用
  `c-sig`，产物保留上游命名（libsigc-3.0 / sigc++-3.0 / include/sigc++-3.0），
  与仓库 c-ares-dev/c-ares-lite 同源异名先例一致。

## 1. W0 依赖检查

- 上游依赖：**无**（纯 C++17 模板库 + 5 个 .cc：connection / scoped_connection /
  signal_base / trackable / functors/slot_base）。仅要求编译器支持 C++17。
- Conan requires：空。ohpcd 探测 `conan list "c-sig/*" -r=ohpcd` → 0（目标包未发布，符合预期）。

## 2. 源码

- URL：https://github.com/libsigcplusplus/libsigcplusplus/releases/download/3.8.0/libsigc++-3.8.0.tar.xz
  （3.8.0 起 GNOME 官方源与国内镜像只有 3.0–3.6，**GitHub release 是唯一源**，已实测 404/200 确认。）
- sha256：`502a743bb07ed7627dd41bd85ec4b93b4954f06b531adc45818d24a959f54e36`
  本地下载实测 + 与 conan-center libsigcpp/3.8.0 conandata.yml 交叉核对一致。
- 许可证：LGPL-3.0-only（ COPYING 为 LGPLv3；2.x 时代 LGPL-2.1+，3.x 起 relicensed，随 conan-center 口径）。

## 3. 构建系统

tarball 同时带 Autotools（configure.ac）、Meson（meson.build + meson_options.txt）、
CMake（CMakeLists.txt）。**选 CMake**：与 conan-center libsigcpp/3.x.x 相同，且符合
仓库"CMake 优先 CMakeToolchain"策略，ctest 可直接承载上游测试。

库目标：`add_library(sigc-3.0 SHARED <5 个 .cc>)`（写死 SHARED，见补丁）。
头文件装到 `include/sigc++-3.0/sigc++/`，生成头 `sigc++config.h` 装到
`lib/sigc++-3.0/include/`（消费方需要两个 include 路径，已在 package_info 声明）。

## 4. 补丁（全部 `patch -p1 --fuzz=0` 干净应用，验证 = 打到干净树后与目标树逐字节一致）

| # | 文件 | 内容 | 类型 |
|---|------|------|------|
| 0001 | sigc++/CMakeLists.txt | 去掉 add_library 写死的 SHARED（让 BUILD_SHARED_LIBS 生效）；install 增加 ARCHIVE→lib、RUNTIME→bin 目标位置（否则静态库/Windows 产物不落盘） | portability |
| 0002 | CMakeLists.txt | 删 `set(CMAKE_CXX_STANDARD 17)`，让 Conan profile 的 compiler.cppstd 决定标准 | conan |
| 0003 | CMakeLists.txt | 跳过 examples 子目录（仅省时；**tests 保留**，42 个上游测试在 build() 里 ctest 运行） | conan |

与 conan-center 补丁的差异：CCI 同时删掉了 tests；本仓库规范要求尽量跑上游测试，故保留。

## 5. 上游测试

- tests/test_*.cc 共 **42 个**可执行测试（test_accum_iter … test_weak_raw_ptr），
  上游 CMake `enable_testing()` + `add_test` 注册，`cmake.test()`（ctest）运行。
- build() 中 `can_run()` 为真（真机原生构建）时运行全部 42 个；交叉编译时编译但不运行。
- test_package：消费者视角 19 个断言，覆盖信号 connect/emit、默认 last-value 收集器、
  connection 断开、空信号值初始化、ptr_fun/mem_fun/bind、trackable 析构自动断连、
  scoped_connection 作用域、emit 期间自断连安全（全部落到 5 个编译单元的真实代码）。

## 6. 本机验证（Windows，2026-09-08）

本机无编译器/cmake（VS 仅剩 Installer），按工作流做本机可行的静态与轻量验证：

- sha256 校验通过并与 conan-center 交叉核对一致（第 2 节）。
- 三补丁以 `patch -p1 --fuzz=0` 顺序应用到干净树，与编辑目标树 `diff -r` 逐字节一致。
- `python -m py_compile` 两个 conanfile 通过；`conan export` 成功
  （c-sig/3.8#cb95c213f4c93a73e1a4357db6d17f15，conandata + 3 补丁打包正确）。
- `conan graph info`：默认 profile（cppstd=14）按预期 Invalid——`check_min_cppstd(17)`
  门禁生效；`-s compiler.cppstd=17` 时 package_id 正常计算（Missing=未构建，预期）；
  依赖图为空，W0 通过。
- 已对照 ci/conan/build_and_test.sh 逐条预检 G0e/L0a-L0j/L1/L2/L4/L5（详细结论留在
  worktree 本地 archives/c/c-sig/3.8/reports/local-verify.md，reports/ 不入库）。

## 7. 真机验证（2026-09-08，10.62.134.118，已通过）

环境：LAN 直连 `ssh -T -p 2222 currentUser@10.62.134.118`；隔离构建
（CONAN_HOME=$HOME/tmp/csig-conan-home、构建目录 $HOME/tmp/csig-build、离线源码缓存
$HOME/tmp/csig-dl、TMPDIR=$HOME/tmp/csig-tmp）；cmake 3.30.0（ohpc-ci-shadow）、
clang 15.0.4、conan 2.29.1（OHOS 版）；profile 为仓库 CI 版（cppstd=17/libc++/hnp
工具链），设备自带 ~/.conan2/profiles/ohos-aarch64 是 gnu14/libstdc++ 旧版不可用。
jobs=2 防内存（当时设备另有他人 Qt test_package 在默认 ~/.conan2 运行，全程
MemAvailable 12.3–13.5GB，无争抢）。

结果：**conan create exit 0 全绿**——

- 上游 ctest：**42/42 Passed，0 Failed（3.36s）**，仅 5 条上游测试自身 unused-variable
  告警（tests/test_tuple_*.cc），无需处理。
- test_package：第一轮 `test c-sig 3.8: PASS`（19 断言）；新增观察者/事件总线用例后
  第二轮复验 `test c-sig 3.8: PASS` + `test c-sig 3.8 observer: PASS`（16 断言：
  订阅生命周期 disconnect/block/unblock、trackable 订阅中析构、last-value 收集器、
  hide() 适配器、emit 异常逃逸、exception_catch 保活多监听者 emit）。第二轮主包走
  缓存命中（配方未变，"Already installed! 1 of 1"），42/42 属同配方第一轮实测。
- 产物：lib/libsigc-3.0.a（62,732 字节）+ include/sigc++-3.0/sigc++/ 全部头 +
  lib/sigc++-3.0/include/sigc++config.h + licenses/COPYING；lib/cmake、lib/pkgconfig
  已按配方移除。

本机/设备侧坑记录：

1. conan global.conf 的 `core.download:download_cache` **不展开 $HOME**，必须写绝对
   路径（写 $HOME 变量会静默失效 → conan 直连 GitHub 超时两轮后报错）。
2. 设备直连 github.com 连接超时（botan3 同款），按 <sha256[:2]>/<sha256> 预置缓存后
   source() 阶段回落命中（首轮下载尝试超时 1 次后即 "Sources correctly downloaded"）。
3. make jobserver 在 hmdfs 上 mkfifo EPERM（`GMfifo*: Operation not permitted`），
   自动降级直接 -j2，构建不受影响。
4. cmake 3.30 对 CMAKE_SYSTEM_NAME=HarmonyOS 打 "System is unknown" 提示性告警，
   编译/链接正常。
5. nohup 后台启动需用绝对路径 `/data/service/hnp/bin/bash`（PATH 不含 hnp）；
   hmdfs 拒绝 #! exec，脚本一律 `bash xxx.sh` 调用。
6. libsigc++ 3.x `connection::disconnect()` 返回 **void**（2.x 返回 bool）——消费者
   断言须用 `!conn.connected()`；真机 clang 15 对 void 一元取反报
   `invalid argument type 'void' to unary expression`（首轮 observer 用例编译失败
   即此因，修正后复验通过）。

## 8. 下一步

```sh
# 可选 shadow CI 复验：
CI_PACKAGES="archives/c/c-sig/3.8" zsh ci/conan/build_and_test.sh
```

补 issue → rebase origin/main → push fork → 建 PR（feat(c-sig): 3.8 编译完成）。

## 9. 风险与已知限制

- **身份鉴定为推断**（证据链见第 0 节，置信度 ~90%）。若任务表所指另有其库，只需替换
  conandata.yml 源与描述，目录/分支/配方骨架不变。
- clang 15（真机）对 C++17 支持完整，无已知坑；上游对 Clang 仅加警告标志（-Werror 仅
  MSVC），预期无需额外补丁。
- 42 个上游测试中 test_disconnect_during_emit 等涉及异常注入的用例在 OHOS 若失败，
  按 cdb 先例记录平台差异，不擅自改上游测试。
