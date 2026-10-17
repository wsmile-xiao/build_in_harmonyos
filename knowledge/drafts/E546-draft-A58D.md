# E546 — 交叉编译中 build-time generator 与 target artifact 角色混用

> Status: DRAFT | 实例: libmagic/file 5.48（HarmonyOS PC 构建 OHOS AArch64）
> severity 🔴 3 | category: cross-compile, build-system, autotools, ohos

## 错误特征

```
Cannot use the installed version of file (0.8.12) to compile magic support files
Please compile the same version of file(1) as this one.
make[2]: *** [Makefile:396: magic.mgc] Error 1

# 或（异构宿主时的另一面）：
sh: ./src/file: Exec format error
make[2]: *** [magic.mgc] Error 126
```

## 触发条件

- 构建系统: autotools / CMake / meson 任意
- 阶段: 编译（数据产物生成处）
- 形态: 上游构建分两阶段——构建期用工具 X 生成数据/源码产物 D（数据库、枚举头、
  marshal 表……），D 随 target 库一起安装并被其解析；非交叉时 X 就是刚构建的
  target 二进制；**交叉模式（--host ≠ --build）下上游改用 PATH 上的系统工具
  并强制版本一致**（D 的格式与库内解析器版本绑定）。

## 根因分析

以 file/libmagic 为例：`magic/Makefile.am` 的 `FILE_COMPILE` 规则把
`magic/Magdir/*` 文本规则编译成 `magic.mgc` 二进制数据库。configure 判定交叉
后默认 `FILE_COMPILE=file`（PATH 上的系统 file），并检查其版本——构建宿主
HarmonyOS PC 只有 toybox file 0.8.12，版本不符即中断。这是构建系统对
"构建期能运行的工具"与"安装给 target 的产物"两个角色的严格区分：数据格式
版本绑定，工具与库必须同版本；而系统工具与被构建库之间没有任何版本契约。

反面：若构建系统不做区分（或适配者直接 `make` 全量），异构宿主上会尝试执行
target ELF，得到 `Exec format error`。

## 识别方式（输入）

- 日志含 `Cannot use the installed version of <tool>` / `Exec format error`
  出现在某个数据文件（.mgc/生成头/表）的生成规则处；
- `grep -RInE "FILE_COMPILE|add_custom_command|BUILD_EXECUTABLE"` 命中
  构建期运行自家工具的规则；
- 失败点不在编译 .c，而在"工具已链接好之后、生成数据产物"这一步。

## 解决方案

### 推荐方案：宿主与 target 同架构时直接运行 target 工具 + 路径覆盖

HarmonyOS PC 本身是 OHOS AArch64，与 target 同架构同 musl libc——刚构建的
target 工具可在构建宿主直接执行。此时无需单独构建 host 工具：

```make
make -j1 FILE_COMPILE=$PWD/src/file
```

要点：
1. **带路径**传 make 变量覆盖：路径含 `/` 时上游版本检查规则被跳过；
2. 用的是刚构建的**同版本** target 工具——天然满足"工具与库版本一致"约束；
3. 先让工具目标链接完成，再构建数据目标（`-j1` 规避并行时序问题）；
4. 生成的数据库**架构无关**（版本化二进制格式，仅含版本魔数与字节序约定），
   target 库运行时加载不受构建机架构影响。

### 回退方案：两阶段 host-tool / target-library（异构宿主）

构建宿主与 target 异构（如 x86_64 宿主交叉构建 OHOS AArch64）时：

```
build profile（原生编译器）
        ↓ 构建 host 工具（同版本）
        ↓ 用 host 工具生成构建期数据（架构无关）
        ↓
target profile（OHOS 交叉工具链）
        ↓ 构建 target 库
        ↓ 安装数据 + 库 + 工具
```

Conan 侧用 `-pr:b`（build profile）提供构建机编译器，或 `tool_requires`
引入独立原生工具配方；上游若无 HOSTCC/CC_FOR_BUILD 类变量，见 E359 的映射法。

### 禁止（安全边界）

- `|| true` / `ignore_errors` / `-k` 吞掉数据生成失败——包内缺失或陈旧
  数据库，测试与消费者静默拿错误结果；
- 删除数据库生成步骤 / 提交预生成 .mgc 绕过构建——无法验证与所构建库版本
  一致，违反仓库不追踪二进制产物规则；
- 用系统旧版本工具 + 篡改版本检查绕过——数据格式漂移，target 端解析失败
  或识别结果错误。

## 验证方式（输出）

1. 数据产物在构建目录生成且非空（`ls -la magic/magic.mgc`）；
2. **用 target 工具真实运行**验证：`./src/file --version` 输出版本；
   `./src/file <任意文件>` 能给出类型识别；
3. 上游正式测试全量执行（libmagic: `make check` 83/83，`MAGIC` env 指向
   构建目录数据库）；
4. 安装产物 ELF 验证：`readelf -h` 确认 ELF64 / AArch64 / interpreter
   `/lib/ld-musl-aarch64.so.1`；
5. test_package 作为真实消费者加载安装的数据库并识别样例文件。

## 适用范围

- 构建宿主 = HarmonyOS PC（AArch64 OHOS），target = OHOS AArch64
  （同架构同 libc，可直接互跑）；
- 上游存在"构建期运行自家工具生成数据"的两阶段构建。

## 不适用范围

- 异构宿主（x86_64 → OHOS AArch64）：用回退方案两阶段构建；
- 工具与数据有架构相关的行为（如生成的代码嵌入目标指令）：必须按
  E359 映射 CC_FOR_BUILD 或 tool_requires，不能用 target 工具替代；
- 上游工具仅构建期需要且构建机已有等价系统工具（无需任何处理）。

## 可复用于哪类项目

- **file/libmagic**：magic.mgc 由 file(1) 编译（本条目实例）；
- **glib/gobject 系**：glib-mkenums/genmarshal 枚举与 marshal 生成；
- **ICU/unicode 数据表类**：构建期工具把文本码表编译成二进制数据库；
- **语法/解析器生成器**：bison/flex 类构建期生成源码；
- **perl XS / python C 扩展**：构建期运行解释器生成常量头；
- 任何 `add_custom_command(COMMAND $<TARGET_FILE:...>)` 在构建期运行
  刚构建目标的 CMake 项目（CMake 3.x 跨编译时同样要求 host 可执行）。

## 与已有知识的差异

- **E456**（Qt/CMake AUTOGEN 宿主工具）：处理目标侧 `moc`、`rcc`、`uic` 无法在构建宿主执行的问题；E546 聚焦构建期数据生成器与目标库的版本强一致约束，仅在宿主与目标 ABI、系统和 libc 兼容且通过真实执行验证时复用目标工具，否则采用两阶段构建。
- **E423**（交叉 Binutils 身份核验）：处理同一包内宿主工具与目标产物的身份分类和消费者验证；E546 处理构建过程中生成器选择错误及其生成数据与目标库的版本绑定。
- **E486**（GCC 引导构建宿主辅助程序）：处理宿主辅助程序立即执行时的签名要求；E546 不以签名为主要问题，而是解决系统工具版本不匹配及构建期数据库生成失败。
- **E359**（cmus HOSTCC/HOSTLD 映射）：解决"上游有 host 编译变量待映射"；
  本条目解决"上游强制用 PATH 系统工具 + 版本一致性检查"，无 host 变量
  可映射，手法是路径覆盖 + 宿主可直接运行 target 产物；
- **E426**（pico-sdk pioasm）：项目特定的子工程选择问题，非本类通用模式；
- **E284**（host 探测结果误入 target 配置头）：方向相反——那是 host→target
  能力污染，本条目是构建期工具角色的 host/target 分派。
