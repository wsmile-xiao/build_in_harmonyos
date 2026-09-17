# libdwarfp 2.1.0 适配笔记

## 编译环境
- 构建系统: CMake (standard conan CMakeToolchain + CMakeDeps + CMake)
- 编译日期: 2026-09-14
- 编译器: clang 15 (OHOS aarch64)
- 状态: published

## 依赖
- 无 conan 依赖。上游 dwarfp 目标与 libdwarf 消费者库同工程、
  PRIVATE 链接 dwarf，无法独立构建，因此本包把同工程的消费者库
  （libdwarf.a + dwarf.h/libdwarf.h）一并打包以闭合静态链接
- 未声明 requires("libdwarf/2.1.0") 的原因：制品仓（ohpcd）当前
  只有 libdwarf/0.11.1，2.1.0 不可获取（R36 依赖须先发布）；本包
  自含两个库后不依赖任何未发布包
- zlib/zstd 不在本包依赖内：二者是消费者侧可选解压依赖
  （ENABLE_DECOMPRESSION=TRUE 且两者齐备才启用），libdwarfp 源码
  零引用

## 上游构建结构（v2.1.0）
- libdwarfp 与 libdwarf 同属一个 CMake 工程
  （github.com/davea42/libdwarf-code，发布包 libdwarf-2.1.0.tar.xz）
- 顶层 CMakeLists.txt 只有在 `BUILD_DWARFGEN=TRUE` 时才
  `add_subdirectory(src/lib/libdwarfp)`，因此必须连同 libdwarf 与
  dwarfgen 工具一起构建；dwarfgen 可执行文件在 package() 中剔除，
  本包交付 producer 库 + 消费者库（静态链接闭包所需）
- libdwarfp 借用 ../libdwarf 的 dwarf_memcpy_swap.c /
  dwarf_string.c / dwarf_tsearchhash.c 一同编译
- 静态 libdwarfp.a 未定义引用共 135 个（实测 llvm-nm -u），跨库部分：
  公开 API 2 个（dwarf_encode_leb128/dwarf_encode_signed_leb128，
  libdwarf.h:9667/9671）+ 跨库内部符号 7 个（dwarfstring_* 家族，
  借用的 dwarf_string.c 同时编入两归档）；dwarf_add_AT_reference_c
  与 dwarf_force_dnames 为归档内跨目标符号（定义于 libdwarfp.a
  自身，最终链接自闭合）

## 编译步骤
```bash
# CMake build using conan
cmake -B build \
    -DBUILD_NON_SHARED=ON \
    -DBUILD_SHARED=OFF \
    -DBUILD_DWARFGEN=ON \
    -DBUILD_DWARFDUMP=OFF \
    -DBUILD_DWARFEXAMPLE=OFF \
    -DDO_TESTING=ON
cmake --build build -j2
ctest --test-dir build --output-on-failure -E selfdwarfdump
cmake --install build
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 仅构建 dwarfp 目标无法独立配置 | 上游 dwarfp 目标与 libdwarf 同工程，且 target_link_libraries(dwarfp PRIVATE dwarf) | 连同整个工程构建（BUILD_DWARFGEN=ON），打包时剔除工具与工程打包元数据 |
| 2 | 静态链接 test_package 报 dwarf_encode_leb128 等未定义 | 静态 libdwarfp.a 不内嵌伴生库符号（未定义引用共 135）：跨库公开 API 2 个（dwarf_encode_leb128/dwarf_encode_signed_leb128，libdwarf.h:9667/9671）+ 跨库内部符号 7 个（dwarfstring_* 家族，借用的 dwarf_string.c 同时编入两归档）；dwarf_add_AT_reference_c/dwarf_force_dnames 为归档内跨目标符号（定义于 libdwarfp.a 自身，自闭合） | 包内同时交付 libdwarf.a，cpp_info.libs = ["dwarfp", "dwarf"] |
| 3 | requires("libdwarf/2.1.0") 无法解析 | ohpcd 制品仓没有 libdwarf/2.1.0（仅 0.11.1），R36 要求依赖先发布 | 改为自含式打包（两库同包，参考 libdwarf 配方 with_dwarfgen=True 路径），并附带两库 license |
| 4 | 上游测试选项易被误记为 BUILD_TESTING | libdwarf/2.1.0 配方 test_package/MANIFEST.yml 误记 | 实际选项是 DO_TESTING（顶层 CMakeLists.txt line 29），本配方 MANIFEST.yml 已写正 |
| 5 | 直接 ctest 会跑 dwarfdump 回归差分测试 | selfdwarfdump* 仅由 DO_TESTING AND NOT WIN32 把守，需要 dwarfdump 二进制 + python3 | 包内构建用 ctest -E selfdwarfdump 只跑自包含单元子集；全量套件已在设备原生验证 |

## 上游测试（RUN，设备原生）
- 入口：`cmake -DDO_TESTING=ON`（另开 BUILD_DWARFDUMP=ON、
  BUILD_DWARFEXAMPLE=ON 以覆盖全部入口）+ `ctest`
- 结果：26/26 全部通过（含 selftestextrastring、selfleb、selftied、
  selfregex 等 20 个自包含单元测试，selfdwarfdumppe/elf/macho 三个
  dwarfdump 回归差分测试，selfjitreader、selfdebuglinka/b 三个
  dwarfexample 测试）
- 配方内 build() 集成的是自包含单元子集（ctest -E selfdwarfdump，
  20 项），原因见上表 #5

## 关键设计决策

### 1. 链接闭包自含式打包
静态 libdwarfp.a 存在消费者库公开符号的未定义引用，且上游不允许
dwarfp 目标脱离 dwarf 目标单独构建。本包 cpp_info.libs =
["dwarfp", "dwarf"]，与 libdwarf 配方 with_dwarfgen=True 路径
（单包双库）同构，保证下游静态/动态链接一次闭合。
注意：若下游同时使用独立的 libdwarf 包，会与本包的
dwarf.h/libdwarf.h 头文件冲突（版本不同时），应二选一。

### 2. 打包范围
交付 include/{libdwarfp.h, libdwarf.h, dwarf.h} 与
lib/{libdwarfp.a, libdwarf.a}（shared=True 时为对应 .so）+ 双
license。cmake/、pkgconfig/、share/、bin/（dwarfgen 工具）剔除。

### 3. 静态构建宏
沿用 libdwarf 2.1.0 引入的约定：静态构建时
`cpp_info.defines = ["LIBDWARF_STATIC=1"]`（libdwarfp.h 的 DWP_API
与 libdwarf.h 的 DW_API 都依赖该宏选择正确的声明形式）。

### 4. 交叉编译处理
- 使用 `cross_building(self)` 检测交叉编译环境
- 设置 `HAVE_UNUSED_ATTRIBUTE_EXITCODE=0` 跳过需要运行的 CMake
  try_run 检查（原生构建无需）
- test_package 使用 `can_run()` 守卫，交叉编译时跳过运行时测试

## 验证结果
- libdwarfp.a/libdwarf.a 静态库编译成功
- 上游 26/26 测试通过（设备原生，含 dwarfdump/dwarfexample 全开关）
- test_package 真实调用 producer API（init → die → attr →
  transform → section bytes → finish → 错误路径）并校验 DWARF5 CU 头

## 交付物
- lib/libdwarfp.a、lib/libdwarf.a
- include/libdwarfp.h、include/libdwarf.h、include/dwarf.h

## 注意事项
- libdwarfp.h 自身并不 #include libdwarf.h（头内注释与实际不符，
  上游文档瑕疵），消费侧代码需先包含 <libdwarf.h> 再包含
  <libdwarfp.h>；三个头文件本包全部提供
- producer 的 Dwarf_Error 使用 producer 私有结构布局，与消费者库的
  Dwarf_Error 不同：producer 错误对象严禁传给 dwarf_errmsg() 等
  消费者 API（实测段错误），只能断言失败本身
- zlib/zstd 属于消费者侧解压能力，由 libdwarf 包按需引入；本包内
  的 libdwarf.a 构建时未启用解压（构建环境无 zlib/zstd 头）
- 与同仓库的 libdwarf/2.1.0、dwarfutils/2.3.1 同上游不同组件
