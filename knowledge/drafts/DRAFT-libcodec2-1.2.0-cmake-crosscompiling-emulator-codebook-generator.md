# DRAFT-libcodec2-1.2.0-cmake-crosscompiling-emulator-codebook-generator — 交叉编译下构建期必须执行的目标架构代码生成器（codebook/查找表）

## 问题（错误签名）

交叉构建（x86_64 构建机 → OHOS aarch64 目标）执行到 codebook 生成步骤时，构建机直接
exec 目标架构生成器，报 `Exec format error`，构建在生成 `codebook*.c` 的第一步中断。
本库适配记录 `archives/l/libcodec2/1.2.0/notes.md` 问题表 #1 原文：

> 交叉构建执行 `generate_codebook` 报 Exec format error ／ 根因：上游为交叉构建生成目标架构工具，
> 但自定义命令直接执行 ／ 解决方案：补丁让 codebook 生成命令显式经过 `CMAKE_CROSSCOMPILING_EMULATOR`

同一事实在 `conandata.yml` 的补丁描述中记为 `"Invoke the codec2_native-built codebook generator
by path (avoids exec-format and target-resolution issues when cross-compiling)"`。
（本地未保留"未打补丁时"的失败日志；该现象以上述仓库内适配记录为据，不另做推断。）

## 根因

上游 `src/CMakeLists.txt:65-88` 的 `if(CMAKE_CROSSCOMPILING)` 分支试图自造一个 "native" 生成器：

```cmake
ExternalProject_Add(codec2_native
   SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/..          # 重新配置同一份源码
   BINARY_DIR ${CMAKE_CURRENT_BINARY_DIR}/codec2_native
   BUILD_COMMAND ${CMAKE_COMMAND} --build . --target generate_codebook
   INSTALL_COMMAND ${CMAKE_COMMAND} -E copy .../generate_codebook ${CMAKE_CURRENT_BINARY_DIR})
add_executable(generate_codebook IMPORTED)
```

缺陷有两层，必须同时成立才会暴露：

1. **嵌套工程没有指定宿主工具链**（无 `CMAKE_ARGS`、无 `CMAKE_TOOLCHAIN_FILE` 复位），嵌套 configure
   沿用构建环境里的 `CC`/`CXX`。而 Conan 的 buildenv 正是
   `CC=/root/ohpc/sdk/ohos-6.0/native/llvm/bin/aarch64-unknown-linux-ohos-clang`、
   `CXX=...clang++`（`.ci_logs/conan_build_libcodec2_1.2.0.log` 第 33-34/58-59 行），于是这个号称
   native 的生成器实际仍被**目标编译器**链接成 aarch64 ELF——构建日志第 232 行可见嵌套工程
   `-- Check for working C compiler: .../aarch64-unknown-linux-ohos-clang - skipped`。
2. **8 处 `add_custom_command`（`src/CMakeLists.txt:91-146`）用裸命令名调用它**：
   `COMMAND generate_codebook lsp_cb ${CODEBOOKS} > codebook.c`——既不是
   `$<TARGET_FILE:generate_codebook>` 也不是绝对路径，CMake 把字面量 `generate_codebook` 写进构建规则，
   由构建机按 CWD/PATH 解析后 exec。

两者相乘：x86_64 构建机上 exec 一个 aarch64 ELF → `Exec format error`。

**关键认知**：这不是"上游没考虑交叉编译"——上游确实考虑了，但它假设"重新配置一次产物就是宿主的"。
只要构建环境把目标 `CC`/`CXX` 以环境变量形式注入（Conan、Waf、Meson 的交叉构建常见做法），
该假设即不成立，"native 分支"会静默产出目标架构二进制，错误推迟到**执行期**才暴露。

## 方案（rec_approach: run-build-time-codegen-through-crosscompiling-emulator）

不删生成步骤、也不把生成器改造成 host-native，而是让目标架构生成器经
`CMAKE_CROSSCOMPILING_EMULATOR` 在**构建机**执行（本库补丁
`archives/l/libcodec2/1.2.0/patches/0001-run-codebook-generator-through-emulator.patch`）：

```cmake
if(CMAKE_CROSSCOMPILING AND CMAKE_CROSSCOMPILING_EMULATOR)
    set(CODEBOOK_GENERATOR_COMMAND ${CMAKE_CROSSCOMPILING_EMULATOR}
        ${CMAKE_CURRENT_BINARY_DIR}/generate_codebook)
else()
    set(CODEBOOK_GENERATOR_COMMAND ${CMAKE_CURRENT_BINARY_DIR}/generate_codebook)
endif()
```

随后 8 处 `add_custom_command` 的 `COMMAND generate_codebook ...` 全部改为
`COMMAND ${CODEBOOK_GENERATOR_COMMAND} ...`，`DEPENDS generate_codebook ${CODEBOOKS}` 原样保留——
生成步骤仍在构建期真实执行，只是执行者由"构建机裸 exec"变成"构建机经模拟器 exec"。

三个易错点：

- 模拟器**从工具链取**（`${CMAKE_CROSSCOMPILING_EMULATOR}`），不硬编码。Conan 侧由 profile 注入：
  `tools.cmake.cmaketoolchain:extra_variables={"CMAKE_CROSSCOMPILING_EMULATOR": "<qemu 包装脚本>"}`
  （`/root/.conan2/profiles/ohos-aarch64-run`、`ohos-aarch64-static` 用 `/root/ohpc/bin/ohos-qemu-aarch64` 包装脚本）。
- 该变量本身是**列表**，支持"命令;参数;参数"。本环境 `ohos-aarch64-local` 档即
  `qemu-aarch64-static;-L;/root/ohpc/sdk/ohos-runroot`。因此必须作为列表整体展开，**不要加引号**包成一个词。
- 回退分支保留产物绝对路径（而非裸命令名），使非交叉构建行为不变、交叉但无模拟器时错误信息更直白。

## 验证

正向（`.ci_logs/conan_build_libcodec2_1.2.0.log`，补丁生效后的完整 CI 构建）：

| 检查 | 命令 | 实测 |
|------|------|------|
| 生成步骤真实发生 | `grep -c "Generating codebook" <log>` | **8**（第 283-290 行） |
| 产物被消费 | `grep -c "Building C object src/CMakeFiles/codec2.dir/codebook" <log>` | **8**（第 326-333 行区间，41%~45%） |
| 产物非空且带上游标记 | `ls -l <build>/src/codebook*.c; head -c 60 <build>/src/codebook.c` | 8 个文件 703 B ~ 200167 B，首行 `/* THIS IS A GENERATED FILE. Edit generate_codebook.c and its input */` |
| 嵌套生成器确为目标架构 | `grep -n "Check for working C compiler" <log>` | 第 105/232/568 行三处均为 `aarch64-unknown-linux-ohos-clang`（含 `codec2_native` 嵌套工程） |
| 模拟器来源可核 | `grep -n CMAKE_CROSSCOMPILING_EMULATOR /root/.conan2/profiles/ohos-aarch64-*` | run/static 档 = `ohos-qemu-aarch64`；local 档 = `qemu-aarch64-static;-L;<runroot>` |

端到端：`conan create` EXIT=0；上游 ctest 真实执行 **75/75 通过（100%）**；`test_package`
消费者 encode/decode 回环 PASS；真机 DAYU200 7 种语音模式回环 7/7（见 PR !12381 正文）。

负控：不施加本补丁时，`COMMAND generate_codebook` 在 x86_64 构建机上执行 aarch64 ELF →
`Exec format error`（即 `notes.md` 问题表 #1 记录的原始失败；本环境未保留该次失败日志，
以仓库内适配记录为据）。

## 禁止做法

1. **删除 / 注释 `add_custom_command` 的生成步骤**：生成器 + 输入数据（本例 `src/data/*.txt` →
   `codebook*.c`）是上游查表数据的唯一真相源，删掉会让构建"看起来成功"，交付物内容却静默改变。
2. **把预生成的 `codebook*.c` 提交进源码或配方冒充构建期生成**：等价于 1，且伪造了"构建期生成"的事实。
3. **把生成器改成 `exit 0` 空壳 / `echo` 假产物**：产物为空或非法，下游编译或运行期才炸。
4. **`-DCMAKE_CROSSCOMPILING=OFF` 强走非交叉分支**：非交叉分支用目标编译器把生成器当普通目标可执行文件
   构建，架构不匹配问题一点没解决，反而把"构建器"混进目标产物。
5. **硬编码模拟器绝对路径进配方**：换 worker 必然失效（本环境模拟器由 profile 注入，正是为了可移植）。

## 适用边界与反例

**适用**：

- 构建期需要运行自产代码生成器/查找表生成器/协议生成器的 CMake 工程
  （`add_custom_command`/`add_custom_target` 里 `COMMAND` 生成器，产物再参与编译）；
- 目标架构 ≠ 构建机架构的交叉构建（OHOS aarch64 on x86_64；同理适用于 Android NDK / Yocto / 嵌入式 aarch64）；
- 上游带 `CMAKE_CROSSCOMPILING` "native helper" 分支、却用嵌套 ExternalProject 重新配置同一份源码的工程
  （工具链经 `CC`/`CXX`/`CFLAGS` 环境变量注入时该分支失效）。

**反例 / 不适用**：

- 生成器本身必须在宿主上因**性能或依赖**原因原生运行（如需宿主专有库、或单次生成耗时极长）→ 走
  `fallback_approach: host-native-generator-via-build-context`（E359 口径），而非模拟器；
- 上游提供显式覆盖开关（如"给出既成数据文件即跳过生成"）且覆盖值与生成结果**逐字节等价**时，
  可用开关替代——但必须附等价性证据，不能默认等价；
- 生成器只读不写、产物不参与构建（纯校验工具）时，跳过不改变交付物，不属本条。

## 与既有条目的差异（查重）

| 条目 | 症状关系 | 处置差异 |
|------|----------|----------|
| E359 Conan 构建上下文编译器映射到 HOSTCC/HOSTLD | 同族：`Exec format error.*build tool`，其 forbid 后果明确写到"代码生成器运行时报 Exec format error" | **相反方向**：E359 把构建期工具真正做成 host-native（构建上下文/第二套 host 工具链）；本条在拿不到 host 工具链时保留目标架构生成器 + 模拟器执行 |
| E456 Windows→OHOS Qt5 host moc/rcc/uic 与 target Qt 分离 | 同族：`Exec format error.*moc` | E456 的前提是**上游本来就提供 host 工具二选一**（`separate-target-qt-and-native-host-tools`）；本条处理的是上游 native 分支被环境变量击穿、且不打算再建 host 工具链 |
| E064 conftest / 宿主首次执行二进制 | 同族：构建期执行二进制失败 | E064 根因是 OHOS 首次执行的**签名/安全弹窗**；本条根因是**架构不匹配**（aarch64 ELF 在 x86_64 上） |
| E467 AutotoolsDeps 导出 LIBS 致 autoconf 最早 run 探针失败 | 预审工具 **TOP1（score=0.34）**；同属「构建期要执行二进制」家族，禁止做法亦为「用开关让探针直接通过」 | E467 处置轴是**读 config.log 修装载器**（探针本身可修好）；本条对象是 build 期**产物生成器**，没有可预置的答案，只能让目标架构二进制在构建机真正跑起来 |
| E159 CMake 交叉模式下 TRY_RUN 跑不了测试程序 | 预审工具 **TOP2（score=0.29）**；同为构建期执行二进制失败的 CMake 场景 | E159 处置轴是**预置 cache 答案**绕过 TRY_RUN（探针结果可外部给定）；本条生成器产物是代码，无法预置。且 E159 的禁止做法是「设 CMAKE_SYSTEM_NAME=OHOS」，与本条正相反——本条**依赖**交叉判定成立才注入模拟器 |
| E486 / E318 / E423 | 均含 `Exec format error` | 分别是签名链路、go test 临时 ELF 签名、binutils 包所有权，无架构不匹配 + 生成器构建期执行语义 |

关键词字面量检索（`grep -rli '<kw>' knowledge/graph knowledge/drafts`）：
`CMAKE_CROSSCOMPILING_EMULATOR` **正式 0 / 其他草稿 0**；`codebook` **0/0**；
`generate_codebook` **0/0**；`lookup table` 正式 0 / 草稿 3；
`add_custom_command` 正式 0 / 草稿 8；`构建期生成` 正式 0 / 草稿 22；
`CMAKE_CROSSCOMPILING` **正式 0** / 草稿 11；`Exec format error` 正式 6 / 草稿 11。

## 关系

- similar_to: E359（构建上下文 host 工具）、E456（host moc/rcc/uic 分离）、E064（构建期执行二进制失败）、
  E467（configure 期 run 探针失败）、E159（TRY_RUN 交叉模式）
- caused_by: 上游 `src/CMakeLists.txt:65-88` 的 native-helper 分支未复位工具链 + `src/CMakeLists.txt:91-146`
  的 8 处裸命令名 `COMMAND`
- prerequisite_of: （无）
- conflicts_with: （无）

## 本库落地证据

- 补丁：`archives/l/libcodec2/1.2.0/patches/0001-run-codebook-generator-through-emulator.patch`
  （8 处 `COMMAND` 全部改为 `${CODEBOOK_GENERATOR_COMMAND}`）
- 配方：`archives/l/libcodec2/1.2.0/conanfile.py`（`generate()` 只设 `BUILD_SHARED_LIBS`/`UNITTEST`/`LPCNET`，
  模拟器完全交由 profile 的 `extra_variables` 注入——配方不写死路径）
- 记录：`archives/l/libcodec2/1.2.0/notes.md` 问题表 #1、`conandata.yml` 补丁描述、`manifest.yaml`
- 构建日志：`.ci_logs/conan_build_libcodec2_1.2.0.log`（本地证据，未入仓）
