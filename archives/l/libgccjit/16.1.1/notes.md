# libgccjit 16.1.1 适配笔记

## 版本说明（重要）

- 看板任务为「libgccjit 16.1.1」（ID 8204，lang=c，路径 C 候选）。
- **上游不存在 16.1.1**：GCC 官方仅发布 16.1.0 / 16.2.0；gcc-16.1.1.tar.xz 返回 404。
- libgccjit **没有独立源码包**：它是 GCC 发行版的一部分，通过
  `--enable-languages=c,jit` 构建。
- 本配方沿用看板版本号 `16.1.1`，conandata.yml 实际映射到
  `gcc-16.1.0.tar.xz`（sha256 见 manifest.yaml）。PR 申报时须如实说明版本修正。

## 编译环境
- 构建系统: autotools-custom（GCC 顶层 configure + make）
- 编译日期: 2026-09-15
- 编译器: clang / clang++（OHOS SDK，全程宿主编译器，因 OHOS 无 cc1plus —— 知识 E053）
- 状态: pending（CI 完成后更新）

## 编译步骤

1. `ohc-run.py init-build libgccjit 16.1.1` 下载并解压 gcc-16.1.0.tar.xz
   + GMP 6.3.0 / MPFR 4.2.2 / MPC 1.3.1（download_prerequisites 官方 in-tree 版本）。
2. `ohc-run.py conan-init` 生成配方骨架后，参照 gcc/9.5.0 配方改造：
   - class/name/version/package_type 改为 libgccjit 16.1.1 library。
   - `--enable-languages=c,jit` + `--enable-host-shared`（libgccjit 硬性要求，
     整个编译器以共享库方式链接进 libgccjit.so）。
   - 其余 OHOS 处理（musl ABI、ELF 签名、串行 make、unlimited stack、
     umask 022、PIE 保留、GNU as/ld、sysroot 推导）沿用 gcc/9.5.0 配方。
3. `ohc-run.py pre-analysis`（已生成 pre-analysis.md）→ `conan create`。
4. test_package 用 gcc_jit API 做真实 JIT 编译+执行验证（见下）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 看板版本 16.1.1 不存在 | 上游仅 16.1.0/16.2.0 | 用 gcc-16.1.0.tar.xz，申报时说明 |
| 2 | pre_analysis.py 全树扫描超时 | 11.9 万文件 × 20+ 模式，HMDFS 慢 | 单遍快速扫描脚本（复用 skill 的 DETECTION_PATTERNS） |
| 3 | 布局不一致 | pre_analysis 期望扁平 `archives/l/libgccjit-16.1.1/src`，init-build 用嵌套 `archives/l/libgccjit/16.1.1` | 报告归位到嵌套布局，清理扁平目录 |
| 4 | libgccjit.so 需链接进整个编译器 | 共享库需要宿主代码 PIC | `--enable-host-shared` |
| 5 | JIT 运行时生成可执行内存 | W^X / SELinux 限制 | E045：2026-04 W^X 放宽，`mmap RWX` 可用（Cling 同轴） |
| 6 | `jit-target.h` 报 `std::_Hash_bytes` 不存在 | libstdc++ 私有哈希函数，OHOS 只有 libc++ | prepare 脚本将其替换为可移植 FNV-1a 64 位哈希（行为一致，仅桶分布不同） |
| 7 | `system.h` 的 `#define abort()` 宏把 libc++ `<functional>` 里 `std::abort()` 重写为 `std::fancy_abort()` 编译失败 | GCC 内部把 abort 宏映射到 fancy_abort 报错；libc++ 头文件直接调用 `std::abort()`（libstdc++ 则放在 .cc 中不受影响） | prepare 脚本在 system.h 追加 `namespace std { using ::fancy_abort; }` 桥接，宏重写后仍可编译 |
| 8 | 加载 libgccjit.so 即崩溃（NULL 函数指针调用，PC 落在 jit-builtins.cc 的 `builtin_data` 数组） | `gcc_target targetm` 含非 constexpr 的 `array_slice` 成员（attribute_table），clang 下 `targetm` 落入 `.bss` 经 `.init_array` 动态初始化；`jit-builtins.cc` 的 `builtin_data` 动态初始化（idx 4）先于 `targetm`（idx >20）执行，期间调用尚未初始化的 `targetm.libc_has_function()` → 空指针 | prepare 脚本第 3 步把 `gcc/vec.h` 的 `array_slice` 全部 8 个构造函数改为 `constexpr`，`targetm` 恢复静态初始化（`.data` + 1459 重定位），崩溃消除 |
| 9 | CI L1 `conan create` 失败：`configure: fork: Out of memory`，`C compiler cannot create executables`（exit 77） | CI worker 多包并行构建、机器无 swap，configure 大进程 fork clang 测试编译时 ENOMEM；L0k 通过后首次进入真实构建即在此崩 | `_run_with_unlimited_stack` 增加通用重试：任一非零退出（fork OOM 类）sync + sleep 30s 后重试一次（make 增量续跑 / configure 重新生成 / install 幂等，代价低）；signal-11 专属重试保留 |

## 源码修改

- `files/prepare_ohos_sources.py` + `files/ohos.h`：从 gcc/9.5.0 配方继承的
  通用 OHOS 转换（config.sub 注入 aarch64-linux-ohos、umask 077→022、
  config.gcc 四处 musl/ohos 匹配）。已核对 GCC 16.1.0 的 config.gcc：
  四处替换点文本全部匹配，脚本无需改动。
- `files/prepare_ohos_sources.py` **第 3 步（新增）**：`gcc/vec.h` 的
  `array_slice` 8 个构造函数全部加 `constexpr`（修问题 #8）。脚本内置
  原文匹配校验：若 GCC 16.1.0 vec.h 文本不匹配则直接报错，不会静默跳过。
  - 验证：patch 对原始 vec.h 精确匹配（`vec_old in vec_content` 为 True），
    应用后 `constexpr array_slice` 计数 = 8；修改后的 vec.h 重编
    aarch64.cc（-O2）→ `targetm` 落入 `.data`（静态初始化，1459 重定位），
    `.init_array` 的动态初始化器从 ~600 字节缩至 92 字节（仅 std::string
    析构注册）。

## 依赖版本

- gmp 6.3.0（in-tree，官方 download_prerequisites）
- mpfr 4.2.2（in-tree）
- mpc 1.3.1（in-tree）
- 宿主：OHOS SDK clang/clang++（aarch64，musl ABI）

## 验证结果

```bash
# build() 内：GCC 自带 selftest + gcc.c-torture/execute 全量（1812 源 × -O0/-O2 = 3624 次执行，镜像 execute.exp/builtins.exp/ieee.exp）
make -C gcc selftest

# test_package：真实 JIT 全链路（编译 C 函数 → 生成可执行机器码 → 调用 → 校验结果）
clang -I<pkg>/include -L<pkg>/lib -lgccjit test_jit.c -o jit_test_program
./jit_test_program   # 期望输出: libgccjit-jit-ohos-ok
```

## 知识积累

- ✅ E007: config.guess 无法识别 HarmonyOS，aarch64-linux-ohos 必须映射到 GCC 的 musl target 配置
- ✅ E053: OHOS 无 cc1plus，GCC 16.1.0 全程用 OHOS SDK clang/clang++ 做宿主编译器
- ✅ E077: GCC 宿主生成器与输出程序必须做 HarmonyOS ELF 签名，否则加载报 EPERM
- ✅ E045: libgccjit 用 mprotect RWX 物化 JIT 机器码，2026-04 W^X 放宽后可用（Cling 同轴）
- ✅ E176: CONFIG_SHELL 不会替换初始解释器，须显式以 Bash 启动并在 ulimit -s unlimited 后执行
- ✅ E016: OpenDesk 导出 AS=llvm-as，GCC 需要 GNU as/ld（/data/service/hnp/bin 为 GNU Binutils 2.45）
- ✅ E127: 设备无 /usr/include，GCC sysroot 从 OHOS SDK Clang 的 native/sysroot/usr/include 推导
- ✅ E138: GMP 6.3.0 / MPFR 4.2.2 / MPC 1.3.1 按 GCC 16.1.0 download_prerequisites 官方 in-tree 版本
- ✅ 新发现: OHOS 仅提供 libc++（无 libstdc++），GCC JIT 代码的 `std::_Hash_bytes` 需替换为可移植 FNV-1a；libc++ 头文件直接调用 `std::abort()`，需 `namespace std { using ::fancy_abort; }` 桥接 system.h 的 abort 宏
- ✅ 新发现: clang 下 `gcc_target targetm` 的 `array_slice` 成员（非 constexpr 构造）会把整个 `targetm` 拖入 `.bss` 动态初始化；`.init_array` 中其它翻译单元（jit-builtins.cc 的 `builtin_data`）先执行并调用 `targetm.libc_has_function()` → NULL 崩溃。`array_slice` 构造函数加 `constexpr` 即可恢复静态初始化（该修复对上游无害，可回馈 GCC）

## 高难度挑战说明（路径 C 判定项，对标 Cling 判例）

该任务命中路径 C 的以下判定项：

- **工具链级依赖图**：需构建完整 GCC 16.1.0 工具链（C + JIT 前端），
  宿主全程 clang（OHOS 无 cc1plus，E053）。
- **JIT/可执行内存 × W^X·SELinux**：libgccjit 在进程内 mprotect RWX 生成并
  执行机器码，是 OHOS W^X/SELinux 对抗的核心验证轴（E045/E134，与 Cling 同轴）。
- **禁止系统接口/架构缺口**：OHOS 无 pthread_cancel → `--disable-threads`；
  无 /usr/include → sysroot 推导；ld-musl-aarch64.so.1 ABI。
- **bootstrap 依赖链**：`--disable-bootstrap`，宿主生成器保持 PIE 规避 LLD
  copy-relocation 对齐失败。
- **真机全链路验证**：selftest + torture 全量 + JIT 消费者程序在 OHOS 真机执行。

## 注意事项

- 评审可能质疑「libgccjit 只是 GCC 一个库，算单库适配」（protobuf 负面判例）：
  对策是突出**宿主编译器 bootstrap（E053）+ JIT 运行时（E045）两条轴**，两者
  都是路径 C 的工具链级/架构级适配，非单库可及。
- `--enable-host-shared` 会让整个编译器编译为 PIC，构建时间/内存明显高于
  普通 GCC；串行 make + 300s 超时需在 CI 侧注意。
