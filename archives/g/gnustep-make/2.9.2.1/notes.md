# gnustep-make 2.9.2.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-28
- 编译器: clang 15 / clang++
- 目标平台: HarmonyOS PC aarch64 (OHOS)
- 状态: built（conan-verify 通过，CI upload 未完成）

## 背景

gnustep-make 2.9.2 已在 PR #5821 完成基础鸿蒙适配（config.guess/config.sub 识别 linux-ohos、configure hmdfs umask）。但该版本安装生成的 GNUstep Makefiles 在 HarmonyOS PC 上仍存在以下缺口，导致下游 gnustep-base 无法正常构建：

1. `target.make` 未把 linux-ohos 识别为 Linux → 无法生成 `.so` 共享库（仅静态 `.a`，静态 ObjC archive 在 libobjc2 上类注册崩溃）
2. `default_library_combo` 默认 `gnu` → 采用 legacy ABI，libobjc2 上消息发送 segfault
3. `DEFAULT_OBJC_RUNTIME_ABI=gcc` → 同上
4. `OPTFLAG=-O2` → clang/lld 对 `__objc_constant_string` 段的 -O2 链接 bug
5. 未配置 `NSConstantString` 常量字符串类 → 测试程序运行时 NSString 初始化失败

## 编译步骤

```
./configure --prefix=/storage/Users/currentUser/usr/local
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `.so` 无法生成 | target.make 未识别 linux-ohos | patch target.make：将 linux-ohos 加入 IS_LINUX（触发 HAVE_SHARED_LIBS 与 -shared 链接） |
| 2 | ObjC ABI 不兼容 | default_library_combo=gnu + DEFAULT_OBJC_RUNTIME_ABI=gcc | config-noarch.make.in 默认 ng-gnu-gnu；config.make.in DEFAULT_OBJC_RUNTIME_ABI=gnustep-2.0 |
| 3 | constant-string 链接失败 | -O2 下 lld 不生成 __objc_constant_string 段符号 | config.make.in OPTFLAG=-fPIC -O0 |
| 4 | NSString 初始化失败 | 无 NSConstantString 常量字符串类 | config.make.in OBJCFLAGS=-fconstant-string-class=NSConstantString |

## 源码修改（补丁）

- `0001-config-noarch.make.in.patch`：default_library_combo = ng-gnu-gnu（libobjc2 modern runtime）
- `0002-config.guess.patch`：识别 HarmonyOS aarch64（来自 2.9.2 基础适配）
- `0003-config.make.in.patch`：OPTFLAG=-O0、OBJCFLAGS=NSConstantString、DEFAULT_OBJC_RUNTIME_ABI=gnustep-2.0
- `0004-config.sub.patch`：接受 linux-ohos 三元组（来自 2.9.2 基础适配）
- `0005-configure.patch`：hmdfs umask 022、chown no-op（来自 2.9.2 基础适配）
- `0006-target.make.patch`：linux-ohos 识别为 GNU/Linux，支持 `.so` 构建

## 验证结果

```bash
# configure 生成的 config 关键值
default_library_combo = ng-gnu-gnu
OPTFLAG = -fPIC -O0
OBJCFLAGS = -fconstant-string-class=NSConstantString
DEFAULT_OBJC_RUNTIME_ABI = gnustep-2.0

# conan-verify 通过（G0-G4/L2/L5 通过；L4 安全扫描为 warn 非阻塞）
```

## 测试与上游测试用例说明

**上游测试用例（N=9）**：gnustep/tools-make 的 `TestFramework/` 目录含 9 个 example
测试（example1-9.m）。已在本 test_package 中依赖已发布的 gnustep-base/1.31.1 真实编译、
链接并运行全部 9 个 example，结果为 **9/9 全部运行通过（EXIT 0）**。
其中 example3/4 是上游**故意设计**的异常测试（向 NSString 发送 `objectForKey:`
"sending a bad message"，依赖测试框架捕获 NSException）——在完整 GNUstep 环境
（libc++_shared.so 已注入）下异常被 NS_DURING/NS_HANDLER **正常捕获**（其内部记录的
"Failed test" 为预期行为），程序正常退出，实测通过。
> 注：早期在缺 libc++_shared.so 的旧环境下曾实测 7/9、example3/4 异常逃逸
> （Uncaught NSInvalidArgumentException），属环境问题而非平台限制；注入 SDK C++
> 运行时后 9/9 全过。

**测试环境说明**：test_package 依赖已发布的 gnustep-base/1.31.1（运行期依赖仅
libobjc2/libffi/curl，gnustep-make 为其 tool_requires 无版本冲突）；运行 example 时
注入 OHOS SDK 的 libc++_shared.so 目录（经 clang realpath 推导，CI 通用）。

**适配后测试（真实运行上游测试）**：gnustep-base/1.31.1 发布到制品仓后，"循环依赖
无法运行"的前提不再成立。test_package 将上游 TestFramework 的 example1-9.m 原样复制，
CMake 编译为 9 个可执行文件，run_examples.sh 逐个真实运行，**全部要求 EXIT 0**，
实测 9/9 通过。经 `conan create` 的 L1 测试执行验证。

**鸿蒙特有测试**：另新增 `test_package/test_ohos_config.c`（纯 C，7 项断言），验证
gnustep-make 针对 HarmonyOS PC 的适配配置在安装产物中正确生效：
1. config.make: `-fconstant-string-class=NSConstantString`
2. config.make: `OPTFLAG = -fPIC -O0`（规避 constant-string 链接 bug）
3. config.make: `DEFAULT_OBJC_RUNTIME_ABI = gnustep-2.0`
4. config-noarch.make: `default_library_combo = ng-gnu-gnu`
5. target.make: `IS_LINUX = yes`（linux-ohos 识别）
6. target.make: `HAVE_SHARED_LIBS = yes`（.so 共享库构建）
7. GNUstep.sh 存在
实测 7/7 通过。这些配置即补丁 0001/0003/0006 的鸿蒙适配产出。

## 注意事项

- 本版本的 ng/-O0/NSConstantString 等配置为目标平台 HarmonyOS PC 的默认配置（ohpcd 制品仓面向鸿蒙）。
- 补丁 0002/0004/0005 沿用 2.9.2 基础适配内容，作为同一软件的新版本归档统一收录。

---

**编译结束**: 2026-08-28
**最终状态**: built