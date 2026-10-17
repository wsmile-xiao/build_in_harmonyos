# DRAFT-E736：HarmonyOS CMake 平台模块缺失的 rpath 后果面 —— CMAKE_BUILD_RPATH 静默无效、构建树内 ctest 加载共享库失败

> Status: **Draft**（待审核 promote）| severity: `2` | category: `cmake|build-system|testing|linking|ohos` | Updated: 2026-09-25
> 对应: `knowledge/drafts/DRAFT-E736-harmonyos-cmake-missing-platform-rpath-ctest-ld-library-path.kv`
> 来源: libproperties 1.1.2 适配（github/tinyhubs/libproperties tag `1.1.2`，sha256 `9ee3903648f8de6c9e2d71fd778721844cc9881dcc2afe2c66cdb2d1cb86b39a`）
> 取号: `knowledge_id.py --claim --task libproperties-1.1.2` → **E736**（三面并集回查未占用）

---

**匹配关键词**：HarmonyOS, CMAKE_SYSTEM_NAME, Platform module, rpath, CMAKE_BUILD_RPATH, CMAKE_INSTALL_RPATH, LD_LIBRARY_PATH, ctest, Error loading shared library, Error relocating, RUNPATH, DT_SONAME, SONAME flag, 版本化文件名, 构建树内测试

## 错误签名（error_signature）

```text
Error loading shared library [^ ]*\.so|Error relocating [^ ]*: [A-Za-z0-9_]+: symbol not found|System is unknown to cmake|tests failed out of [0-9]+
```

## 预扫（prescan）

- `prescan_pattern`: `add_test\s*\(|enable_testing\s*\(|CMAKE_(BUILD|INSTALL)_RPATH|CMAKE_SHARED_LIBRARY_SONAME`
- `prescan_globs`: `CMakeLists.txt, conanfile.py, test_package/*`
- `prescan_severity`: 2

> 触发面：工程里出现 `add_test`/`enable_testing`（说明要在构建树里跑测试）**或**配方里出现
> `CMAKE_BUILD_RPATH`/`CMAKE_INSTALL_RPATH`（说明作者以为原生机制能用）即预扫命中。

## 根因（root_cause）

一条根因、两个**可独立观测**的后果面（2026-09-25 设备实测，cmake 4.1.2 / clang 15.0.4 / aarch64）：

1. **系统名注入**：Conan 的 OHOS profile 把 `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS` 写进
   CMakeToolchain；设备裸跑 CMake 也认这个系统名。
2. **平台模块缺失**：CMake 按 `Modules/Platform/<SYSTEM_NAME>.cmake` 查找，设备 cmake 4.1.2 没有
   `Platform/HarmonyOS.cmake`（`ls` → `No such file or directory`），configure 首屏逐字打：
   `System is unknown to cmake, create: Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org...`
3. **后果面 A（本条主体）：rpath 机制整体静默失效**。rpath 旗标本应从 `Platform/Linux.cmake` 继承，
   链接链路断裂后 CMake 不向链接器加 `-Wl,-rpath`。实测**显式** `-DCMAKE_BUILD_RPATH=<dir>` +
   `CMAKE_SKIP_RPATH=NO` 的情况下，`readelf -d <测试可执行文件> | grep -cE 'RPATH|RUNPATH'` 仍为 **0**。
   于是构建树里跑 `ctest` 时，musl 加载器按裸 soname 找不到同目录的共享库 ⇒
   `Error loading shared library libX.so.N` ⇒ `0% tests failed ... out of N`。
   形态极像「库坏了 / 工具链坏了」，实际编译与链接全程正常——**失败只发生在运行期解析**。
4. **后果面 B（同根因，已有条目侧记）**：`CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG` 同样未定义 ⇒
   不仅没有 `DT_SONAME`，**CMake 连版本化文件名都不生成**，`cmake --install` 后安装树里只有一个裸
   `libX.so`（无 `.so.1` / `.so.<ver>`），W3 报 `L5a: … 缺少 DT_SONAME`。
   libproperties 实测：未注入 flag 时 `ls install/lib` → `libproperties.so` 一个文件；
   注入后 → `libproperties.so -> libproperties.so.1 -> libproperties.so.1.1.2`。
5. **③④ 必须一起修**：只补 SONAME flag 而不给测试注入 loader 路径，ctest 依旧红；
   只注入 LD_LIBRARY_PATH 而不补 SONAME flag，测试绿了但产物仍是半套（缺 DT_SONAME、缺版本化文件名），
   W3 L5a 会在 CI 侧爆。

**为什么这不是「库的 bug」**：同一份源码在无该平台缺口的环境下（或加了 flag 之后）逐字节同一套命令全绿，
失败只取决于「平台模块是否加载」这一个变量——见下方正反对照。

## 推荐方案（rec_approach: `scoped-ld-library-path-for-ctest-plus-soname-flag`）

生产侧两步，**都不改上游文件、不加补丁**：

```python
# conanfile.py :: generate()
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"   # 消后果面 B（纯 C 工程只加 C 项）
# conanfile.py :: build()，cmake.build() 之后
build_dir = self.build_folder
os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
    [build_dir] + ([os.environ["LD_LIBRARY_PATH"]] if os.environ.get("LD_LIBRARY_PATH") else [])
)
self.run('ctest --test-dir "{}" --output-on-failure'.format(build_dir), cwd=build_dir)
```

要点：

- **作用域收窄**：`LD_LIBRARY_PATH` 只在本次测试命令的进程树内生效，不进 `package()`、不进交付面、
  不影响消费者环境；消费者侧（`test_package`）由 Conan 的 `conanrun` 自己给出包 `lib/` 路径。
- **纯 C 工程只注入 C 项**：同时注入 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 会在纯 C 工程打出
  `Manually-specified variables were not used by the project: CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG`
  （libproperties 实测），是噪声不是错误。
- **与 P-ENV-001 的关系**：该原则要求优先用构建系统原生机制（RPATH 等）。本平台的原生机制已实测为
  no-op（段2），因此这是**降级**而非偏好——符合 P-BUILD-001「平台限制必须降级而非绕过」，
  并把作用面压到单条测试命令。

## 证据（evidence，逐字）

段1（平台模块缺失）：

```text
$ ls /data/service/hnp/share/cmake-4.1/Modules/Platform/HarmonyOS.cmake
ls: .../Platform/HarmonyOS.cmake: No such file or directory
$ cmake -S . -B b   # 首屏
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org so it can be added to cmake
```

段2（最小工程，`-DCMAKE_BUILD_RPATH=<build dir>` 已显式给出）：

```text
RPATH/RUNPATH count: 0
libq736.so                      # 只有裸 .so，无 .so.1 / .so.<ver>
--- ctest without env ---
0% tests passed, 1 tests failed out of 1
--- ctest with LD_LIBRARY_PATH ---
100% tests passed, 0 tests failed out of 1
```

段2 失败轮日志（`Testing/Temporary/LastTest.log` 逐字）：

```text
Error relocating .../b/t: q736: symbol not found
```

正反对照（libproperties 1.1.2 真实工程，同一份源码、只差一个 configure 变量）：

```text
# 未注入 SONAME flag
$ ls install-plain/lib
libproperties.so                                   # 无 DT_SONAME、无版本化文件名
$ dlopen("libproperties.so.1", RTLD_NOW)
dlopen failed: Error loading shared library libproperties.so.1: No such file or directory   # rc=1

# 注入 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG="-Wl,-soname,"
$ ls install-fixed/lib
libproperties.so -> libproperties.so.1 -> libproperties.so.1.1.2
$ readelf -d install-fixed/lib/libproperties.so.1.1.2 | grep -i soname
 0x000000000000000e (SONAME)  Library soname: [libproperties.so.1]
$ readelf -d build/libproperties_test | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libproperties.so.1]      # 裸名，不是路径形
$ (cd build && LD_LIBRARY_PATH=$PWD ctest)
100% tests passed, 0 tests failed out of 2                               # rc=0
```

干净轮（conan create，配方 `build()` 内）逐字：

```text
RUN: ctest --test-dir ".../build/Release" --output-on-failure
1/2 Test #1: 1.properties .....................   Passed    0.03 sec
2/2 Test #2: 2.properties .....................   Passed    0.02 sec
100% tests passed, 0 tests failed out of 2
```

## Fallback

1. **（优先级 2）补丁给测试挂 ENVIRONMENT**：在上游 `CMakeLists.txt` 的 `add_test()` 后追加
   `set_tests_properties(<case> PROPERTIES ENVIRONMENT "LD_LIBRARY_PATH=${CMAKE_BINARY_DIR}")`
   —— CMake 的测试级原生机制，作用面更窄。代价：改动上游文件 ⇒ `refresh-patch` 两面同步 +
   补丁三关（NUL=0 / `@@`≥1 / 真 apply 后与目标树 `cmp` 一致）；且只对用 CMake 注册用例的工程有效，
   裸 Makefile 工程没有这个挂点。
2. **（优先级 3）改静态构建**：`BUILD_SHARED_LIBS=OFF`，运行期无加载器解析问题。代价：交付面与上游
   默认（shared ON）不一致，**完全失去 DT_SONAME/版本化文件名的覆盖**，W3 L5a 与消费者 dlopen 场景
   不再被验证——只在产物本就不需要共享形态时用。

## 禁止（forbid）

1. **`forbid_1`：把 `CMAKE_BUILD_RPATH` / `CMAKE_INSTALL_RPATH` / `CMAKE_SKIP_RPATH` 当作修复**
   —— 本平台这三个变量是静默 no-op，设完 `readelf` 仍是 0 条 RPATH/RUNPATH，给人「已修复」错觉；
   后果是 ctest 继续红、排障方向被带偏到「库/工具链坏了」，反复重配重编仍不绿。
2. **`forbid_2`：把上游测试从 `build()` 摘掉来消红**
   （注释掉 `self.run(... ctest ...)`、或关掉 `LIBPROPERTIES_TEST` 等测试开关）—— 属伪造通过面：
   上游套件不再执行，CI L1c 找不到 ctest 痕迹，N/N′ 口径随之塌陷；
   后果是违反 R51「上游测试必须真实执行」，外部审查按「实测 N > 声明 N」或无执行痕迹判不通过。

## 探针注意事项（避免假阴性）

段2 的共享库**不要**叫 `libm.so` / `libc.so` 等会被加载器特殊解析的名字：实测用 `libm.so` 时，
即使 `LD_LIBRARY_PATH` 正确指向该目录、`readelf --dyn-syms` 明确看到符号 `m` 已导出，
运行仍报 `Error relocating ./t: m: symbol not found`（rc=127）——这是探针自身的假阴性，
与本条根因无关，换成普通名字（如 `libq736.so`）后读数立刻恢复自洽。

## 去重与关系

- **E537**：记录「无 DT_SONAME ⇒ 路径形 DT_NEEDED」的**症状面**与消费侧修补；本条补 rpath 后果面
  （`CMAKE_BUILD_RPATH` 静默 no-op → 构建树内 ctest 失败）与「版本化文件名也不生成」这一观测，
  并把修复统一收在生产侧 configure 期。
- **E096**：同一根因（平台模块缺失）的 C++ 标准检测后果面（需显式 `CMAKE_CXX_STANDARD`）；互补不重复。
- **`DRAFT-cmake-harmonyos-platform-soname-flag`**：已有的 SONAME 专条，覆盖后果面 B；
  本条与之**并列**（不同草稿号、不同后果面），建议 promote 时在两条之间互挂 `similar_to`。
- **E092**（`conan-verify` G0 会提示的「CMake 不认识 HarmonyOS 作为目标平台」）：同源提示，
  但 G0 只是告警、不解释「为什么设了 RPATH 还是没用」，本条给出该问题的可复现读数。

## 原则挂钩

- **P-ENV-001**（环境变量与构建系统语义冲突陷阱：应优先构建系统原生机制）——本条是对它的
  **有据例外**：原生机制已实测 no-op，故降级到作用域受限的 `LD_LIBRARY_PATH`，并写明理由。
- **P-BUILD-001**（平台限制必须降级而非绕过）——不删上游测试、不改判据，只换执行环境。

## 五项质量门槛自检

1. 规则式标题 + 问题类 slug（无库名-版本命名；库名仅进 `source_event` 当案例）——✔
2. rec + 双 fallback（含诚实权衡）+ 2 条 forbid（reason + consequence）——✔
3. `verification_cmd` 自包含：段1（`ls`）+ 段2（写最小工程 → `cmake` → `readelf` → 双轮 `ctest`）
   全部落在 `$HOME/tmp/e736-rpath-probe`，新 shell 可跑，不引用本 run 任何日志路径，
   并已**实测跑通**（三条读数 0 / 0% / 100% 与上文一致）——✔
4. `principles` 挂钩（P-ENV-001、P-BUILD-001）、`affected_scope` 泛化句式、
   `similar_to` 链 E537/E096 ——✔
5. 本 run 配额：仅此 1 条（`malloc.h` 只在 `#ifdef _MSC_VER` 分支、`alloca.h` 非 MSVC 分支
   等 W0 结论属**未触发**的安全面，不构成知识增量；L4 NX 判据误报归 `feedback/pending/`
   工具问题，不进图谱）——✔
