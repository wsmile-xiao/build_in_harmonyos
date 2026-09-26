# DRAFT-11123 — JNI 共享库在 OHOS 的无 JVM 消费者测试路径（thesias 3.1.1 实证）

- **状态**: UNMATCHED（待 draft-review / promote）
- **触发实例**: thesias 3.1.1（任务 11123），适用所有"JDK 自举构建 + C 层核心默认导出"的 JNI 库
- **日期**: 2026-09-21

## 可复现症状与稳定错误签名

JNI 库在 OHOS 包内做消费者测试时，直觉路径是装 JVM → `System.load` → 跑 jar，随之撞上：

```
javac: command not found / no java runtime
UnsatisfiedLinkError / System.load ... Permission denied
（E083：需要给 JDK 与 JNI 库做 ELF 自签）
```

而走 conan test_package 的共享库消费者还会撞加载器两类坑：

```
Error loading shared library libthesiaslib.so.0: (needed by .../test_thesias)
```
（SONAME 与包内文件名不一致：DT_NEEDED 取 SONAME，按 `libthesiaslib.so.0` 找不到包内 `libthesiaslib.so`）

ctest 运行时即使名字一致也找不到库：conan 2 的 CMakeDeps/CMakeToolchain 不注入 rpath，
ctest 进程也不带 conanrun env，`LD_LIBRARY_PATH` 缺失。

## 根因与最小复现

1. **加载器按 DT_NEEDED（=SONAME）找文件**：链接时 `-Wl,-soname,libthesiaslib.so.0`
   而包内文件名为 `libthesiaslib.so` → 运行必挂。最小复现 = 用 soname≠文件名的
   .so 链接任意消费者程序并运行。
2. **conan 2 无 rpath/无 env 注入**：`grep rpath conan-create.log` 为 0；`cmake.test()`
   起的 ctest 不继承 conanrun env。
3. **JVM 链可以整体不需要**：JNI 库的 C 核心（如 Cephes 数值例程）通常在独立 .c、
   未加 `-fvisibility=hidden`，`nm -D lib*.so | grep " T "` 默认导出——这部分公共
   计算面就是合法的测试 API 面，R34（消费者必须调用被测包 API 并断言行为）由 C 层
   直调完全满足。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| `cmake.test()`（模板默认，wolfmqtt 等静态库可行） | 本例失败：ctest 无 conanrun env，`Error loading shared library libthesiaslib.so.0` |
| SONAME=文件名同形 + 仍走 cmake.test() | 未单独重试，与上一条同根因（env 缺失），直接改方案 C |
| **（采纳）** 直接 `self.run("./test_thesias", env="conanrun")` | ✅ 真实运行，7/7 断言通过 |
| JVM+签名链（E083 路径） | 未走：nm -D 探针判定 C 层可直调后，整条链不必要 |

## 最终方案（三件套 + 一探针）

1. **JDK 自举**（E084 组分）：build() 纯 Python 下载 bishengjdk-17.0.13-ohos-aarch64
   （cmd-pkgs releases）取 `jni.h`/`javac`/`jar`；C 编译器经
   `tools.build:compiler_executables` 获取（R33）。
2. **SONAME=文件名同形**：`-Wl,-soname,libthesiaslib.so`，产物即 `libthesiaslib.so`
   （jna/libjnidispatch.so 同款），免 conan 包内版本 symlink。
3. **消费者直跑**：test_package 的 test() 用 `self.run(binary, env="conanrun")`，
   由 conanrun env 提供 `LD_LIBRARY_PATH` → 包内 lib/。
4. **选型探针**：链接产物 `nm -D | grep " T "`——C 层核心导出（如 igam/ndtri/chdtri
   等 T 符号）即走 C 层数值断言消费者测试；JNI 入口（`Java_*`）的存在性由同一输出
   佐证。**不导出**（全 static/hidden）时才需要考虑 JVM+签名路径。

## 输入输出与真实验证

- thesias/3.1.1 conan-verify 全绿（G1-G4 + L2/L4/L5），conan create 干净构建通过；
- 消费者测试 `./test_thesias` 真实运行：**7/7 断言通过**
  （ndtri/lgam/igam/igamc/chdtr/chdtri/igami 对固定 double 常量，tol 1e-9/1e-6）；
- 全程无 JVM、无 ELF 签名步骤；
- 探针与失败现场留证：`~/tmp/uc2/thesias-3.1.1/`（nm -D 输出、SONAME 不一致版报错）。

## 适用范围、反例、解除条件与风险

- **适用**：构建需要 JDK（jni.h/javac/jar）、但 C 层核心默认导出的 JNI 共享库；
  也适用于任何 conan 2 共享库消费者测试的 env/rpath 坑。
- **反例**：C 核心全 static/`-fvisibility=hidden` 的 JNI 库（探针不过）——此时退回
  JVM+签名链（E083）；上游仅提供静态产物的包不受 SONAME 问题影响（可继续 cmake.test()）。
- **解除条件**：conan 未来给 CMake.test 注入 conanrun env 或默认 rpath 时，第 3 件
  可还原为 cmake.test()。
- **风险**：soname 同形牺牲了版本化 soname 语义；对同一进程加载多版本的场景不适用
  （conan 单包消费场景无此需求）。

## 知识库查重与新增价值说明

- **组分 A**：E084（manual-java-native-build，jna）已沉淀 JDK 自举与 javac -h 机制
  ——本条不重复，直接引用其 URL/做法。
- **组分 B**：E083（sign-jdk-and-library）沉淀 JVM 运行链的签名要求——本条给出其
  **解除条件**：C 层可直调时整条链可跳过。
- **组分 C**：E274（draft-review 相似度命中，根因同"SONAME 与包内文件名不一致"）
  ——SONAME 修复本身不是新增价值，本条仅将其作为三件套组件之一引用。
- **组合后新增的解题路径**（按"组合型知识不判重"申报）：以一行 `nm -D` 探针为
  判据的**消费者测试选型决策**（C 层直调 vs JVM+签名），加上 conan 2 共享库消费者的
  conanrun 直跑工程坑与 A+B+C 组装后的完整可复制链路。该决策对后续所有 JNI 家族包
  可复用，属跨仓库测试选型知识；draft-review 相似度最高 0.42（E492，灰区），与
  E492/E274/E316 的单机制条目无整体重复。
