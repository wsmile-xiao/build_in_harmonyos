# DRAFT-gated-sublib-dual-archive-closure：单工程门控子库的静态链接闭包与伴生库未发布下的单包双库自含打包

> Contributor: libdwarfp-2.1.0 适配 | Status: Draft | Updated: 2026-09-14
> Source: archives/l/libdwarfp/2.1.0（round-1 CI 一次通过；上游测试 26/26 原生全过）

## 现象

libdwarf 2.1.0 上游是"单工程多库"结构：消费者库（libdwarf，读）与
生产者库（libdwarfp，写）同属一个 CMake 工程，发布包只有一个
`libdwarf-2.1.0.tar.xz`。为 libdwarfp 单独立 Conan 包时连续命中三类
阻塞：

1. **构建失败（门控）**：顶层 `CMakeLists.txt` 仅在
   `BUILD_DWARFGEN=TRUE` 时 `add_subdirectory(src/lib/libdwarfp)`
   （默认 FALSE），缺省配置下 dwarfp 目标根本不存在；且
   `target_link_libraries(dwarfp PRIVATE dwarf)` 同工程链接伴生库，
   子库无法独立配置/构建。
2. **链接失败（静态归档未定义符号）**：静态 `libdwarfp.a` 不内嵌
   伴生库符号。`llvm-nm -u` 实测共 135 个未定义引用，其中跨库部分：
   - 跨库公开 API 2 个：`dwarf_encode_leb128` /
     `dwarf_encode_signed_leb128`（libdwarf.h:9667/9671）；
   - 跨库内部符号 7 个：`dwarfstring_*` 家族（append /
     append_length / constructor / destructor / reset / string /
     strlen）——源码来自借用文件 `dwarf_string.c`，同时编入
     libdwarfp.a 与 libdwarf.a 双归档；
   - 归档内跨目标符号 2 个：`dwarf_add_AT_reference_c` /
     `dwarf_force_dnames`——在部分成员里未定义，但定义于
     libdwarfp.a 自身其他成员，最终链接自闭合。
   只打包子库 `.a` 的包对静态下游必然 `undefined reference`。
3. **依赖闭包断裂（伴生库未发布）**：`requires("libdwarf/2.1.0")`
   无法解析——ohpcd 制品仓只有 libdwarf/0.11.1。CI 门禁 R36/L0i 对
   每个 `requires` 用 `conan download --only-recipe` 探测
   （ci/conan/build_and_test.sh:481-529），未发布依赖是确定性 fail
   （`L0_RESULT=fail: unpublished_deps`），不是可重试问题。

## 与现有知识的关系

- **E277（build-vendored-to-staging）— 最相近，不重复**：E277 处理
  上游自带 vendored 依赖源码的"源码级内嵌"（staging 内联编译）；本条
  处理"制品级同工程双归档同包"（两库都来自同一构建树，cpp_info.libs
  闭合）。触发面与修法均不同，互链区分。
- **E278（CMake 条件排除内部目标后静默降级 -l 库名）— 机理互补**：
  E278 是"消费者仍引用被条件排除的内部目标 → CMake 静默生成
  -l<name> → 链接期失败"；本条第 (1) 层是其变体：门控选项关闭时
  dwarfp 目标缺失，唯有显式打开选项才可构建。互链区分。
- **DRAFT-KPACKAGE-KARCHIVE-619-ZLIB-DISCOVERY（kpackage/6.18.0.2
  消费 karchive/6.19.0，消费侧）— 依赖闭包大类消费侧对照案例，
  互补不重复**：该条在消费方配方层显式注入传递依赖
  （KF6ArchiveConfig 的 find_dependency(ZLIB/OpenSSL) 与 pkg-config
  zstd 路径 + 链接 flag）；本条是生产侧在 requires 不可行（R36
  未发布）时的同包双库闭合。单向互链：本主条指向它，它侧是否回链
  由知识库主编复核时定。本条 error_signature 保留通用模式
  `static library.*transitive dependencies`（源自 librsvg 2.62.3
  静态归档传递符号案例；该案例原引用的 DRAFT-staticlib-transitive-libs
  条目在候选基线 5dff0c6a5c1 语料中不存在——官方仓旧克隆与本基线
  因历史重写非祖先关系（merge-base=227a79b4e7bf），语料重写背景
  如实注明，不影响模式本身的通用性）。
- **E007（autotools config.guess）**：本库 autotools 入口不可用属
  E007 覆盖范围，复用，不在本条重复申报。
- **第二实例广度（基线配方树同模式实测）**：基线 archives 配方树中
  "cpp_info.libs 多归档列表 / append / extend"（单包多归档闭包）
  实测命中 250 个 conanfile.py，可复算：
  `git grep -l -E 'cpp_info\.libs = \[[^]]*,|cpp_info\.libs\.(append|extend)' -- archives | grep -v test_package | wc -l`
  （libdwarf/2.1.0 配方 with_dwarfgen=True 路径的
  `libs=["dwarf"]` + `append("dwarfp")` 即同型实例）。

## 方案（决策规程）

1. **门控探测**：读顶层 CMakeLists.txt，确认子库
   `add_subdirectory` 被什么 option 守卫（如 BUILD_DWARFGEN）；
   配方构建时显式打开该选项（整工程一起构建）。
2. **符号探测**：构建后 `llvm-nm -u lib<sublib>.a | grep -c ' U '`
   与逐符号清单，区分跨库公开 API / 跨库内部符号 / 归档内跨目标
   符号，确认伴生库归档必须随包。
3. **依赖模式决策**：探测伴生库制品仓版本——注意 CI 门禁实际语义是
   `conan download "<dep>/<ver>" -r <remote> --only-recipe`（R35/R36），
   `conan list` 仅作人工佐证。未发布 → 走自含式打包；已发布且 R37
   允许 → 可用标准 requires() 模式。
4. **自含打包要点**：同时交付两库归档 + 全部公共头文件 + 各自
   license；`cpp_info.libs = [<sublib>, <companion>]`（与 libdwarf
   配方 with_dwarfgen=True 路径同型）；静态构建补
   `LIBDWARF_STATIC=1`；剔除工具可执行文件与工程打包元数据
   （bin/、lib/cmake、lib/pkgconfig、share/），并在 notes 声明与
   伴生库独立包的头文件共存警示。
5. **回退路径（诚实权衡）**：伴生库版本日后发布制品仓且过 R37 版本
   占用检查后，可回退 requires() 模式；受制于发布节奏，不可作为当期
   前提。

## 验证证据

libdwarfp 2.1.0 在 HarmonyOS PC（OHOS aarch64）单包 CI：

- `llvm-nm -u libdwarfp.a`：未定义引用共 135；跨库公开 API 2
  （dwarf_encode_leb128/dwarf_encode_signed_leb128）+ 跨库内部 7
  （dwarfstring_*）+ 归档内跨目标 2（dwarf_add_AT_reference_c/
  dwarf_force_dnames，定义于 libdwarfp.a 自身），其余为 libc 与
  producer 内部符号。
- `conan download "libdwarf/2.1.0" -r ohpcd --only-recipe` → 报错
  （`conan list "libdwarf/*" -r ohpcd` 佐证仅 0.11.1）→ R36 规避
  动机实证。
- 采用单包双库自含打包后：权威 CI round-01 一次通过（1/1，100%，
  L0/L1/L4/L5 pass），test_package 真实调用 producer 全流程
  （init → die → attr → transform → section bytes → finish →
  错误路径，11 断言）链接运行全过；上游测试 26/26 原生全过。

## 禁止做法

- 不要对未发布到制品仓的依赖版本声明 `requires()`——CI R36/L0i
  确定性 fail，重试无意义。
- 不要只打包子库 `.a`（`cpp_info.libs` 仅 [子库]）——静态归档不内嵌
  伴生库符号，下游链接必失败。
- 不要假设"打开门控选项只构建子库目标"——上游门控下子库目标
  PRIVATE 链接伴生库目标，必须整工程构建，再在打包层裁剪产物。
- 探测未定义符号时 `llvm-nm` 的开关是小写 `-u`（`-U` 是 BSD 风格
  "不显示未定义"，语义相反）；归档内跨目标符号（部分成员 U、其他
  成员 T/D）不能只看单个成员的 nm 输出下结论。
