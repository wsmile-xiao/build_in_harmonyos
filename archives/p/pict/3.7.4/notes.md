# PICT 3.7.4 - 适配笔记

## 概述
PICT（Pairwise Independent Combinatorial Testing，微软）成对组合测试用例生成命令行工具。
本适配目标 HarmonyOS PC（aarch64，musl），官方 v3.7.4 tag：github.com/microsoft/pict。
纯 C++17 / CMake 工程，无第三方依赖；上游测试套件为 perl test.pl + 提交基线。

## 编译环境
- 构建系统: cmake（Unix Makefiles，C++17，-Wall -Werror -pedantic）
- 编译日期: 2026-09-04
- 编译器: clang 15（OHOS BiSheng，-target aarch64-linux-ohos --sysroot OHOS musl sysroot）
- 状态: built（conan-verify G0-G4 全过；L2/L4/L5 因本地无签名执行环境 SKIP；发布上传由 CI release 完成）

## 编译步骤
1. cmake 配置：`cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=<ohos clang++ wrapper>`
2. 全量构建：`cmake --build . -j1` → 产物 cli/pict、api/libpict.a、clidll/libpict.so（仅安装 pict）
3. 打补丁（见下）后干净重编译验证；native（host clang）未打补丁 vs 打补丁 Debug 双构建输出等价（3 模型 3/3 一致）
4. conan create 本地验证：源下载（gh-proxy 镜像）→ 干净构建 → package(bin/pict) → test_package L1 通过
   （test.sh：pict 存在性 + aarch64 ELF 校验；unsigned ELF 无法在 x86 host 执行 → 记 SKIP，合法 ELF）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pictapi.cpp:281` `-Werror,-Wunqualified-std-cast-call` | clang15+ 对 `using namespace std` 下非限定 `move(...)` 告警（上游只按 MSVC/GCC 维护，CMakeLists 仅给 GNU 关过类似项） | 补丁 0002：改 `std::move(...)`（等价，无平台宏） |
| 2 | `mparser.cpp:357` `-Werror,-Wunused-but-set-variable` | `bool found` 仅被 `assert(found)` 读取，Release(NDEBUG) 下 assert 编译掉 → set-but-unused；GNU 有 `-Wno-unused-but-set-variable` 豁免、clang 无 | 补丁 0003：删除 found，循环内 break 定位 index，改 `assert(index < Parameters.size())`（语义等价） |
| 3 | Release 链接 `ld.lld: unknown argument '-flto'` | CMakeLists 用 `LINKER:` 前缀把 `-flto` 直传给链接器；GNU ld 接受该直传，clang/lld 不接受（LTO 应由 clang driver 处理） | 补丁 0001：LTO 行加 `$<$<CXX_COMPILER_ID:GNU>:...>` 守卫（AppleClang 上游已除外）；`--no-undefined` 保留（lld 支持） |
| 4 | Windows 宿主 clang 生成 .d 依赖文件含 Windows 绝对路径 → cmake 增量构建 "multiple target patterns" | 交叉编译器为 Windows exe（BiSheng），由 WSL wrapper 调起，输出 depfile 混入 `C:\`/`D:\` 路径 | 仅影响本机交叉开发流：每次改码后全新 configure+build（conan create 单次全量构建不受影响）。CI 用设备 Linux clang，无此问题 |

## 源码修改
- patches/0001-CMakeLists.txt.patch：Release LTO 链接选项仅对 GNU 编译器生效（clang/lld 兼容）
- patches/0002-api-pictapi.cpp.patch：`move(` → `std::move(`
- patches/0003-cli-mparser.cpp.patch：去掉 NDEBUG 下 unused 的 `found`，用 `assert(index < Parameters.size())`
（全部为编译器可移植性修复，无 `__OHOS__`/平台宏；与上游行为等价，见验证结果）

## 依赖版本
- 无外部依赖（纯 libc/libc++ + musl）
- 工具链：OHOS BiSheng clang 15.0.4（C++17，-stdlib=libc++，链接 -lc++ -lpthread，动态加载器 /lib/ld-musl-aarch64.so.1）

## 验证结果
- 交叉产物：ELF 64-bit LSB PIE, ARM aarch64, dynamically linked, interp /lib/ld-musl-aarch64.so.1；NEEDED libc++.so + libc.so
- conan-verify：G1/G0/G2/G3/G4 PASS（reports/conan-verify-report.md）
- 行为等价：host clang Debug 下 pristine(带 -Wno 豁免) vs 本补丁集 输出逐字节一致（3 模型含 submodel 语法，3/3）
- test_package L1：pict 打包完整，aarch64 ELF 校验通过（SKIP 计数=签名限制，同 net-tools 先例）

## 注意事项
- 上游完整测试套件（test.pl + baselines）需运行 pict 本体；OHOS unsigned ELF 需 sign-elf 签名后才能在真机执行，真机运行验证留待有签名环境的后续会话/CI
- conandata.yml 使用官方 GitHub 单源 URL（R39），sha256 对官方 release 包；镜像回退由 CI 自动追加
- commands.json 已声明（R38，type=tool，命令 pict）
---

**编译结束**: 2026-09-04 02:36
**最终状态**: built
