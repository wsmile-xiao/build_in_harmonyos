# angelscript 2.37.0 适配笔记

## 基本信息

| 项目 | 内容 |
|------|------|
| 软件名 | angelscript（AngelCode Scripting Library） |
| 版本 | 2.37.0（ANGELSCRIPT_VERSION=23700） |
| 上游 | https://www.angelcode.com/angelscript/ |
| 源码包 | https://www.angelcode.com/angelscript/sdk/files/angelscript_2.37.0.zip（zip 格式） |
| SHA-256 | 0c52d1688016a0b2484e9ca549471c4e295df060770c57840144c64815f54f10 |
| 许可证 | Zlib（条款内嵌源文件头 + docs/manual/doc_license.html） |
| 任务 | #14891（openmw #329 的阻塞依赖——游戏脚本线解锁件） |
| 构建系统 | 直编（custom：clang++ 逐单元编译 + llvm-ar 归档） |

## 软件简介

AngelScript 是面向游戏应用的跨平台脚本引擎（C++ 库）：静态强类型、
寄存器式虚拟机、类 C++ 语法，支持 JIT 式原生调用约定（应用直接注册
C++ 函数供脚本调用）。openmw（开源 Morrowind 引擎重实现）将其作为
游戏脚本运行时。核心库单库形态：sdk/angelscript/source/ 下 33 个通用
.cpp + 平台专属调用约定文件，头文件仅 include/angelscript.h。

## 构建方式：直编路径

不走上游 CMake（sdk/angelscript/projects/cmake）与 autotools，直编+归档
（abc/aklomp-base64 直编先例）：

```bash
# 1. 下载（官方 zip，conan get strip_root 去掉 sdk/ 顶层）
# 2. 直编 35 个编译单元
clang++ -c -std=c++17 -O2 -fPIC -DANGELSCRIPT_EXPORT -D_LIB \
  -I sdk/angelscript/source -I sdk/angelscript/include \
  sdk/angelscript/source/<each>.cpp -o obj/<each>.o
clang++ -c -x assembler-with-cpp -I sdk/angelscript/source \
  sdk/angelscript/source/as_callfunc_arm64_gcc.S -o obj/as_callfunc_arm64_gcc.o
# 3. 归档
llvm-ar rcs libangelscript.a obj/*.o && llvm-ranlib libangelscript.a
```

编译单元清单：上游 CMakeLists ANGELSCRIPT_SOURCE 的 33 个通用单元
（含守卫型 x86/x64_msvc/mingw/mips 平台文件——as_config.h 宏守卫使其在
非目标平台编译为空目标，上游同样全编）+ aarch64 专属
as_callfunc_arm64.cpp 与 as_callfunc_arm64_gcc.S。

## 本地预验证（2026-10-05，OHOS aarch64 真机）

```bash
# 35/35 编译单元全绿（clang-15 -std=c++17）
# libangelscript.a 归档成功（35 对象，2,630,370 字节）
# 宏路径实测（macro_check.cpp）：
__ANDROID__ NOT defined          # 走 __linux__ 分支（AS_LINUX）
AS_ARM64: native arm64 calling conventions ACTIVE
AS_MAX_PORTABILITY not defined   # 未降级为纯字节码模式
AS_POSIX_THREADS defined
atomics available                # AS_NO_ATOMIC 未触发
# 引擎往返测试 5/5 PASS（test_engine.cpp）：
PASS: asCreateScriptEngine(ANGELSCRIPT_VERSION=23700) OK
PASS: version 2.37.0 confirmed
PASS: script module compiled ('int main() { return 42; }')
PASS: script executed, returned 42 (native arm64 calling conventions exercised)
PASS: second asCreateScriptEngine/asReleaseScriptEngine roundtrip OK
ALL TESTS PASSED
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 运行测试程序报 Error loading shared library libc++_shared.so | SDK libc++.so 是链接器脚本（INPUT(-lc++_shared)），运行期加载器不认 | LD_LIBRARY_PATH=/system/lib64（系统真 so，__h 命名空间）——已知 OHOS 环境特性，非本包问题 |
| 2 | -lpthread 链接 | musl pthread 已并入 libc | 实测不加 -lpthread 链接同样成功（conanfile 不传） |
| 3 | gitlab.com/angelcode/angelscript 匿名 git ls-remote 认证失败 | HTTP 302 重定向可达但 git 协议需认证 | 第二源仅作备援记录（curl 302 实测可达），conandata 按 R39 只写官方单条 URL |

## 源码修改

无补丁（patches: {}）。OHOS 无需任何源码改动：as_config.h 原生识别
OHOS clang（__linux__ 且非 __ANDROID__），arm64 原生调用约定与 POSIX
线程自动激活。

## 依赖版本

无第三方库依赖（零外部依赖）。

## 测试说明

上游 SDK 无随包测试套件（N=0）：
- 官方 zip 无 test/、tests/ 目录
- projects/cmake/CMakeLists.txt 无 enable_testing()/add_test()
- add_on/ 与 samples/ 为示例代码（asrun 等 sample main），非断言型测试

test_package 消费者测试 5 断言（引擎创建/释放往返，见
test_package/MANIFEST.yml）：本地实测 5/5 PASS。
