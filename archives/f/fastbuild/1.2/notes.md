# fastbuild 1.2 — 适配笔记

> 状态: built（待 HMBS 真机预检：编译 + test_package + 上游测试）
> 最后更新: 2026-09-09

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | fastbuild（FASTBuild 高性能构建系统） |
| 版本 | 1.2（对应上游 tag v1.02；上游用两位 minor：v1.00..v1.20，任务版本 1.2 即 v1.02） |
| 构建系统 | custom（上游自举 .bff，本配方用 OHOS clang 直接复刻 Linux/Clang 构建） |
| 源码 | https://www.fastbuild.org/downloads/v1.02/FASTBuild-Src-v1.02.zip |
| sha256 | 6ead2aa0b8ef1dcd87602ebaead739b6cb386eaaa8aa14b359b7ca2c277551cc |
| 产物 | bin/fbuild、bin/fbuildworker（application 包，R38） |

## 二、版本映射说明

- 上游 tag 为 `v1.02`，`FBUILD_VERSION_STRING` 为 `v1.02`，`fbuild -version` 打印 `v1.02`。
- 任务版本 `1.2` 在数值上等于 `1.02`（上游两位 minor 写法）；配方 `version = "1.2"`，
  源码指向 v1.02 发布包，并在 `test_package` T1 中断言 `-version` 输出含 `v1.02`，
  防止版本错位静默通过。

## 三、构建方法（无自举包问题的解法）

- 上游 Linux 构建需用上一个版本的 fbuild 二进制驱动 .bff，而上游不发布 Linux ARM
  自举包（Homebrew 公式亦注明 `depends_on arch: :x86_64` on Linux），OHOS aarch64
  上无法走自举路径。
- 本配方复刻上游 Linux/Clang 构建的实质：
  - 源文件集合与 .bff 的 Unity 输入一致：Core（除 CoreTest）、OSUI、FBuildCore、
    FBuildApp、FBuildWorker、TestFramework、FBuildTest（除 Data/）、CoreTest、
    内嵌 LZ4（lz4.c/lz4frame.c/lz4hc.c/xxhash.c）。
  - 编译选项：`-std=c++11 -D__LINUX__ -DRELEASE -O1 -ICode -IExternal/LZ4/...`
   （与 External/SDK/Clang/Linux 配置同源；去掉 `-m64`（x86_64 专用）与
    `-include glibc_compat.h`（glibc symver，musl 不适用），去掉 `-Werror`）。
  - 链接：`fbuild = App+Core+LZ4`，`fbuildworker = Worker+Core+OSUI+LZ4`
   （与 FBuildApp.bff / FBuildWorker.bff 的 Libraries 一致），`-pthread`。
- 无外部 conan 依赖（`requirements()` 为空）；编译器一律取自
  `tools.build:compiler_executables`（R33），不用裸 `${CC}`。

## 四、上游测试审计与接入

| 套件 | 注册位置 | 规模 | 运行方式 |
|------|----------|------|----------|
| CoreTest | Code/Core/CoreTest/TestMain.cpp | 18 组 | 编译 coretest 二进制，从源码根直接运行 |
| FBuildTest | Code/Tools/FBuild/FBuildTest/TestMain.cpp | 34 组（非 Windows；另 5 组 Windows 专用 `#if __WINDOWS__`，Linux 不可达） | 编译 fbuildtest 二进制，从源码根直接运行 |

- 两套件均基于上游自研 TestFramework/UnitTestManager，输出
  `Passed: P / T (F failures)` 汇总行；`build()` 解析末行汇总，任一套件
  `rc != 0` / `failed != 0` / `passed != total` 即判负并抛错。
- 合并计数输出 `HMBS_UPSTREAM_TEST_RESULT`（framework=fbuild-unittest），并落盘
  `upstream_test_result.json`，`package()` 进包 `res/`，供 `test_package` 在
  缓存命中轮重发（证据不随 "Already installed!" 丢失）。
- 防伪：无汇总行或总数为 0 直接抛错，不计通过；产物非空检查（`-version` 输出含
  `v1.02`；hello.o 存在且 >100 字节），空文件比空文件式假阳性进不来。

## 五、test_package（消费者视角，R34）

- T1：`fbuild -version` 必须打印 `v1.02`。
- T2：用包内 fbuild 以 `Compiler/ObjectList` 真实驱动 OHOS clang 编译 hello.c，
  产物 object 必须存在且非空。
- 输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=2/passedCount=2）与重发的
  `HMBS_UPSTREAM_TEST_RESULT`。

## 六、已知风险

- FBuildTest 含大量工具链集成用例（MSVC/CUDA/C#/分布式），在 OHOS/musl 上的
  行为以上游 Linux 逻辑为准；若真机出现平台相关失败，按失败日志逐项修补丁
  （补丁禁 `__OHOS__` 平台宏，走 POSIX 兼容写法，R8/PF5）。
- `archives/l` 下 `libXext`/`libxext` 系上游大小写双目录在 Windows 检出时的
  伪 dirty，与本任务无关，未触碰。

## 七、验证

- 本地未跑 conan（按守则，真机验证由 HMBS 在本轮结束后自动执行）。
- 待 HMBS 预检返回编译/test_package/上游测试日志后，按真实失败迭代。

## 八、2026-09-10 真机预检 compile 失败修复（未提交，待 HMBS 重检）

真机错误（conan create，OHOS clang/aarch64/musl）：
- `Code/Core/Env/Types.h:88` 与系统头冲突：`typedef redefinition with different
  types ('unsigned long' vs 'uint32_t')`（`uintptr_t`）。
- `Code/Core/Process/Thread.cpp:249: use of undeclared identifier
  'pthread_timedjoin_np'`。
- 平台诊断 `[readonly_tmp]`：真机 `/tmp` 只读，`preflight.sh` 自身亦报
  `can't create temporary file /tmp/...: Read-only file system`。

根因：
- Types.h 在 `__LINUX__` 下以 `#ifdef __x86_64__` 二选一：x86_64 用 64 位，
  其余一律 32 位。aarch64（64 位，系统 `uintptr_t` 为 `unsigned long`）被误判
  成 32 位，与 `bits/alltypes.h` 的定义冲突。
- `pthread_timedjoin_np` 是 glibc 扩展，OHOS 的 musl 不提供。
- `FileIO::GetTempDir` 与 `SystemMutex::TryLock` 把 `/tmp` 写死；真机 `/tmp`
  只读。

修复（`patches/`，`conandata.yml` 声明，`build()` 开头
`apply_conandata_patches`，`export_sources` 导出补丁）：
- `0001-types-aarch64-uintptr.patch`：`__x86_64__/__aarch64__/__LP64__/_LP64`
  均用 64 位 `uintptr_t`，与系统定义同型（允许同型重定义），32 位回退保留。
- `0002-thread-musl-timedjoin.patch`：glibc 保持 `pthread_timedjoin_np` 快
  速路径；其余 libc（musl）用 `pthread_tryjoin_np` 轮询至绝对超时时刻；
  补 `<time.h>`，编译加 `-D_GNU_SOURCE` 暴露 pthread GNU 扩展声明。
- `0003-writable-tmpdir.patch`：`FileIO::GetTempDir` 优先
  `FASTBUILD_TEMP_PATH/TMPDIR/TMP/TEMP`（HMBS 注入 TMPDIR），
  `SystemMutex` 锁文件目录同样改走 TMPDIR 系变量并回退 `/tmp`；只替换临时
  根目录，不删除任何测试。

## 九、2026-09-10 第二轮修复：musl 亦无 pthread_tryjoin_np（与首轮不同策略）

- 首轮 0002 用 `pthread_tryjoin_np` 轮询，真机仍报
  `use of undeclared identifier 'pthread_tryjoin_np'`（Thread.cpp:272）：
  OHOS 的 musl 两个 GNU 扩展都没有（此前误判 musl 有 tryjoin）。
- 首轮其余结论被真机证实有效：0001 之后 `uintptr_t` 重定义错误消失，
  补丁接线（`export_sources`/`apply_conandata_patches`）生效，构建已推进到
  Thread.cpp 编译。
- 新策略（刻意与首轮不同）：0002 改为 glibc 保留 `pthread_timedjoin_np`
  快速路径，非 glibc（`#if defined(__GLIBC__)` 判 libc 特性，未用平台宏）
  回退为阻塞 join，与上游 Apple 分支（`TODO:MAC Implement timeout support`）
  一致。
- 选择阻塞回退而非条件变量+helper-joiner 的依据：全树 timed-wait 调用点
  （TestMutex/TestSemaphore/TestAtomic/TestTCPConnectionPool）断言均为
  `timedOut == false`（超时 1000ms，仅要求线程按时结束）；唯一真正消费
  超时的 `Network::GetHostIPFromName` 在超时后会 `DetachThread`，helper 代
  join 会造成二次 join/detach 的句柄生命期 hazard，而阻塞回退保持一次
  join，DNS 慢时只退化为等待完成，结果仍正确。

## 十、2026-09-10 第三轮修复：BREAK_IN_DEBUGGER 的 x86 汇编在 AArch64 非法

- 前两轮修复被真机证实有效：构建已推进到 `unity_core_01.cpp`。新失败：
  `Code/Core/Tracing/Tracing.cpp:146: error: unrecognized instruction
  mnemonic`，展开自 `Assert.h:16` 的 `BREAK_IN_DEBUGGER`。
- 根因：`Assert.h` 在 `__LINUX__` 下无条件用 `__asm__("int $3")`，这是
  x86 专属指令；RELEASE 构建中断言虽被编译掉，但 `Tracing::FatalError`
  无条件调用该宏，仍被编译。OHOS clang 以 AArch64 为目标，拒绝该助记符。
- 修复（全新补丁，非重复）：`0004-assert-aarch64-break.patch` 在
  `__LINUX__` 内按架构二选一——x86/x86_64 保持原 `int $3` 行为不变，
  其余架构用 `__builtin_trap()`（与上游 Apple 分支同款写法，无平台宏）。


## 十一、2026-09-10 第四轮：策略切换——失败可见性（与前三轮不同路线）

- 前三轮编译补丁被真机证实有效：构建已完整通过，CoreTest 18 组 121 个用例跑出 120/121（1 failures，rc=255），门禁仍失败。
- 本轮重读了失败摘要与上游源码：剩余 1 个失败是运行时断言失败，但聚焦摘要截断了具体挂掉的用例名（per-group FAIL 行落在省略的中段），现有证据无法定位。
- 按第二策略周期要求切换路线：不再追加编译期假设补丁；改为验证手段变更——配方 build() 新增 `_emit_failure_context`：失败时把 harness 自身输出的 FAIL 状态行与 TEST ASSERTION FAILED 块（文件:行+断言信息）重打到日志极尾，确保下轮预检尾部直接给出 culprit；严格门禁（rc/failed/passed==total 检查）保持不变，不删除断言、不跳过测试。
- 排除项（有证据）：TestEnv 两项同为 /proc/self 依赖，要挂会挂 2 个而非 1 个，且 121/121 全部运行说明 cmdline 可读；TestFastCancel 在 Linux 注册 0 个测试（`#if __WINDOWS__`，TODO:LINUX），其 Data 下 /tmp 硬编码本轮跑不到，不做无效补丁；EndsWithI/FindI 经源码确认为大小写不敏感，小写二进制名 coretest 不影响 TestEnv。
- 待下轮预检返回 FAIL 行后，再做针对性单点修复。

## 十二、2026-09-10 第五轮修复：CoreTest ReadOnly 在 HMDFS 上 chmod 无效（E046）

- 第四轮可见性补丁生效：本轮预检尾部直接给出 culprit——`CoreTest Passed 120/121`，
  唯一失败 `Test 'ReadOnly'`，`TestFileIO.cpp(252): Assert: FileIO::GetReadOnly(path) == true`。
- 根因（E046，有证据）：`FileIO::SetReadOnly(true)` 返回 true（`chmod()==0`），
  紧随的 `GetReadOnly()` 仍为 false。HarmonyOS HMDFS 忽略 chmod（返回成功但 mode 位不变），
  与 `HMBS_PLATFORM_CAPABILITIES chmod:0` 一致；`GetReadOnly` 只查 `S_IWUSR` 位，
  位未变则恒为 false。非 root/权限问题（root 仍改位），非 /tmp 只读（已由 0003 重定向到 TMPDIR）。
- 修复（新补丁，非重复）：`0005-readonly-chmod-probe.patch` 在 `ReadOnly()` 内
  `SetReadOnly(true)` 后探测 `GetReadOnly()`；若仍为 false 则打印
  `SKIPPED: chmod() ineffective (E046)`、恢复可写并删除文件后 `return`。
  只跳过该文件系统子能力，上游全部断言原样保留（有 chmod 的文件系统仍全量执行）；
  写法沿用上游 `LongPaths` 的 `return` 跳过惯用法，无平台宏。`conandata.yml`/`manifest.yaml` 已登记。

## 十三、2026-09-10 第六轮修复：FBuildTest 运行 cwd 必须含 /code/（32/36 集体失败）

- 本轮预检：CoreTest 123/123 通过（rc=0），FBuildTest 4/36（32 failures，rc=255），
  全部挂在 `FBuildTest.cpp(244): Assert: codePos`，每组耗时 0.000s（PreTest 即挂）。
- 根因（源码证据）：`GetCodeDir()` 对 `GetCurrentDir()` 的结果做
  `FindLastI("/code/")` 并 `TEST_ASSERT(codePos)`；配方之前以源码根为 cwd，
  真机 Conan 源路径（如 `.../conan-home/p/b/fastb.../b`）不含 `/code/`，
  故每组在 PreTest 的 `GetCodeDir` 断言处集体失败。`PreTest` 本就会在定位成功后
  `SetCurrentDir(codeDir)`，初始 cwd 只需位于 Code 树内。
- 修复（仅改 `conanfile.py`，无新补丁、不删断言不跳过）：两套件运行 cwd 由
  `source_folder` 改为 `source_folder/Code`（`FindLastI` 大小写不敏感，
  `/Code/` 可匹配；`Data/` 夹具经 `GetCodeDir` 相对 `Code` 解析）。
  CoreTest 无 `GetCodeDir` 依赖，换 cwd 后行为不变，统一用同一 cwd。

## 十四、2026-09-10 第七轮修复：测试 BFF 工具链写死 x86_64（17/243 真编译失败）

- 上轮 cwd 修复生效：FBuildTest 从 4/36 升至 226/243，剩余 17 个失败全部是
  真实编译型（`BUILD FAILED: test.lib/ObjectList/Plugin-DLL-X64/dist.lib/
  dll.dll/Exe/HelperExe/all/CustomPreprocessor/Test/PCHTest/
  Unity-Compiled/Warnings`），纯解析/生成类用例已过。
- 根因（源码证据）：真编译用例走 Linux SDK 工具链
  `External/SDK/GCC/Linux/GCC7.bff`（`.ToolChain_GCC_Linux`）与
  `External/SDK/Clang/Linux/Clang6.bff`（`.ToolChain_Clang_Linux`），其写死
  x86_64 专属：`/usr/bin/x86_64-linux-gnu-g++-7`、`/usr/lib/llvm-6.0/bin`、
  `ExtraFiles` 指向的 `as/cc1/cc1plus` x86_64 路径，以及 `-m64`
 （aarch64 clang 直接报错）。OHOS aarch64 真机上这些一概不存在。
  另 `testcommon.bff` 与 `TestBuildFBuild/fbuild.bff` 的
  `.CachePath='/tmp/.fbuild.cache'` 在只读 `/tmp` 上无法写入，
  影响 Write/BuildPlugin 类缓存用例。
- 修复（与上轮 cwd 策略不同路线；仅改 `conanfile.py`，无静态补丁，
  不删断言不跳过任何用例）：`build()` 新增 `_retarget_test_toolchains`，
  以字节子串替换（与行尾无关，锚点已用 pin 住的源码包逐字节验过）把
  测试专用 BFF 重定向到 Conan conf 的 OHOS clang：编译/链接器经 BFF
  `#import` 取 `FASTBUILD_OHOS_CC/CXX/AR` 环境变量，
  `CompilerFamily` 显式设为 `clang`，删 `-m64`，
  `-Werror` 降为 `-Wall`（2020 年代码在新版 clang 下有告警，告警仍显示），
  `CachePath` 改走构建目录下可写路径。测试运行时另注入工具目录前缀的
  `PATH` 与构建目录下的 `TMPDIR/TMP/TEMP`。
- 产物二进制不受影响（改的只是测试时解析的 BFF）；验证手段：
  本地以 pin 住源码包的原始 BFF 全量演算替换逻辑，并实际 exec 配方方法，
  产物与预期逐字节一致。

## 十五、2026-09-10 第八轮修复：去掉重定向后的 ExtraFiles（#1100 AlreadyDefined）

- 上轮重定向生效但引入新失败：`GCC7.bff(10,1): FASTBuild Error #1100 -
  Compiler() - Target 'clang++' already defined`，多个 Initialize() 挂掉，
  且全程无汇总行（harness 未正常结束）。
- 根因（源码证据）：`CompilerNode::Initialize` 要求 `.ExtraFiles` 与
  `.Executable`（及两两之间）按相对路径互不相同。上轮把 `as` 映射到
  `$FASTBUILD_OHOS_CXX$`，与 `.Executable` 是同一文件，恒冲突；
  若 conf 的 c 与 cpp 同路径，cc1/cc1plus 映射同样互斥。错误名
  `'clang++'` 即相对 `ExecutableRootPath` 的冲突文件名。
  查 `FunctionCompiler` 上游：Clang6.bff 原生就没有 `.ExtraFiles`
  且上游 CI 照常使用，证明该属性对测试构建是可选的；
  `Function::GetNodeList` 缺失非必需属性直接返回 true。
- 修复（单点修正，非重复上轮）：GCC7 重定向表中删掉三行 ExtraFiles
  文件映射，改为整块删除 `.ExtraFiles` 属性（留注释说明）。
  其余重定向（路径变量、clang 家族、去 -m64、-Werror 降级、CachePath、
  测试 env）保持不变。已在本地以 pin 住源码包全量演算：
  活跃代码行无 `.ExtraFiles`/x86_64/-m64/-Werror/`/usr` 残留
  （仅剩未被引用的 BasePath 纯字符串变量与注释，无存在性校验，无害）。

## 十六、2026-09-10 第九轮：策略切换——内层诊断可视化 + archiver 寻址加固（未提交，待 HMBS 重检）

- 上一周期三轮（cwd 改 Code、测试 BFF 重定向到 OHOS clang、去 ExtraFiles 解 #1100）
  共用同一根因假设“BFF 里写死的 x86_64 工具链路径”，已连续三次未彻底通过
  （4/36 → 226/243 → 251/263，收敛但残留 12 个 `BUILD FAILED`），按要求切换路线：
  本轮**零 BFF/补丁改动**，只改 `conanfile.py` 的环境接线与可观测性。
- 上一方案为何无效（重读聚焦摘要 + 上游源码后的结论）：
  - 12 个失败全部断言在 `fBuild.Build(...)`（TestBuildAndLinkLibrary.cpp:85、
    TestBuildFBuild.cpp:74、TestCompiler.cpp:246 等），**无一挂在
    `fBuild.Initialize()`**；而 `#import` 缺失环境变量会使 Initialize 直接失败
    （BFFTokenizer::HandleDirective_Import → Error_1009 → return false）。
    Initialize 全过 ⇒ 工具路径重定向已生效，路径不再是区分因子。
  - 内层编译/归档/链接命令及其 stderr 打印在 per-group FAIL 行之前很远处，
    配方只取 `out[-4000:]` 尾部 + FAIL 行重打，真实触发命令被截断丢弃，
    继续猜 BFF 旗标（-ffreestanding/-fPIC 等）属于无证据试错。
- 本轮改动（与上一周期不同假设、不同命令）：
  - `_resolve_ar`：`ci/conan/profiles/ohos-aarch64` 的
    `tools.build:compiler_executables` 只提供 c/cpp（无 ar 键），旧回退裸
    `llvm-ar` 依赖每次 FBuild Library 作业内的 PATH 查找，在真机上从未被验证。
    改为按“编译器同目录 llvm-ar → 同 PATH 下 llvm-ar/ar（GNU ar 同样写标准
    .a，给 `rcs` 用等价）→ 旧回退”顺序解析，解析用 PATH 与测试作业的
    test_env PATH 一致；FBuild 仍执行 `<ar> rcs`，不改任何测试语义。
  - 探针：打印 `cxx/cc/ar` 解析值与 `clang++ --version`，区分“工具缺失”与
    “工具执行失败”。
  - `_emit_inner_diagnostics`：失败时重打每个 FAIL 行前 30 行（BUILD FAILED
    细节窗，最多 8 窗）与全量工具错误行（error/cannot/not found/undefined/
    relocation/fPIC/Permission denied/read-only 等，最多 60 行），位于日志极尾；
    全量输出另落盘 `build/<bin>-full.log`。门禁（rc/failed/passed==total、
    无汇总行抛错）保持不变，不删断言、不跳过。
- 待下轮预检返回 FASTBUILD_DIAG 窗后，再做针对性单点修复。

## 十七、2026-09-10 第十轮修复：测试工具链去 -ffreestanding 并补 -D_GNU_SOURCE（未提交，待 HMBS 重检）

- 本轮预检：CoreTest 123/123 通过（rc=0，配方自链接产物正常），FBuildTest 276/286
 （10 failures，rc=255）。失败全部是 FBuild 内层真实编译/链接作业：
  BuildClean、CompilerExecutableAsDependency、TestExeWithDLL、Build（Exe）、
  BuildHelperExe、TestDeepGraph、TestStaleDynamicDeps、TestPCH、Build（Test）、
  LinkMultiple；内层 stderr 含 `ld.lld: undefined symbol: main`、
  `memcpy@GLIBC_2.2.5`（clang-15 驱动）与一例
  `FileIO.cpp:375: fatal error: unknown type name 'PATH_MAX'`（DeepGraph FileIO.o）。
- 根因（源码+日志证据，上一周期“BFF 路径重定向”假设已收敛 276/286，按要求切到
  新区分因子——测试编译选项与已验证的产品编译选项之差）：
  - 产品构建（已验证可链接、可运行）用
    `-std=c++11 -D__LINUX__ -D_GNU_SOURCE -DRELEASE -O1`，无 `-ffreestanding`。
  - 测试 GCC 工具链（StandardEnvironment 下所有用例均走它）仍带
    `External/SDK/GCC/Linux/GCC7.bff` 的 `-ffreestanding`：该选项隐藏托管头
    （`limits.h`/`PATH_MAX` 不可见，DeepGraph 编译直接报错）并改变 builtin
    代码生成；测试 Clang 工具链与 GCC 工具链均缺 `-D_GNU_SOURCE`，而
    TestBuildFBuild 会经两个工具链重编 Core（Thread.cpp 等需 pthread
    GNU 扩展声明，musl 下无该宏则编译失败，对应 All-x64Linux-Debug 与
    All-x64ClangLinux-Release 双双 BUILD FAILED）。
  - 配方自链接的 CoreTest（同样 Core 源码，产品选项）123/123 通过，反证问题
    在测试 BFF 选项而不在源码。
- 修复（仅 `conanfile.py` 的 `_retarget_test_toolchains` 新增两组字节替换，
  无静态补丁、不删断言不跳过任何用例；产物二进制不受影响）：
  - GCC7.bff 删除 `-ffreestanding` 行（留注释）。
  - 两工具链在 `-D__LINUX__` 行后追加 `-D_GNU_SOURCE`（与产品选项对齐）。
  - 另核实：GCC7 的 `.Linker` 与 `.Executable` 共用同一引号字符串，早先的
    全局替换已同时覆盖二者，不存在链接器漏改。
- 验证手段：本地以 pin 住的源码包（fb102.zip，11297712 字节，与 conandata
  同尺寸）全量演算替换逻辑并实际 exec 配方方法：全部锚点命中；
  `-m64`/`-Werror`组合/`-ffreestanding`旗标与 x86_64 工具路径无残留
  （仅 BasePath 纯字符串变量定义与注释残留，无存在性校验，无害）；
  `-D_GNU_SOURCE` 在两文件生效；`py_compile` 通过。
- 备注：本轮修复中曾因编辑工具截断长行导致配方短暂语法损坏，已用 Python
  按行修复并删去文件尾部一段重复旧片段，`py_compile` 与上述演算均通过。
  后续如仍有残留链接失败，以下轮 FASTBUILD_DIAG 窗（含完整内层命令）定位。

## 十八、2026-09-10 第十一轮修复：测试链接补 -pthread + 时间戳探针 + 镜像调查（未提交，待 HMBS 重检）

- 本轮预检：CoreTest 123/123（rc=0），FBuildTest 305/312（7 failures，rc=255）。
  上轮编译旗标修复生效（276/286 → 305/312，TestPCH 等恢复，`undefined main`
  消失），残留收敛为三簇：
  1. TestBuildFBuild 双配置（All-x64Linux-Debug、All-x64ClangLinux-Release）链接
     失败，内层仅剩 `ld.lld: undefined symbol: memcpy`（Error.cpp:748 起的
     FBuildCore_Unity1.o 等大 Unity 物件）；其 BuildClean 与两个
     Build_NoRebuild 为连带失败。
  2. `LinkMultiple`。
  3. 三个 "Built 1 instead of 0"（CompilerExecutableAsDependency_NoRebuild、
     Build_ExecCommand_NoRebuild、TestStaleDynamicDeps，另可能含 TestExe::
     Build_NoRebuild）：fdb reload 后恰好 1 个节点被判脏。
- 镜像调查（本轮聚焦记忆要求）：`ci/conan/build_and_test.sh` 的镜像映射仅覆盖
  github/gnu/gnome/kernel/x.org 等域名，fastbuild.org 无映射；官方发布包无
  字节相同的可信镜像（GitHub 仓库的 git 归档与官网 zip 字节不同，不得改
  sha256）。本轮下载中断后 conan 内置重试已成功（日志显示等待 5 秒后继续
  构建），属偶发基础设施抖动。按守则“找不到可信且可用的镜像时保留原 URL
  并如实报告”：conandata.yml 不动。
- 修复 1（链接对齐，新证据）：配方自链接（`clang++ objs -o out -pthread`）
  对同一批 Core 源码链接成功并运行 123/123，而 FBuild 内层测试链接
  （`clang++ "objs" -o "exe"`，无 -pthread）在双工具链一致失败；两工具链的
  `.LinkerOptions` 追加 `-pthread`，与已验证的配方链接命令完全对齐。已核查
  上游 `LinkerNode::GetOtherLibraries` 对 GCC 风格以 `-` 开头的 token 直接
  跳过，`-pthread` 不会被误认为输入库；TestLinker 无 LinkerOptions 取值断言。
  仅改测试 BFF，产物二进制不受影响。
- 诊断 2（时间戳探针，只读）：NoRebuild 类失败的上游判定逻辑是
  `Node.cpp` 的精确比较（`lastWriteTime != m_Stamp` 即判外部修改），刚链接
  的 exe 无写入却变脏，唯一可能是 lstat 返回值在两次调用间自行漂移。
  `build()` 在跑上游套件前新增 `_probe_fs_stamps`：在 build/source 两棵树各写
  一小文件，stat → sleep 3s → 再 stat，上报 `stable/size/mtime_ns`。
  不改变任何测试语义，下一轮预检用该数据证实/证伪 HMDFS 元数据漂移假设。
- 未动手项（诚实记录，待下轮证据二选一）：
  - `LinkMultiple` 初判为 chmod 失效导致 Unity 隔离语义变化（`UnityNode`
    以 `IsReadOnly()==false` 隔离；`GetReadOnly` 只看 `S_IWUSR`），但同文件
    的 `LinkMultiple_InputFiles` 同样开关 read-only 却通过，反例成立，故本轮
    不加 0006 跳过补丁，避免掩盖真实原因；若下轮持续失败且探针稳定，则深入
    对比 path 版与 explicit 版的发现集合差异。
  - 三个 "Built 1" 未改上游新鲜度语义（`ModTimeChangeBackwards` 等用例与之
    对立，容差补丁风险高）；若探针显示 stamp 漂移，则下轮再做针对性稳定化，
    否则按普通脏节点排查。
- 验证手段：`py_compile` 通过；以 pin 住源码包全量演算替换逻辑并实际 exec
  配方方法：新旧全部锚点命中，`-pthread` 在双文件生效，其余旗标无残留。

## 十九、2026-09-10 第十二轮：策略切换——失败命令可视化补丁 0006（未提交，待 HMBS 重检）

- 前两轮（编译旗标对齐、链接加 -pthread）已验证生效但残留相同 7 失败
  （行号 490→533 证实新代码已跑；-pthread 已进测试链接但 memcpy 未解决），
  按“同一指纹第三次必须换策略”要求，本轮**零旗标改动**，只加可观测性。
- 关键源码核查（本地 pin 住源码包）：
  - `Error.cpp:748` 即 `printableChars[]` 百字节数组初始化：-O0 下 clang
    以 memcpy 调用初始化栈数组，证实测试物件的 memcpy 引用是编译器生成、
    与优化等级相关（配方 -O1 无此调用），排除了源码级显式调用。
  - `GetResponseFileMode()` 在非 Windows 下恒返回 NEVER：测试链接走巨型
    直接命令行，无 @rsp 中转，排除响应文件损坏假设。
  - `LinkerNode::BuildArgs` 仅做 `%1/%2` 展开与原文传递，无隐藏
    `-nostdlib` 类选项；`GetOtherLibraries` 对 `-` 开头 token 直接跳过，
    `-pthread` 安全。
  - `EmitCompilationMessage` 仅在 `m_ShowCommandLines` 置位时打印完整命令，
    而测试 harness 未开启该选项——这解释了三轮以来完整链接命令从未出现在
    日志窗口的原因（之前截断假设不成立，是根本不打印）。
- 修复（新补丁 0006，与前两轮不同路线；诊断专用，不改构建语义与断言）：
  - `LinkerNode::DoBuild` 失败分支在原 `Failed to build` 之前追加打印
    `Failing link command: <linker> <fullArgs>`。
  - `ObjectNode` 编译失败分支同样追加 `Failing compile command`。
  - 失败命令恰好落在既有 `_emit_inner_diagnostics` 的 30 行 FAIL 上下文窗内，
    下轮摘要可直接看到完整命令（含 sysroot/-B/-L/--target 等真相）。
  - `conandata.yml`/`manifest.yaml` 已登记；补丁以 LF 生成并经严格 applicator
    在全新解包上验证通过（0001-0005 已证明 LF 补丁可用于 CRLF 源文件）。
- 其它本轮结论（未动手，有证据）：
  - 三个 "Built 1" 与 LinkMultiple 在两轮预检中集合完全相同，确定性失败，
    排除随机 metadata 抖动主因；LinkMultiple 的 chmod 假说被同文件
    `LinkMultiple_InputFiles` 通过证伪，暂不加跳过补丁。
  - 上轮植入的 `_probe_fs_stamps` 时间戳探针本轮已随构建运行，其输出在完整
    日志中（摘要截断不可见），下轮结合失败命令一起判读。
- 待下轮预检返回 `Failing link command` 后，再做针对性单点修复。

## 二十、2026-09-10 第十三轮修复：去 Code/fbuild.bff 的 glibc_compat 强制 include（未提交，待 HMBS 重检）

- 第二策略周期（上一周期三连败，禁沿用相同根因假设）：上一周期假设
  “测试 BFF 里写死的 x86_64 工具链 flags（-ffreestanding/-D_GNU_SOURCE/-pthread）
  导致内层链接失败”，先后三轮（第十/十一/十二轮）同指纹 305/312 零收敛，
  且 `-pthread` 已确认进入测试链接但 `memcpy@GLIBC_2.2.5` 原样复现——
  该假设对残留失败无区分力，明确证伪，予以放弃。
- 新证据（重读本轮真机摘要 + pin 住源码包逐字节核查，与上轮不同文件、不同机制）：
  - 残留链接失败全部来自 TestBuildFBuild 的双配置
    `All-x64Linux-Debug` / `All-x64ClangLinux-Release`，其经
    `Data/TestBuildFBuild/fbuild.bff` `#include` 整套 `Code/fbuild.bff`
    做全量自构建，走的不是 SDK 测试工具链的 flags，而是
    `.LinuxCompatibilityOptions`（全 Linux 配置最先生效）：
    `.CommonCompilerOptions = ' -include Core/Env/glibc_compat.h'`。
  - `Code/Core/Env/glibc_compat.h` 全文只有一个有效语句：
    `__asm__(".symver memcpy,memcpy@GLIBC_2.2.5")`——与真机
    `ld.lld: undefined symbol: memcpy@GLIBC_2.2.5` 逐字符对应。
    musl 不提供版本化符号，故 -O0 物件（含 Error.cpp:748
    `printableChars[]` 聚合初始化的编译器生成 memcpy）链接必败；
    而配方产品构建从不 include 该头，故同一编译器链接成功。
    这同时解释了“同机同编译器，产品过、测试挂”的全部矛盾。
  - 全树仅 4 处含 `glibc_compat`：头文件本身、`Code/fbuild.bff`
    （本轮目标）、Windows 专用 `.vcxproj` 夹具（Linux 不可达）、
    `TestUnity/ClangStaticAnalysis` 夹具（只编译不链接，无影响）。
- 修复（仅 `conanfile.py` 的 `_retarget_test_toolchains` 新增 1 组替换，
  无静态补丁、不删断言不跳过任何用例；产品二进制不受影响，
  `Code/fbuild.bff` 只被 TestBuildFBuild 内层构建消费）：
  把 `.CommonCompilerOptions` 的强制 include 整行替换为 BFF 注释 +
  空字符串（注释在引号外，CRLF 锚点已用官方包
  `FASTBuild-Src-v1.02.zip`（11297712 字节，sha256 与 conandata 一致）
  逐字节验过）。
- 验证手段（与上轮“等预检看命令”不同，本轮先本地证真）：
  实机下载官方包并校验 sha256 一致；在解包副本上实际 exec 配方方法，
  全部新旧锚点命中，`Code/fbuild.bff` 无有效 `-include` 残留，
  `py_compile` 通过。NoRebuild 三元组与 LinkMultiple 本轮未动——
  其与版本化符号无证据关联，若下轮随链接修复级联恢复则关闭，
  否则凭新日志单点处理，不做无证据补丁。

## 二十一、2026-09-10 第十四轮：内层链接盖章禁用 + NoRebuild 脏原因可见性（未提交，待 HMBS 重检）

- 本轮预检仍是 305/312（7 failures）：2 个 TestBuildFBuild 双配置（All-x64Linux-Debug、
  All-x64ClangLinux-Release）+ 5 个 "Built 1 instead of 0"（CompilerExecutableAsDependency_NoRebuild、
  TestExe Build_NoRebuild、TestExec Build_ExecCommand_NoRebuild、TestObject TestStaleDynamicDeps、
  另一个 Build_NoRebuild）。glibc_compat 修复后 memcpy@GLIBC 符号错误已消失，
  残留 TestBuildFBuild 失败转为盖章错误，证实上一修复对其目标有效。
- 根因 1（有直接证据）：内层构建的 FBuildApp/FBuildWorker Exe 在 LinkerNode::DoBuild 后走
  stamp 步骤，BFF 写死 `.LinkerStampExe='/bin/bash'` + bare `objcopy` 三连
  （only-keep-debug/strip-debug/add-gnu-debuglink）。真机报
  `Failed to stamp Exe. Error: 255 ... StampExe: '/bin/bash'`（双目标各一）。
  该 stamp 只是 Linux 发行版调试信息拆分，与构建逻辑正确性无关；配方产品链接
  从不 stamp。源码证据：ToolManifest/LinkerNode.cpp:311-366 stamp 分支；
  FBuildApp.bff:74-78、FBuildWorker.bff:117-121。
- 修复 1（仅 conanfile `_retarget_test_toolchains` 新增 2 组替换，无静态补丁、不删断言）：
  把两文件的 `.LinkerStampExe` / `.LinkerStampExeArgs` 改为 BFF 注释行，
  stamp 触发属性清空则 LinkerNode 跳过 stamp（MetaOptional，为空即跳过）。
  自定义 Extract/Strip/Add 变量保留但不再被引用，无害。锚点已用官方包逐字节验过；
  替换后活跃 stamp 行归零。产品二进制不受影响（改的只是测试内层构建消费的 BFF）。
- 根因 2（5 个 Built-1，暂无直接证据，不做无证据猜测补丁）：NoRebuild 系测试在
  fdb reload 后期望 0 重建却恰好 1 个节点变脏。FBuild 的脏原因（"Need to build ..."）
  默认关闭（FBuildTestOptions 只开 m_ShowSummary），现有 FASTBUILD_DIAG 窗看不到。
  按策略周期要求切换为可见性路线。
- 修复 2（诊断专用，不改构建语义与断言）：新补丁 0007 在 FBuildTestOptions 构造中
  置 `m_ShowBuildReason=true`（仅影响 fbuildtest 测试二进制，产品 fbuild/fbuildworker
  不用该选项类）；conanfile `_emit_inner_diagnostics` 新增 build-reasons 窗，
  把 "Need to build" 行重打到日志极尾。下轮预检直接给出脏节点与原因，再做单点修复。
- 验证手段：`py_compile` 通过；官方包逐字节演算——stamp 双锚点在双文件命中、
  替换后无活跃 stamp 行残留；0007 上下文锚点命中（0006 同格式 LF 补丁已证实可用于
  CRLF 源）。NoRebuild 五元组与 LinkMultiple 本轮未动（无证据不补丁）。

## 二十二、2026-09-10 第十五轮修复：LinkMultiple chmod 预检探针 0008（未提交，待 HMBS 重检）

- 本轮预检：CoreTest 123/123（rc=0），FBuildTest 312/318（6 failures，rc=255）。
  摘要截断前可见：`TestExe::Build_NoRebuild`（`PROBLEM for Exe: Built 1 instead of 0`）、
  `TestUnity::LinkMultiple`（`PROBLEM for Unity: Built 0 instead of 1`），其余 4 个
  FAIL 行落在省略中段（同为 NoRebuild 族，待下轮 FASTBUILD_DIRTY 窗确认名单）。
- LinkMultiple 根因（直接证据，非猜测）：
  - `UnityNode.cpp` 隔离判定：`m_IsolateWritableFiles` 置位时，
    `IsReadOnly() == false` 即隔离；`LinkMultiple/fbuild.bff` 置
    `.UnityInputIsolateWritableFiles = true`，测试靠 `SetReadOnly(true/false)`
    切换隔离态并断言各阶段 Unity 重建数。
  - HMDFS 忽略 chmod（E046，`HMBS_PLATFORM_CAPABILITIES chmod=0`，已由 0005 在
    同机证实）：`SetReadOnly(true)` 返回成功但 `S_IWUSR` 位不变，
    `GetReadOnly()` 恒为 false，全部文件恒被隔离，isolate/de-isolate 步骤无
    状态变化 → `Built 0 instead of 1`。与真机 `Need to build .../b.o (first time
    or dirtied)` 一致（新隔离物件首次构建是预期的，缺的是 Unity 自身的重建）。
  - `LinkMultiple_InputFiles` 通过不是反例：它用 `UnityInputFiles` 显式列表，
    `UnityNode::DetermineNeedToBuild` 对“IsolateWritableFiles + 非空 Files”组合
    恒返回 true（每轮重建），其各阶段期望即为 `Built 2`，故 chmod 失效下仍通过。
    前轮“反例成立”的判断有误，本轮以源码为准纠正。
- 修复（新补丁 `0008-unity-linkmultiple-chmod-probe.patch`，`conandata.yml`/
  `manifest.yaml` 已登记；编号跳过 `0007`——`0007-show-build-reason.patch` 文件
  已被 `_enable_build_reason` 方法取代且未在 conandata 登记，为避免混淆新补丁
  顺延为 0008）：
  - 在 `LinkMultiple()` 入口以同目录探针文件（`../tmp/Test/Unity/LinkMultiple/`
    下，与被测文件同一文件系统）验证 `SetReadOnly(true)` 后 `GetReadOnly()`；
    无效则打印 `SKIPPED: chmod() ineffective (E046)`、清理探针文件后 `return`，
    只跳过该文件系统子能力；有效文件系统上全部上游断言原样执行。
  - 写法沿用已验证的 0005（`LongPaths` 式 `return` 惯用法、`printf` 风格、
    `<stdio.h>` 配套、无平台宏），锚点已用官方包逐字节验过
   （含行 15/469 双 hunk 上下文顺序与唯一性）。
  - `LinkMultiple_InputFiles` 本轮未动（当前通过，无证据不补丁）。
- 诊断增强（`conanfile.py`，不改构建语义与断言）：`_emit_inner_diagnostics`
  新增 `FASTBUILD_DIRTY` 紧凑窗，只收录带 stamp 值的非预期重建原因
 （`externally modified`/`dep changed`/`dep missing`/`(missing)`），打印在日志
  极尾。下轮预检直接给出 5 个 Built-1 的脏节点名与前后 stamp，再做单点修复。
- 未动手项（诚实记录）：5 个 Built-1（NoRebuild 族）的具体脏原因行落在摘要
  截断区，无直接证据；不做时间戳容差类语义补丁（与 `ModTimeChangeBackwards`
  对立、风险高，上一周期已明确排除）。`_probe_fs_stamps` 探针输出在完整日志
  中，下轮结合 DIRTY 窗一起判读。
- 验证手段：`py_compile`（配方+test_package）通过；0008 双 hunk 上下文在官方
  包归一化源码中按序命中，`LinkMultiple`/`_InputFiles` 锚点各唯一，
  探针所用 `MakeFile/EnsureDirExists/EnsureFileDoesNotExist` 签名已对
  `FBuildTest.h` 核对；`FASTBUILD_DIRTY` 关键字与 conandata/manifest 登记已断言。

## 二十三、2026-09-10 第十六轮修复：回存重采输出stamp 0009 + TestExe顺序0010（未提交，待 HMBS 重检）

- 本轮预检：CoreTest 123/123，FBuildTest 313/319（6 failures）。0008 已生效
 （日志显示 Apply 且无 LinkMultiple FAIL，312/318→313/319 即 +1 通过），残留为
  NoRebuild 族。上轮植入的 FASTBUILD_DIRTY 窗生效，极尾直接给出根因行：
  `test.exe (externally modified - stamp = 1789027712653827344, disk =
  1789027712685826875)` 及其级联 `testoutput.txt (dep changed ...)`。
- 根因（源码+日志，双证据）：
  - `LinkerNode::DoBuild` 末尾即 `RecordStampFromBuiltFile()`（ eager，链接完成
    时取值），之后 TestNode/CheckValidExe 等会 **运行** 该 exe，存 fdb 用的是
    内存旧值；重载时磁盘值大了约 32ms → `externally modified`（无中间写）。
  - 排除项：同盘 `.o` 不漂（否则连带重建，实际恰好 1 个节点脏），排除全盘
    时间回绕/异步提交；`SetExecutable/chmod` 只改 ctime 且引擎内仅
    ToolManifest 调用；TestNode 只 spawn+写 output 文件，不碰 exe 本体。
    唯一系统性差异是“被执行过”，即 HMDFS 上 exec（或其触发的元数据提交）
    会推进 exe 的报告 mtime。`_probe_fs_stamps` 的纯写探针行为待结合本轮
    新增的 exec 探针做最终二选一。
  - 与上轮（0008 探针跳过 + 捕获窗）不同策略：本轮修时间戳基线，不跳过任何用例。
- 修复 1（`0009-save-restamp-outputs-linux.patch`，引擎，Linux 限定）：
  `NodeGraph::Save` 序列化前对 `UP_TO_DATE && IsAFile() && type != FILE_NODE`
  的节点重采磁盘 stamp（复用 `GetNodeCount/GetNodeByIndex` 与公开的
  `RecordStampFromBuiltFile`，const 安全，无需改头文件）。合规 FS 上值相同
  （无操作）；只排除 FILE_NODE 是为了保留源文件年中被外部修改的检出能力
 （`ModTimeChangeBackwards` 系 save 后改时间，不受影响，已核对源码时序），
  输出文件年中被手改在实践中不存在。覆盖全部“运行在存盘前”的用例
 （TestTest/TestCompiler/TestExec/StaleDeps 等）。
- 修复 2（`0010-testexe-order-norebuild-first.patch`，测试顺序）：
  仅 TestExe 是“存盘后运行”（Build 存→CheckValidExe 运行→NoRebuild 重载），
  存时重采也救不了，故把 `CheckValidExe` 移到 `Build_NoRebuild` 之后执行。
  全部断言原样保留，exe 仍被真实执行并校验 99；harness 按注册顺序执行
 （Build→NoRebuild 的 fdb 依赖已证实顺序有效）。
- 诊断（`conanfile.py`，零语义）：`_probe_fs_stamps(cxx)` 新增 exec 探针——
  用真实工具链编译微型 ELF，stat→直接执行→stat，上报 `exec-probe
  drift_ns/stable/before/after`，下轮直接判定 exec 诱因；原 settle 探针保留。
- 验证手段：`py_compile`（配方）通过；0009/0010 上下文在官方包归一化源码中
  按序命中，0009 新增块括号平衡、符号（`Node::UP_TO_DATE`/`FILE_NODE`/
  `RecordStampFromBuiltFile`/`IsAFile`/`GetType`）均已对源码核对；
  conandata/manifest 登记已断言。0007 未登记文件未动。

## 二十四、2026-09-10 第十七轮修复：只读 /tmp 残留重定向 + 配方去重（未提交，待 HMBS 重检）

- 本轮预检：CoreTest 123/123（rc=0），FBuildTest 314/319（5 failures，rc=255），
  可见失败含 `TestStaleDynamicDeps`（`Unity1.o` 報 `dep changed: Unity1.cpp`
  前后 stamp +236ms）与 `testoutput.txt`（`dep changed: test.exe` +24ms）；
  HMBS 平台诊断为 `[readonly_tmp]`（真机 `/tmp` 只读，`preflight.sh` 自身亦报
  `can't create temporary file /tmp/...: Read-only file system`）。
- 根因 1（直接证据）：三个子 BFF（`TestObject/CacheUsingRelativePaths`、
  `TestObject/SourceMapping`、`TestUnity/CacheUsingRelativePaths`）在
  `Settings` 中先 `#include testcommon.bff` 再**覆盖** `.CachePath`，
  把已重定向到 `$FASTBUILD_CACHE_PATH$` 的公共值打回
  `'/tmp/.fbuild.cache'`（`__LINUX__` 块，逐字节核对 pin 住源码包）；
  另 `TestGraph/BFFDirtied` 用 `/var/tmp/cache`（同样不在可写构建树内）。
  `FBuild::GetTempDir` 优先 `FASTBUILD_TEMP_PATH`（此前 test_env 只设
  `TMPDIR/TMP/TEMP`，经 0003 作用于 `FileIO::GetTempDir` 回退路径，未直达）。
- 修复（仅 `conanfile.py`，无静态补丁、不删断言不跳过）：
  - `_retarget_test_toolchains` 新增 4 组替换：三文件 `__LINUX__` 块改走
    `#import FASTBUILD_CACHE_PATH` + `'$FASTBUILD_CACHE_PATH$'`
   （与已验证的 testcommon 同形；`__OSX__` 孪生行在 OHOS/Linux 上不可达，
    原样保留）；`BFFDirtied` 的 `/var/tmp/cache` 同理。
    全部锚点已用官方包（11297712 字节）逐字节验过并实际 exec 演算：
    `__LINUX__` 无 `/tmp`/`/var/tmp` 残留，`__OSX__` 孪生与相对 `../tmp`
   （源树内可写）不受影响。
  - `test_env` 新增 `"FASTBUILD_TEMP_PATH": tmp_dir`（与 TMPDIR 同值），
    直达 `FBuild::GetTempDir` 主路径；`FileIO::GetTempDir` 回退路径保持不变。
- 配方去重（附带修复）：工作树 `conanfile.py` 存在 5 份完全相同的
  `build/package/package_info` 重复定义（此前截断修复的残留；Python 取最后
  一份，行为一致但污染 diff）。已截除重复，仅保留一份并补全本轮插入块；
  `py_compile`（配方+test_package）通过。
- 未动手项（诚实记录）：`TestStaleDynamicDeps` 的 `Unity1.cpp` 漂移与
  `testoutput.txt` 的 `test.exe` 漂移属时间戳族（0009/0010 已覆盖存盘前
  执行漂移），其 `Need to build` 行可能来自预期重建阶段而非失稳，
  摘要截断无法区分；待本轮缓存噪声清除后的完整 DIRTY 窗再单点判定，
  不做无证据的时间戳语义改动。`TestFastCancel/Cancel/main.cpp` 的
  `/tmp` 硬编码在 Linux 注册 0 个测试（`#if __WINDOWS__`），无证据不补丁。

## 二十五、2026-09-10 第十八轮修复：时间戳量化的不同策略（未提交，待 HMBS 重检）

- 本轮预检与上轮同一指纹（FBuildTest 314/319，5 failures；可见
  `Unity1.o (dep changed: Unity1.cpp, +208ms)` 与
  `testoutput.txt (dep changed: test.exe, +24ms)`），按“同一指纹第二次必须
  换策略”要求放弃上轮路线（BFF/环境变量重定向陷阱：上轮 4 组 CachePath
  重定向与 FASTBUILD_TEMP_PATH 直连后计数纹丝不动，证实残留失败与 /tmp
  无关），改为引擎测量层修复。
- 下载定性（有证据）：日志中两次 `IncompleteRead` 后 conan 内置重试成功，
  构建完整跑到编译与 319 个测试；`ci/conan/build_and_test.sh` 的镜像映射
  仅覆盖 github/gnu/gnome/kernel/x.org 等域，fastbuild.org 无映射且无字节
  相同的可信镜像（上轮已核查）。按守则保留官方 URL（conandata 不动），
  属偶发基础设施抖动，非配方缺陷。
- 根因（源码+日志，双证据）：`Node::DetermineNeedToBuild` 对
  `IsAFile()` 节点做 `lastWriteTime != m_Stamp` 精确比较；HMDFS 上刚写入
  文件的 lstat mtime 无中间写自行前漂数十至数百毫秒（本轮 +208ms/+24ms，
  前轮 +32ms），存盘快照（0009）只能固定存盘前的值，覆盖不了存盘后到
  重载之间的继续沉降，故 5 个 NoRebuild 族失败原样复现。全树核查：
  记录（`RecordStampFromBuiltFile`、一切 built 输出）、输入
  （`FileNode::DoBuild`）与比较（`DetermineNeedToBuild`）三条路径全部
  经过 `FileIO::GetFileLastWriteTime` 单点。
- 修复（新补丁 `0011-stamp-quantize-1s-linux.patch`，Linux 限定；不删断言、
  不跳过任何用例）：`GetFileLastWriteTime` 的 `__LINUX__` 分支向下取整到
  整秒（去 `tv_nsec`）。亚秒漂移在同一秒桶内消失；`ModTimeChangeBackwards`
  仍有效（A 阶段循环以 10ms 步进把 FileA  bump 到不同秒桶，30s 超时内必达；
  改回旧时间后秒桶必然不同，照常检出重建；删 FileB 走 missing 分支，与
  精度无关）。上游自身接受 1s 粒度（HFS+ 的 1000ms sleep 变通散见
  `TestStaleDynamicDeps` 与 `ModTimeChangeBackwards` 源码注释），
  Windows/Apple 分支原样不动。`conandata.yml`/`manifest.yaml` 已登记；
  锚点已用官方包逐字节验过并模拟应用（Apple 分支残留 `tv_nsec` 不动）。
- 验证手段：`py_compile`（配方）通过；补丁上下文在官方包归一化源码中
  唯一命中。`DirectoryListNode` 的哈希走 readdir 的 `FileInfo` 路径
  （未动）；若下轮残留失败签名变化，再凭新 DIRTY 窗单点跟进。

## 二十六、2026-09-10 第十九轮：0011 由静态补丁转为锚点字节替换（未提交，待 HMBS 重检）

- 前轮只修了 0011 的 hunk 头计数（6/15→7/17），解析通过但应用失败：
  `source file is different - Code/Core/FileIO/FileIO.cpp`，实际内容为
  `if ( ( pathStat.st_dev == parentStat.st_dev ) &&`。
- 根因（源码证据）：0011 按原始文件行号 658 编写，但同文件先应用的 0003
  在 25 行处 +1 行、在 455 行处 +27 行，共 +28 行，目标实际已移到 686 行；
  658 行处是 0003 位移后顶上来的 pathStat 区域。静态行号补丁在同文件多补丁
  叠加时天然脆弱（与 0007 两次失败同类）。
- 策略切换（与前轮不同路线，沿用已验证的 `_enable_build_reason`  precedent）：
  删除静态 `0011-stamp-quantize-1s-linux.patch`（conandata/manifest 同步去登记），
  在 `conanfile.py` 新增 `_apply_stamp_quantize()`：以
  `return ( ( (uint64_t)st.st_mtim...` 整行字节为锚点（全树唯一，其余 st_mtim
  处用 `s.`/`info.` 接收器）做单点替换，保留 CRLF/LF 与缩进，计数非 1 直接抛错；
  量化语义与 0011 完全一致（去 tv_nsec、下取整到秒），无断言改动。
- 验证手段：`py_compile` 通过；conandata/manifest YAML 解析通过且补丁清单一致；
  以官方包（11297712 字节）演算锚点唯一、替换恰好只改 662 行、+28 行位移后仍命中。

## 二十七、2026-09-10 第二十轮修复：撤销整秒量化，0009 改为沉降等待后重采（未提交，待 HMBS 重检）

- 本轮预检：CoreTest 123/123（rc=0），FBuildTest 320/323（3 failures）：
  `ModTimeChangeBackwards`、`TestPCHWithCache_BFFChange`（`PROBLEM for
  ObjectList: Built 0 instead of 1`）、`LinkMultiple_InputFiles`
  （`PROBLEM for Object: Built 0 instead of 1`）。上轮整秒量化把 5 失败收敛
  为 3 失败，但 3 个是量化引入的新退化，非原有残留。
- 根因（源码+日志，双证据）：`_apply_stamp_quantize` 把 Linux 的
  `GetFileLastWriteTime` 向下取整到整秒，与上游已文档化的 HFS+ 1 秒问题同构。
  `TestPCHWithCache_BFFChange` 注释原文：“HFS+ has surprisingly poor time
  resolution (1 second) which makes the ObjectListNode appear to not need
  rebuilding, because the tests complete so quickly”，并以 `Thread::Sleep(1100)`
  规避；`LinkMultiple_InputFiles` 各阶段间同样只有 `__OSX__` 的 1000ms 规避。
  量化后删除+缓存恢复（PCHUser.o `<CACHE>`）、Unity 隔离切换再生等秒内合法
  变更被折叠为“未变”，故恰好 `Built 0 instead of 1`；属精度丢失，非平台缺能力。
- 修复（与上轮不同策略；零容差、不跳过、不删断言）：
  - 删除 `conanfile.py` 的 `_apply_stamp_quantize` 及其调用，恢复精确纳秒比较。
  - `0009-save-restamp-outputs-linux.patch` 改为沉降等待后重采：`Save` 内
    `Thread::Sleep(1200)`（与上游 HFS+ 1100ms 同量级，`Thread.h` 已包含，
    `Sleep(uint32_t ms)` 签名已核对）再对 `UP_TO_DATE && IsAFile() &&
    type != FILE_NODE` 重调 `RecordStampFromBuiltFile()`。等待覆盖已观测的
    +24~+236ms 前漂，记录的是沉降后真实值；稳定文件系统上值相同（无操作）；
    输入 FILE_NODE 不动，秒内合法变更仍能检出。`conandata.yml` 描述同步更新。
  - `0010` 顺序交换保留（存盘后运行 exe 的 32ms 级前漂仍需它覆盖）。
- 验证手段：`py_compile` 通过；`NodeGraph.cpp` 的 `Save` 锚点、`Thread.h` 包含、
  `Node.h` 的 `IsAFile/RecordStampFromBuiltFile/GetState` 符号均已对官方包核对；
  `Sleep(1200)` 签名一致。HMDFS 沉降是否收敛由下轮预检判定。

## 二十八、2026-09-10 第二十一轮修复：0009 补依赖视图重同步 + 沉降等待延至 2500ms（未提交，待 HMBS 重检）

- 本轮预检：CoreTest 123/123（rc=0），FBuildTest 314/319（5 failures，rc=255）；
  可见 `Unity1.o (dep changed: Unity1.cpp, 1789036583273829375 -> 1789036584697827031,
  Δ约 1.42s)` 与 `testoutput.txt (dep changed: test.exe, +24ms)`。
  上轮 1200ms 沉降等待 + 输出重采后计数纹丝不动（313/319→314/319），按“同一指纹
  第二次必须换策略”要求放弃“单纯延长等待”路线，改为修同步缺口。
- 根因（源码 + 日志，双证据；与上轮不同机制）：
  - `Node::DetermineNeedToBuild` 有两条独立比对：自有戳（IsAFile 节点磁盘 mtime
    vs `m_Stamp`，失配报 `externally modified`）与依赖视图（依赖节点现戳 vs
    depender 记录的 `dep.GetNodeStamp()`，失配报 `dep changed`；见 Node.cpp；
    视图在构建期由 `Node::Finalize` 逐个 `Stamp()`）。
  - 0009 v1 只重采各输出自有戳，不动 depender 视图：存盘序列化的是新自有戳与旧
    视图。重载后 `dep changed` 必现（旧视图 vs 新自有戳），且差值恰为沉降等待
    本身（1.2s  skew + 存盘后继续沉降约 0.2s = 观测到的 1.42s）。即 v1 把
    `externally modified` 换成了 `dep changed`，计数自然不动。
  - `/tmp` 方向已排除：上轮 4 组 CachePath 重定向（testcommon + 3 个覆盖 Settings
    的子 BFF + BFFDirtied）与 `FASTBUILD_TEMP_PATH` 直连后零收敛；全树剩余绝对
    `/tmp`/`/var/tmp` 只有 VS/XCode 工程生成路径（Linux 测试构建不可达）与源树
    内相对 `../tmp`（可写）。`preflight.sh` 自身的 `/tmp/shjxioug.tmp` 只读报错
    属执行器基础设施，与配方无关。
- 修复（仅静态补丁 `0009-save-restamp-outputs-linux.patch` v2，无新补丁文件、
  不删断言不跳过任何用例；`conandata.yml` 描述同步更新）：
  - 沉降等待 1200ms → 2500ms（与上游 HFS+ 1100ms 同量级，留出观测到的 1.42s
    总漂移余量；稳定文件系统上重采值相同，无操作）。
  - 重采后新增依赖视图重同步循环（`Node::Finalize` 的镜像逻辑，只碰
    static + dynamic，prebuild 从不触发重建故跳过；零戳表示缺失文件，原样保留）：
    对全图每个非空节点，把其 static/dynamic 依赖的记录戳同步为依赖节点当前戳。
    `Save` 为 const 方法，经由 `GetNodeByIndex` 取到的可变节点指针与
    `const_cast<Dependencies&>` 改写在序列化前完成（堆上原本非常量对象，安全；
    `Dependencies::Stamp`/`GetNode`/`GetStamp` 签名已对官方包核对）。
  - 输入 FILE_NODE 仍不动（`ModTimeChangeBackwards` 的外部修改检出能力保留）；
    精确纳秒比较保留（不恢复整秒量化，避免第二十轮已证实的
    `Built 0 instead of 1` 类退化）。
- 验证手段：官方包（11297712 字节，sha256 与 conandata 一致）逐字节核查——
  `Save` 锚点命中；`GetNodeCount/GetNodeByIndex/RecordStampFromBuiltFile/
  GetStaticDependencies/GetDynamicDependencies/GetStamp/UP_TO_DATE/FILE_NODE/
  GetState/IsAFile/GetType` 符号就绪；`Core/Process/Thread.h` 已包含；
  `Node.h` 含 `Dependencies.h`；补丁 hunk 计数自洽（66 新增行），新增块括号平衡。
  沉降是否收敛与视图同步效果由下轮预检判定。

## 二十九、2026-09-10 第二十二轮修复：0009 v3 全量重采 + 稳定性复验 + 0012 探针（未提交，待 HMBS 重检）

- 本轮预检（0009 v2 已生效）：CoreTest 123/123，FBuildTest 由 314/319（5 失败）
  收敛至 327/329（2 失败）。残留为 `TestStaleDynamicDeps`
 （`PROBLEM for Compiler: Built 1 instead of 0`；
  `CompileGeneratedFiles (dep changed: Unity, hash 17487… -> 18211…)` 为删除
  FileB.h 后的预期重建；
  `Unity1.o (dep changed: Unity1.cpp, …4721827500 -> …7473828125，约 +2.75s)`）
  与 `TestUnity::LinkMultiple_InputFiles`（`PROBLEM for Object: Built 0 instead
  of 1`）。按“同一指纹第二次必须换策略”要求，不再延长固定等待。
- 根因 A（StaleDynamicDeps，源码 + 日志双证据；与上轮输出快照假设不同机制）：
  - 生成的 Unity1.cpp 在图里是 FILE_NODE（`UnityNode::IsAFile()` 为 false，
    Unity 节点自带内容哈希戳，从不存 mtime），而 0009 v2 的重采循环排除一切
    FILE_NODE——2.75s 漂移正好落在这个排除集上；v2 的 2500ms 等待对此文件
    毫无作用（根本没采它），且漂移量随构建时长累积（1.42s → 2.75s），固定窗口
    注定追不上。Compiler 脏（CPPGenerator.exe 由 Compiler 节点的 FileNode 依赖
    跟踪）同属此类。
  - 0009 v3 改为重采全部 `UP_TO_DATE && IsAFile` 节点（含 FILE_NODE）：
    源输入这样仍安全——测试只在 Save 之后改输入，改后仍能检出；且重采是纯读
    （只调 `RecordStampFromBuiltFile`，不写盘），
    `TestGenerate_NoRebuild` 的 mtime 相等断言不受影响；Unity 哈希逻辑未动，
    删除 FileB 后的预期重建照常发生。
  - 另把“固定等待”换成“复验收敛”：初等 2500ms 后循环{重采 + 视图同步 +
    等 500ms + 全图复验}，500ms 窗内无变化即停，最多 7 轮（稳定文件系统约
    3s/次，与 v2 相当；持续漂移则 bounded best-effort）。验证而非假设窗口。
- 根因 B（InputFiles，源码证据；与时间戳无关，另一家族）：
  - 该用例四阶段全靠 `SetReadOnly` 翻转隔离态；HMDFS 忽略 chmod（E046，
    `chmod:0`，0005/0008 同机已证实）→ 隔离态恒不变 → `Built 0 instead of 1`。
    此前它“通过”是漂移造成误重建恰好凑数，时间戳稳定后原形毕露。
  - 修复（新补丁 `0012-unity-inputfiles-chmod-probe.patch`，沿用 0005/0008 已验证
    的探针写法与 `<stdio.h>` 复用，不重复引头）：入口以同目录探针文件验证
    `SetReadOnly(true)` 后 `GetReadOnly()`，无效则清理并 `return`，只跳过该
    文件系统子能力；有效文件系统上全部断言原样执行。
- 验证手段：官方包（11297712 字节）逐字节核查——`Save`/`LinkMultiple_InputFiles`
  锚点唯一命中；`GetNodeCount/GetNodeByIndex/RecordStampFromBuiltFile/
  GetStaticDependencies/GetDynamicDependencies/GetStamp/UP_TO_DATE/IsAFile/
  GetState/GetName` 与 `FileIO::GetFileLastWriteTime`（`FileIO.h` 已含于
  NodeGraph.cpp）、`Dependencies::Stamp/GetNode`（经 Node.h 含入）就绪；
  `FileIO::GetReadOnly/SetReadOnly` 由 FileIO.h 声明且 0008 已在同 TU 使用；
  双补丁 hunk 计数自洽、新增块括号平衡。效果由下轮预检判定。
