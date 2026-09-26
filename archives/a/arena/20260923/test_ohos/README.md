# test_ohos — arena 20260923 HarmonyOS PC 专项验证

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
本目录完全自包含（不依赖兄弟 test_package 目录，可被单独复制/执行）：

  T1  header-only 消费者编译：通过 Conan 包 include 路径引入 arena.h（ARENA_IMPLEMENTATION 展开实现），编译为 aarch64 ELF
  T2  区域增长语义：arena_alloc 跨 Region 分裂（>ARENA_REGION_DEFAULT_CAPACITY），验证内存有效且可写
  T3  arena_realloc/arena_memdup 数据保真（字节级 round-trip）
  T4  arena_sprintf 变参格式化与 arena_rewind/arena_reset 语义（mark 快照回退）
  T5  arena_da_append 动态数组（String_Builder 模式，上游 001 演示同款路径）
  T6  arena_free/arena_trim 释放不崩溃、无泄漏（musl 下重复分配/释放压力循环）
  T7  ELF 主机兼容性：二进制为 ELF64 AArch64（readelf 校验），可在本机直接运行

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。