# bali-phy 4.1 - HarmonyOS PC 适配笔记

## 上游事实

- 官方仓：github.com/bredelings/BAli-Phy；tag 4.1 = commit 1fd88e6ebe99a8e32cba486cb324740ca3a343d7（2025-06-11 发布，内部版本串 "4.1-preview"）
- 源码：GitHub 自动归档 https://github.com/bredelings/BAli-Phy/archive/refs/tags/4.1.tar.gz，SHA-256 94ddb61de0983df70ecc5664050e4616a8d24884d7ac961179a2b2865407cd97（设备实测一致）
- 许可证：GPL-2.0（COPYING 为 GPL v2 全文）；vendored immer(MIT)/range-v3(BSL-1.0)/dlfcn-win32(MIT)；vendored Boost.JSON + uuid/convert/rational/compute 头（本配方 patches/boost-extra，183 个文件，逐字 vendor，无 OHOS/musl 修改）为 BSL-1.0
- 构建系统：Meson（>=1.1，C++20）；设备 meson 1.11.1 / ninja 1.13.1 / clang 15.0.4（官方 CI 用 clang17+，本机 clang15 实测可用）
- 测试入口：ninja -C build test（meson test；cairo 缺席时注册 218 条 = 6 直接 + 44 工具 --help + 168 testsuite（2 xfail）；cairo 可用则 219）；tests/run-tests.py 驱动

## 依赖与断点

| 依赖 | 必需/可选 | 4.1 要求 | 采用 |
|------|-----------|----------|------|
| Boost | 必需 | program_options/random/system/chrono/json | boost/1.91.0.1.1：chrono/random/program_options 编译件齐全；system header-only；json/uuid/convert/rational/compute 头见下方断点 |
| Eigen3 | 必需 | eigen3 | eigen/3.4.1（header-only；配方提供 cmake 配置，本配方补写 eigen3.pc 供 meson pkg-config 发现） |
| fmt | 必需(static:true) | fmt | fmt/8.1.1（ohpcd 交付 shared；meson static:true 实际链共享库，运行期随包携带） |
| cereal | 必需 | cereal | cereal/1.3.2（header-only） |
| range-v3 | 系统有则用，否则 internal | - | 不声明；meson 头探测失败后使用上游 internal vendored 副本（上游默认行为） |
| cairo/MPI | 可选 | - | 均关闭/缺省（draw-tree 工具不建；with-mpi=false） |

### Boost 头文件缺口（关键）

- 现有 ohpcd boost 配方全部用 BOOST_INCLUDE_LIBRARIES 只装精选头文件子集，**均未装 boost/json 头**；也没有配方导出 Boost::json 组件。
- bali-phy 硬依赖 <boost/json.hpp>（src/util/json.hh、src/mcon/mcon.H），另含 <boost/convert.hpp>、<boost/rational.hpp>、<boost/compute/detail/sha1.hpp>（boost/uuid 为 convert/compute 的传递依赖）。
- **方案**：不改任何其他库配方。本配方在 patches/boost-extra 内逐字 vendor Boost 1.91 缺失的 header-only 头文件：boost/json + boost/uuid + boost/convert + boost/rational + boost/compute（183 个文件，BSL-1.0，无 OHOS/musl 修改），并在 generate() 搭一个最小 meson boost 根（boost-bundle）：真实 boost 的 version.hpp + vendor 的这些头 + header-only 的 boost/system + 编译件 .so 拷贝，使 meson 五个模块（program_options/random/system/chrono/json）全部解析；真实 boost include 目录经 cpp_args -I 提供。
- Boost.JSON 官方 header-only 用法 = 恰一个 TU 里包含 <boost/json/src.hpp>。补丁 0001 新增 src/util/boost-json-src.cc 并注册进 libutil_sources（所有可执行文件与 builtins 模块都链 libutil，json 符号全局可解析）。
- 该方案不修改 boost/eigen/fmt/cereal 任何配方；已用最小探针（json+chrono+random+program_options 编译/链接/运行）在设备实测通过。

## 运行时自包含

- meson 只在 host=linux/darwin 时设 install_rpath=/../lib/bali-phy；OHOS host_system=harmonyos 分支为空。本配方通过 cpp_link_args 给所有目标统一加 -Wl,-rpath,/../lib，使已安装可执行文件（<pkg>/bin -> ../lib）能找齐随包拷贝的 boost/fmt .so。
- 29 个 builtins 共享模块安装到 <pkg>/lib/bali-phy/（bali-phy 运行期按 get_system_lib_path() 自动发现）；dlopen 依赖解析继承可执行文件 DT_RUNPATH。builtins .so 用 OHOS binary-sign-tool 签名（E083）。
- 随包拷贝：libboost_program_options/chrono/random/container.so + libfmt.so.8.1.1(+so.8/so symlink)。libc++_shared/libc 为系统库。
- package_info：bindirs=[bin]，buildenv/runenv PATH + runenv LD_LIBRARY_PATH=<pkg>/lib。

## 问题与解决方案

| 问题 | 解决 |
|------|------|
| 设备直连 github 下载超时（HTTP:000，IPv6 黑洞；-4 可通） | conan 源下载缓存已含官方 URL 的 tarball（sha256 匹配），create 走本地缓存 |
| boost 头文件缺失（json/uuid/convert/rational/compute） | 配方内逐字 vendor 对应 Boost 1.91 头（patches/boost-extra，183 个文件） + json src.hpp TU（补丁 0001），不改 boost 配方 |
| meson boost 依赖解析 json 失败 | boost-bundle staging 根 + boost_root 属性（meson [properties]） |
| meson 依赖发现缺 eigen3.pc | generate() 写最小 eigen3.pc 到 generators 目录（PkgConfigDeps 只产出 eigen.pc） |
| OHOS /tmp 只读 / HMDFS | 构建在 Conan 缓存目录内进行；test_package 用 $TMPDIR 或当前目录做 scratch |
| HMDFS symlink | 实测支持（tests/run-tests.py 的 data 符号链接可建） |
| musl / clang15 | dl 符号、feenableexcept 等由 meson configure 探测；clang15 C++20 实测可编译 |
| 共享库运行期定位 | 随包拷贝 + $ORIGIN rpath + runenv LD_LIBRARY_PATH |
| builtins dlopen | OHOS 签名（binary-sign-tool） |
| libc++15 缺 std::string/vector/variant 的 <=>（LLVM17 才补全） | 补丁 0002：compare_string/compare_vector 辅助函数 + 手动改写 9 处 operator<=>（Var/Apply/Let/ConPat/Pattern/Alts/ConApp/BuiltinOp/Constant）+ integer_container 用 cpp_int.compare()；并对 4 个原 defaulted 类型（Pattern/Alts/Constant/integer_container）补回 C++20 隐含的 operator==（按 <=>==equal 实现） |
| aarch64/OHOS 跨模块 RTTI：builtins .so 各自定义 Box<T> typeinfo，跨 dlopen 边界的 dynamic_cast 失败（Cannot convert ... from type X to type X；--test/MCMC/haskell 运行时全部命中）| 已修复（用户决策 A）。0003 补丁新增 src/bali-phy/rtti-inject.cc，显式实例化 builtins 需要而 exe 缺省的 14 个 Box<T> typeinfo 并注册进 baliphy_sources；主 exe export_dynamic 后 .so 的弱引用在 musl 下插桩到 exe 定义，跨模块 dynamic_cast 统一。实测 exe .dynsym 导出 54 个 _ZTI3Box*（含所需全部 14 个）；meson test 218 全量 OK，consumer 10/10 PASS。注：12 路并行下 2 个 5d 长分析用例曾超 300s 单测超时（并行争用），单跑/2 进程均通过；上游 CI runner 为双核，等价负载下 218/218 通过。|

## 验证命令（设备）

- conan create（settings: arch=armv8 build_type=Release compiler=clang 15 libc++ cppstd=17 os=OHOS os.version=6.0）
- build() 内：meson configure -> meson build -> --version/--help 冒烟 -> meson test（官方 ninja -C build test 入口）
- test_package：test_bali_phy.sh 10 项 consumer 检查（--version/--help/--test 自检/短 MCMC）
