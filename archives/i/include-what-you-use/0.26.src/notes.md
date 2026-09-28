# include-what-you-use 0.26.src 适配笔记

## 编译环境
- 构建系统: CMake（上游要求 >=3.13.0；本机实测 4.1.2）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4（设备 SDK /data/service/hnp），C++17
- 目标平台: aarch64-linux-ohos（OHOS 真机原生构建，conan os=OHOS arch=armv8）
- 状态: 进行中（收尾时更新 published/built/failed）

## 依赖版本（W0 已核验，均在 ohpcd 制品仓）

| 依赖 | 版本 | 来源 PR | 备注 |
|------|------|---------|------|
| llvm | 22.1.0 | #4759 | 已合入；LLVMConfig 提供方 |
| clang | 22.1.8 | #3868 | 已合入；ClangConfig/clang-cpp 提供方，含 LLVM+Clang 一体（llvm-project 单仓构建） |
| zlib | 1.3.2 | #3929 | 已合入 |
| zstd | 1.5.7 | #1900 | 已合入 |
| xz | 5.8.3.1 | #5991 | 已合入 |
| libedit | 20240808 | #2845 | 已合入 |
| z3 | 4.15.4 | #4801 | 已合入（可选） |

> IWYU 0.26 官方 release note：仅兼容 Clang/LLVM 22（"Compatible with Clang 22"），与 clang/22.1.8 对齐。

## 源码与版本号

- 版本号 `0.26.src`：与官方源码包名对齐（官方 include-what-you-use.org 声明 "equivalent to the `0.26` tag and `clang_22` branch"），全程统一（init-build/版本目录/conanfile/finish/submit/result/PR 标题）
- conandata 源 URL: `https://codeload.github.com/include-what-you-use/include-what-you-use/tar.gz/refs/tags/0.26`（GitHub 官方归档主机，tag 0.26 固定）
  - 选用原因（实测 2026-09-27）：官方 release 资产链 `releases/download/0.26/0.26.tar.gz` 本机 HTTP 404（设备出口拦截层）；`github.com` 主域 curl TCP 连接超时不可达；`codeload.github.com`（GitHub 自有 tag 归档后端，与 tag 归档同源）实测可下载完整 tarball
- 源码 sha256: `ca3f157a5e6bf293cfb2fea585b103ec87245d02eaee0b6ab832665e740016eb`（1146969 字节）

## 上游测试清点（R51，构建前清点 2026-09-27，tarball 实地核对 + 脚本实测）

| 类型 | 入口 | 上游数量 | ctest 注册 | 说明 |
|------|------|----------|------------|------|
| C++ 单元测试（gtest，vendor/googletest 自带） | unittests/*.cc | 7 文件（5 测试 + main + helpers）；**仅 3 个测试文件**编入 iwyu-unittests 二进制 | 1（iwyu-unittests，单入口跑全部 gtest 用例，用例数实测回填） | lexer_utils / path_util / string_util（include_picker_test、output_test 在目录中但未列入 CMake 目标） |
| e2e-C | tests/c/*.c | 9 | 9（run-test-c.*） | run_iwyu_tests.py 每文件：iwyu 分析 + FileCheck 校验 |
| e2e-C++ | tests/cxx/*.cc | 191 | 191（run-test-cxx.*） | 同上 |
| e2e-driver | tests/driver/*.c | 24 | 24（run-test-driver.*） | 同上 |
| bug 回归套件（XFAIL） | tests/bugs/<issue号>/ | 56 目录 / 137 文件 | 0（默认不注册；需 --extra-suite=bugs 显式加入） | 复现 open issue（IWYU_XFAIL 标记）；README 声明主要在 Linux GCC/Clang 环境运行 |
| stdin 冒烟 | tests/stdin/ | 5 | 0（iwyu-run-stdin-tests.bash 手动执行） | 仅验证 iwyu 无错误完成 |
| Python 测试 | fix_includes_test.py / iwyu_tool_test.py（顶层） | 2 | 2 | fix_includes CLI 与 iwyu_tool.py |
| **合计** | | ctest 内测试文件 229（3 gtest + 224 e2e + 2 py） | **227 条 ctest 条目（1 gtest + 224 e2e + 2 py）** | |

> 口径依据：`python3 run_iwyu_tests.py --list-test-files` 实测 224 条（c=9 / cxx=191 / driver=24）；CMakeLists 注册 `iwyu-unittests` + 每文件 `run-test-*`（仅 Python3 找到时）+ 2 个 py 测试；bugs 套件仅当 `--extra-suite=bugs` 时注册（CMakeLists 的 execute_process 未传该参数 → 默认不注册）。
> `SKIP_RETURN_CODE 77`（SKIP 码）仅作用于 224 条 run-test-*。统计口径：N=注册总数 227，M=通过，F=失败，S=跳过。
> ctest 实际条目数以 `ctest -N` 输出为准（configure 后回填）。

## 遇到的问题与解决方案（难度台账）

| # | 问题 | 根因 | 修复 | 类别（平台/构建系统/依赖/工具链） |
|---|------|------|------|------|
| 1 | init-build 主源 URL（releases/download/0.26/0.26.tar.gz）HTTP 404；备用链（github.com/archive）连接被重置；curl 直连 github.com:443 TCP 超时 | 设备出口网络对 github.com 主域不可达（拦截层返回 404/断连） | 改走 GitHub 官方归档后端 codeload.github.com（tag 0.26 固定），curl 实测下载成功，sha256 已记录；conandata 记录该 URL | 构建系统（源获取） |
| 2 | init-build 将构建系统误判为 autotools（模板选择走 autotools 分支） | 启发式检测未识别 CMake（lang-preflight 正确判为 cmake） | 不影响：配方按 CMake 手写；conanfile 中 layout 按 cmake 声明 | 构建系统 |
| 3 | configure 失败：HandleLLVMOptions.cmake:249 "Unable to determine platform"（设备 `uname -s`=HarmonyOS，LLVM 22 平台分支无 HarmonyOS） | OHOS 内核标识不在 LLVM 已知平台表 | 造 `Platform/HarmonyOS.cmake`（内容 `include(Platform/Linux)`）放 build 目录 platform-modules/，经 `-DCMAKE_MODULE_PATH` 注入；禁设 CMAKE_SYSTEM_NAME（保持 CMAKE_CROSSCOMPILING=FALSE，llvm/clang 配方同款先例） | 平台 |
| 4 | iwyu 运行报 `fatal error: 'vector' file not found`（C++ 标准库头找不到） | clang 包不含 C++ 标准库头；iwyu 内置 driver 默认搜索路径（/usr/include/c++…）在 OHOS 设备不存在 | 标准库头 = 设备 SDK `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/libcxx-ohos/include/c++/v1`，经 `-isystem` 注入（system include 分类，与上游 CI /usr/include 语义一致）；builtin 头（stddef.h 等）由 IWYU_RESOURCE_DIR=../lib/clang/22（clang 包 resource dir）提供 | 平台（工具链） |
| 5 | C 库头（stdio.h 等）在 C++ 模式下解析异常：`cstddef:50: no member named 'nullptr_t'`（CPATH 方案）/ `stdio.h:249: unknown type name 'uint64_t'`（shim builtin 覆盖方案） | OHOS sysroot 为 musl 系 C 库（`__NEED_*` + `bits/alltypes.h` 机制）；`::nullptr_t` 仅编译器 builtin stddef.h 在 C++ 模式提供；用 CPATH 类环境变量注入头目录会被 clang 归为 user include（破坏 IWYU 归属判断，25 条测试失败）；用 builtin 头覆盖 C 库 stdint.h 破坏 musl `__NEED_*` 链 | 最终方案：`-isystem` 注入（builtin 头优先于 sysroot，顺序经 clang driver 保证：builtin stddef.h 先行提供 nullptr_t，C 库头走 sysroot -isystem）——224 条 e2e 全部按此跑通 | 平台（工具链） |
| 6 | clang-cl 模式测试（clmode/preprocess_msvc/use_pch_msvc）注入 `-isystem` 报 "unknown argument ignored in clang-cl"；`--driver-mode=cl`（LLVM 18+ 新式 cl 模式选择，IWYU_ARGS 实测为此写法）未被识别 | clang-cl driver 拒绝 -isystem/--sysroot 等非 MSVC 风格参数；测试文件 IWYU_ARGS 实为 `--driver-mode=cl …`（早期 grep 视图为 `-clang-cl`，文件系统瞬时视图不一致导致误判） | 测试 wrapper 脚本按参数分支：cl 模式纯透传（这 3 条测试不含系统头），普通模式前置 3 个 -isystem；wrapper 经 CTestTestfile.cmake（build 目录生成物）替换 iwyu 路径注入，不改上游源码 | 平台（工具链） |
| 7 | dashdash 测试（IWYU_ARGS=`-c --`）注入 -isystem 报 "no such file or directory: '-isystem'" | run_iwyu_tests.py 把 IWYU_EXTRA_ARGS 追加在测试参数之后（`--` 之后→被当作输入文件） | wrapper 把 -isystem 前置到所有参数之前（`--` 之前=driver 侧），测试通过 | 构建系统（测试） |
| 8 | 二进制运行被 OHOS XPM 拒绝（未签名） | OHOS 要求可执行文件带代码签名 | `objcopy --remove-section .codesign` 去旧段 + `binary-sign-tool sign -selfSign 1` 自签（llvm/clang 配方同款流程），实测 iwyu --version 正常 | 平台 |
| 9 | py 测试（fix_includes_test）要求 `IWYU_BINARY` 环境变量（fix_includes.py:148 `os.environ['IWYU_BINARY']` 无默认值） | 上游 CI 在 Actions 环境注入该变量 | ctest 环境显式 `IWYU_BINARY=<wrapper>`；iwyu_tool_test 自管理该变量（seed/restore）不受影响 | 构建系统（测试） |
| 10 | 设备 /data/service/hnp/bin/grep 为损坏 ELF（"cannot execute binary file"），shell grep 静默失败导致多次误判"无匹配" | 设备预装工具链个别二进制不可用 | 关键文件内容核验改用 python3 逐行读（对 .work 源码文件一律如此，防 HMDFS 视图不一致） | 工具链（设备） |
| 11 | conan create source() 报 `BadZipFile: File is not a zip file` | codeload URL 的 basename 是 tag 名 `0.26`（无扩展名）；conan 2.29 `get()`→`unzip()` 按**文件名后缀**判定压缩格式（conan/tools/files/files.py），无后缀回退 zip | conandata sources 增加 `filename: "include-what-you-use-0.26.tar.gz"`（get() 透传给 unzip 的判定名；sha256 校验仍对实际内容，不受影响） | 构建系统（conan） |
| 12 | C3 消费者用例首跑断言失败（IWYU 已改写 1 文件但 grep 不通过） | 断言 `! grep -F 'consumer_b.h'` 误匹配**用例文件自身注释**（注释文字描述了 consumer_b.h 的用例背景）；另发现 conan 2 test_package 的 build_folder=source 目录，工作文件 c3_run.cc 落在 test_package/ 内（污染归档树） | 断言精确到 include 行（`! grep -F '#include "consumer_b.h"'`）；命令尾部 `; rc=$?; rm -f {work}; exit $rc` 保证工作文件测试后删除 | 构建系统（测试） |

## 编译步骤（手动适配实测，conanfile 按此复现）

```
# 前置：conan install 依赖（clang/22.1.8 含 LLVM/Clang 一体）；设备 clang/clang++ 15.0.4 在 PATH
mkdir -p $BUILD/platform-modules/Platform
echo 'include(Platform/Linux)' > $BUILD/platform-modules/Platform/HarmonyOS.cmake

cmake -S $SRC -B $BUILD \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_MODULE_PATH=$BUILD/platform-modules \
  -DLLVM_DIR=<clang包>/lib/cmake/llvm \
  -DClang_DIR=<clang包>/lib/cmake/clang \
  -DIWYU_RESOURCE_RELATIVE_TO=iwyu \
  -DIWYU_RESOURCE_DIR=../lib/clang/22 \
  -DBUILD_SHARED_LIBS=OFF
# 实测：LLVM 22.1.8 检出、Python3 检出、ctest -N Total Tests: 227；rc=0

cmake --build $BUILD -j4      # 实测 <2min，0 error 0 warning
# 产物：bin/include-what-you-use（4.2MB，动态链 libclang-cpp.so+libLLVM-22.so）
#       bin/iwyu-unittests（1.0MB，内置 googletest）

# OHOS XPM 自签（llvm/clang 配方同款）：
objcopy --remove-section .codesign <bin> <bin>.tmp && mv <bin>.tmp <bin>
/data/service/hnp/bin/binary-sign-tool sign -inFile <bin> -outFile <bin> -selfSign 1
# 实测输出 "write code sign data success"；iwyu --version =
# "include-what-you-use 0.26 based on clang version 22.1.8"

# 全量测试环境（详见"注意事项"）：
ln -s <clang包>/lib/clang/22 $BUILD/lib/clang/22        # builtin 头桥接（IWYU_RESOURCE_DIR 解析）
# ctest -j4，227 条，实测 20.98s
```

## 源码修改

**无。** 上游源码（$SRC/.work 树）零修改：
- `Platform/HarmonyOS.cmake` 为 build 目录新增模块（CMAKE_MODULE_PATH 注入），非上游文件修改
- 测试 wrapper 脚本、CTestTestfile.cmake 路径替换均为 build 目录产物
- `patches/` 目录为空（R8 无平台宏、无源码补丁）

## 验证结果

### 上游全量测试（R51 步骤 2，OHOS 真机实测 2026-09-27）

- 命令：`ctest -j4 --output-on-failure`（build 目录，wrapper+环境见"注意事项"）
- 结果：**N=227，M=223 通过，S=1 跳过，F=3 失败，通过率 98.2%**（目标 ≥90% 达成）；Total Test time 20.98s
- 跳过 1 条：`cxx.test_ms_inline_asm`（SKIP 码 77 合法跳过——MSVC 专属 inline asm 测试，上游在非 MSVC 环境即跳过）
- 失败 3 条（均为 OHOS 标准库与上游 CI 标准库的实现差异，非适配缺陷，逐条说明）：
  1. `cxx.test_badinc`：`#include <string>` 的 "for" 注释不同——期望 `for basic_string, string`，实测 `for allocator, basic_string, char_traits, string`。OHOS libc++ 的 std::string 内部经 allocator/char_traits 间接使用，libstdc++（上游 CI）不展开；include 建议本身一致（都建议加 <string>）
  2. `cxx.test_libbuiltins`：`std::pow(float, float)` 归属诊断不同——实测输出 `pow(float, float) is defined in <cmath>`（libc++ 的 pow 重载经 cmath using-decl 可见），上游期望的 regex `std::pow\(float,\ float\)\ is.*cmath` 无对应行；libc++/libstdc++ 的 <cmath> 重载声明方式差异
  3. `cxx.test_std_size_t`：期望 iwyu 建议 `stdio.h → cstdio` 替换（glibc 下 size_t 经 stdio.h 的归属判定），OHOS musl sysroot 下 iwyu 判定 `#include <stdio.h>` 已正确（musl stdio.h 直接定义 size_t 路径，默认 std_symbol_map 归属判定不同）

### 消费者用例（R34 实质测试，C1-C3，OHOS 真机实测 2026-09-27）

安装布局：`cmake --install .` → `install/bin/{include-what-you-use,fix_includes.py,iwyu_tool.py}` + `install/share/include-what-you-use/*.imp`（17 映射）+ `install/share/man/man1/`；iwyu 自签后 `--version` = "include-what-you-use 0.26 based on clang version 22.1.8"。
C2/C3 适配说明：iwyu 0.26 **无 `--json` 选项**（0.26 选项表实测：--error/--verbose/--mapping_file 等，无 JSON 报告输出）；iwyu 本体**无 `--fix_headers` 选项**（0.26 的文件改写由官方配套 `fix_includes.py` 完成，`iwyu 报告 | fix_includes.py` 管道用法；iwyu 报告输出在 **stderr**）。C2/C3 按 0.26 实际能力等价实现，断言强度不减。

| 用例 | 内容 | 断言 | 结果 |
|------|------|------|------|
| C1 基础头分析 | c1_bad.cc 用 std::vector/std::string/std::cout 但漏 <vector>；iwyu + 3×-isystem（v1/sysroot 双层） | rc=0；报告含 "should add these lines" 且含 `#include <vector>`；<iostream>/<string> 未被误删 | 通过 |
| C2 确定性输出与退出码（0.26 对 --json 用例的等价） | C2a：违规文件 + `-Xiwyu --error`；C2b：include 正确的文件 + `-Xiwyu --error` | C2a rc=1 且输出含 "should add"；C2b rc=0 且输出含 "has correct #includes/fwd-decls" | 通过（C2a rc=1✅ C2b rc=0✅） |
| C3 文件改写（0.26 对 --fix_headers 用例的等价，官方 fix_includes.py） | c3 文件经 consumer_b.h 间接见 Alpha（可编译），直接只用 Alpha → iwyu 报告 add consumer_a.h / remove consumer_b.h；`iwyu 2>&1 \| fix_includes.py` 改写 | "IWYU edited 1 files"；改写后含 consumer_a.h、不含 consumer_b.h；**改写后 clang++ -fsyntax-only rc=0** | 通过 |

三例均过编译门（用例文件经设备 clang++ 语法编译）+ 链接门（iwyu 动态依赖 libclang-cpp.so/libLLVM-22.so 经 clang 包 lib/ 解析）+ 运行门（签名 ELF 实际执行）。
踩坑记录：①C3 初版文件 Alpha 不可见（unknown type name）→ iwyu 遇硬编译错误 rc=1 不产报告，必须设计为"可编译但含多余 include"（上游 fix_includes_test 同款模式）；②iwyu 报告在 stderr，管道必须 `2>&1`。

## 交付物

{收尾时回填}

## 注意事项

### 全量测试环境配方（conanfile CI 复现依据）

1. **builtin 头桥接**：`ln -s <clang包>/lib/clang/22 $BUILD/lib/clang/22`（IWYU_RESOURCE_DIR=../lib/clang/22 相对 iwyu 二进制解析，clang 包 resource dir 含 builtin include/）
2. **测试 wrapper**（build 目录 bin/iwyu-wrapper.sh）：
   - 参数含 `-clang-cl`/`--driver-mode=cl*` → `exec <iwyu> "$@"`（cl driver 拒绝 -isystem/--sysroot；这 3 条测试不含系统头）
   - 否则 → `exec <iwyu> -isystem <SDK>/llvm/include/libcxx-ohos/include/c++/v1 -isystem <SDK>/sysroot/usr/include/aarch64-linux-ohos -isystem <SDK>/sysroot/usr/include "$@"`（前置=driver 侧，避开 dashdash 的 `--`）
   - SDK=`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native`
3. **CTestTestfile.cmake 路径替换**（build 目录生成物）：`bin/include-what-you-use"` → `bin/iwyu-wrapper.sh"`（224 条 run-test-* 条目）
4. **ctest 环境**：
   - `PATH=<clang包>/bin:$BUILD/bin:$PATH`（FileCheck/count 由 run_iwyu_tests.py 调用）
   - `LD_LIBRARY_PATH=<clang包>/lib`（iwyu 链 libclang-cpp.so→libLLVM-22.so→libc++_shared.so）
   - `IWYU_BINARY=<wrapper>`（fix_includes_test 必需；iwyu_tool_test 自管理）
5. **签名**：所有参与测试的 ELF（iwyu、iwyu-unittests）均须自签（OHOS XPM）；wrapper 为 sh 脚本无需签名
6. **禁止事项**：CPATH/CPLUS_INCLUDE_PATH 类环境变量注入（clang 归为 user include，破坏 IWYU 归属，实测 25 条失败）；`-isystem` 追加在参数尾部（dashdash 的 `--` 之后会被当输入文件）

### 其他

- 设备 /tmp 只读：构建/缓存一律 $TMPDIR=$HOME/tmp
- 设备 hnp grep 损坏：源码内容核验用 python3
- iwyu 二进制动态链接（libclang-cpp.so 等均在 clang 包 lib/），CONAN 消费时 RPATH 由 conan 管理
- 上游 bugs 套件（137 文件）默认不注册 ctest，未跑（XFAIL 套件，上游声明主要在 Linux 环境）
---

**编译结束**: 2026-09-27 14:32
**最终状态**: built
