# isa-l 2.32.1 适配笔记（HarmonyOS PC, aarch64）

- 申请人：momimgya；队伍：干
- 上游：https://github.com/intel/isa-l，tag v2.32.1（2026-07-01）
- 源码包：https://github.com/intel/isa-l/archive/refs/tags/v2.32.1.tar.gz
  - 实测 842741 字节（与 Gentoo DIST 记录一致），
    sha256=d9f7179ab0e14a3db9b610fac22793854a1435e8423ec9ce07f4cbedc5f92f5e
- License：BSD-3-Clause（上游 LICENSE 为 Intel BSD 模板）
- 构建系统：custom（直接编译；源集/宏/头路径与上游 cmake/*.cmake 的
  CPU_AARCH64 分支精确等价，但不执行 CMake project()，见下）。
- 依赖：无（纯计算库，无第三方运行时依赖）。
- 适配路径：路径 A（基础适配）。

## 上游源码审计

- tag 包内含完整 CMake 构建（顶层 CMakeLists.txt + cmake/*.cmake），
  按 CMAKE_SYSTEM_PROCESSOR 选择 CPU 分支：aarch64/arm64 → CPU_AARCH64，
  取 `crc/aarch64`、`erasure_code/aarch64`、`raid/aarch64`、
  `igzip/aarch64` 等目录的 `.S` 汇编（由 CMAKE_C_COMPILER 预处理，
  `-D__ASSEMBLY__`），x86_64 以外不需要 NASM。
- aarch64 运行时多版本派发用 getauxval(AT_HWCAP)（<sys/auxv.h>），musl/OHOS
  提供该接口；缺失的 HWCAP_* 宏上游自带 fallback 定义。
- 公共头：crc.h、crc64.h、erasure_code.h、gf_vect_mul.h、igzip_lib.h、raid.h、
  mem_routines.h、isal_api.h + 构建时生成的 isa-l.h（umbrella，由
  cmake/isa-l.h.in 经版本替换生成，本配方在 build() 内同法生成）；
  安装布局为 include/isa-l.h + include/isa-l/*.h，库为 libisal
 （pkg-config 名 libisal）。
- 构建系统选型（两轮真机失败后的结论）：
  1. 首轮 autotools（autoreconf 现场生成 configure）：卡在构建
     tool_requires 的 m4/1.4.19，
     `src/configure[139]: /data/service/hnp/bin/bash: inaccessible or
     not found`（profile 把 SHELL/CONFIG_SHELL 钉死到该路径，而该 runner
     上缺失），伴随 /tmp 只读。m4 系第三方配方，无法在本包内改写其 SHELL。
  2. 次轮 CMake：仍失败于 `CMakeLists.txt:30 (project)`，
     `The CMAKE_C_COMPILER: /data/service/hnp/bin/clang`，
     `The C compiler identification is unknown`——同一类钉死路径问题，
     只是从 bash 换成了 clang。
  3. 本轮改用直接编译（libe57format/3.3.0 先例）：完全不执行 CMake
     project()，用经 `--version` 探针验证可用的编译器，按
     cmake/*.cmake 的 AArch64 源集（含 igzip 的 proc_heap_base.c 回退、
     非 AArch64 时走 CPU_UNDEFINED 的 base-aliases 源集）逐文件编译，
     保持 `-Daarch64`、库私有 `-DISAL_DEPRECATED_INTERNAL`、
     `-Iinclude -I.`（igzip 测试另加 `-Iigzip`）、`.S` 文件
     `-D__ASSEMBLY__` 等价，现场生成 isa-l.h 并安装。
   唯一例外：erasure_code/aarch64/gf_nvect_dot_prod_sve.c 含
   <arm_sve.h>（clang 守卫要求编译器 SVE 特性宏），按
   erasure_code/aarch64/Makefile.am 的 -O3 意图，以
   `-O3 -march=armv8-a+sve` 单独编译该 TU；其函数全带
   target("+sve") 属性且仅经 HWCAP 门控的派发器调用，非 SVE
   CPU 不受影响（与上游 aarch64 发行物一致）。
     这不是跳过测试：运行的是同一组 17 个 check 程序（见下）。

## 上游测试清点（与各 cmake/*.cmake 的 CHECK_TESTS/add_test 注册集一致，共 17 个程序）

| 模块 | 程序 | 说明 |
|------|------|------|
| erasure_code | gf_vect_mul_test、erasure_code_test、gf_inverse_test、erasure_code_update_test | 4 |
| raid | xor_gen_test、pq_gen_test、xor_check_test、pq_check_test | 4 |
| crc | crc16_t10dif_test、crc16_t10dif_copy_test、crc64_funcs_test、crc32_funcs_test | 4 |
| igzip | igzip_rand_test、igzip_wrapper_hdr_test、checksum32_funcs_test | 3 |
| mem | mem_zero_detect_test | 1 |
| misc | version_test | 1 |
| 合计 | | 17 |

- 另有 *_base_test 等 unit_tests 与 perf 可执行文件在上游
  ISAL_BUILD_TESTS=ON 时会被编译但不经 add_test 注册，`ctest` 默认不跑；
  本配方只构建并运行上述 17 个 check 程序（测试 .c + libisal 链接，
  各自带 main，不链接额外 main 库）；fuzz/ 下为模糊测试驱动，不计入。
- 配方在 build() 内逐个运行 17 个二进制，以进程退出码判定通过/失败，
  计数做 fail-closed 校验（discovered=17、executed==discovered、无失败
  无跳过才判 passed），双通道输出 HMBS_UPSTREAM_TEST_RESULT 并落盘
  build_folder/hmbs_upstream.json，package() 再复制到 package res/
  供 test_package 复述。
- 证伪设计：以真实退出码判定，不是自报通过；二进制缺失/空文件直接抛错；
  解析器要求 discovered>0 且 executed==discovered。

## 配方关键决策

1. 默认静态（shared=False）：小众加速库，静态避免 OHOS loader 路径问题；
   test_package 直接链接 libisal.a，运行时零依赖（shared=True 时以
   `CC -shared` 链接 libisal.so，对象统一带 -fPIC）。
2. 编译器/归档器回退：钉死的绝对路径仅在通过 `--version` 运行探针后才用；
   否则按 basename 走 PATH 找可用编译器（优先同目录兄弟编译器），
   仅覆盖本次调用的 CC/AR，不碰 CFLAGS/LDFLAGS；两者皆无时抛明示环境错误。
   全部工具调用经 `self.run(..., env="conanbuild")`，继承 hmbs 注入的
   PATH 与可写 TMPDIR。
3. 构建前先做最小编译链接运行冒烟（可写临时目录内），探针失败即停。
4. 可写临时目录：TMPDIR/TMP/TEMP=可写目录 + SHELL=/bin/sh +
   CONFIG_SHELL=/bin/sh + umask 022（HMDFS 兼容）。
5. test_package 不用 CMake（device cmake 缺 HarmonyOS 平台文件，
   dcap/2.47.14 预检实证），直接 CC 编译；同样做 basename 归一化与
   `--version` 探针，编译经 `self.run(env="conanbuild")`；test() 保留显式
   self.run() 调用以满足 L0 门禁。
6. test.c 共 6 个断言，全部离线、确定性：
   - crc16_t10dif / crc32_ieee 用上游 crc_simple_test.c 的固定已知向量
    （0x60b3 / 0x2ceadbe3），非空文件比对，杜绝“空比空”式假通过；
   - CRC 分段拼接自洽；
   - isal_get_version() 精确等于 ISAL_MAKE_VERSION(2,32,1)；
   - 纠删码线性（全零输入→全零校验）+ 确定性（两次编码一致）+
     非退化（真实数据校验非全零，抓住返回全零的 stub）。

## 验证状态

- 2026-09-17 真机失败 `Failed to parse patch .../0001-sve-always-inline-clang.patch`
  （`extra lines for hunk no.1`）：手写补丁头声明 `+39,13`，实际新区 14 行
  （9 旧行 -2 删除 +7 新增 = 14），解析器在编译前直接拒绝。按第 3 策略周期
  要求改走不同路线：删除该补丁文件与 conandata patches 项，改为 build() 内
  `replace_in_file` 精确替换两个属性行（仅去 `always_inline`，保留
  `target("+sve"/"+sme")+inline`，语义与原补丁一致，免 hunk 计数/CRLF 风险）。
- 本轮：工作树已完成，未提交；等待 HMBS 真机预检（conan create +
  直接编译 17 项上游 check + test_package 6 断言）。
- 上游测试通过数、test_package 实测输出，以预检 evidence 回填到
  manifest.yaml 与 PR 正文，之前不填写任何猜测数字。
- 2026-09-17 聚焦轮：预检仍报 `always_inline function
  'gf_nvect_dot_prod_sve_unrolled' requires target feature '+sve', but would
  be inlined into function 'gf_vect_dot_prod_sve2' that is compiled without
  support for '+sve'`。根因为两点：① 通用 `_patch_once()` 以“新串已存在”
  判幂等，而本 TU 的 `target("+sve")` 包装器原文已存在 7 处，修复被误判
  “已应用”而跳过，helper 的 `always_inline` 原样残留；② 7 个 SVE2 包装器
  用 `target("+sve+sve2")` 拼写，真机 clang 不从该组合拼写授予 `+sve`，
  调用方实为无 SVE 编译，强制内联必然非法。修复改走不同路线：
  `_apply_sve_inline_fix()` 改为直接整文件替换（全量 occurrence，以旧串
  判幂等），去 `always_inline` 并将 `"+sve+sve2"/"+sme+sme2"` 收敛为纯
  `"+sve"/"+sme"`（SVE2 仅 EOR3 优化，位精确一致；HWCAP 派发守卫不变，
  17 项测试全部保留）。工作树未提交，待 HMBS 真机复检验证。

## 本轮真机诊断（2026-09-17，14/17，失败：pq_check_test、igzip_rand_test、checksum32_funcs_test）

- 证据：`fail end test - offset: 0, len: 1024`；`error: incorrect zlib trailer found when inflating data`；
  `fail checksum rand 13 = 0xba88733e 0xb7cd733e`、`checksum32_adler Failed 904 tests`。
  其余 14 项（含全部 erasure_code/crc/mem/version、xor_gen/pq_gen/xor_check）通过，说明工具链与整体分发机制可用，
  且测试确在执行（非空比空；exit 码门禁有效）。
- 根因 A（pq_check_test）：`raid/raid_base.c` 的 `pq_gen_base` 用
  `#if __WORDSIZE == 64 || _WIN64 || __x86_64__` 选择 64 位字掩码；musl（OHOS）不提供 `__WORDSIZE`，
  LP64 aarch64 上误入 32 位掩码分支（`unsigned long` 实为 64 位），Q 校验生成错误。
  本用例中 ref/neon 交叉检查均通过，只有唯一使用 `pq_gen_base` 生成、`pq_check`（neon）校验的 end-test 失败，
  与该根因精确吻合。`ec_base.c` 的同名条件 fallback 为宽度无关的逐字节实现，不受影响，无需改动。
- 根因 B（checksum32 + igzip zlib trailer）：`isal_adler32` 的 neon 向量路径（长度≥32）在真机上与
  位精确 C 参考 `adler_ref` 系统性不一致（约 904 例；低 16 位一致而高 16 位分歧；<32B 标量路径一致），
  zlib trailer 失败为同一 adler 缺陷的下游症状（deflate/inflate neon 往返本身通过）。
  配方仅将 `isal_adler32` 在 `__OHOS__` 下收敛到已验证的 `adler32_base`，其余分发器不动，17 项测试全部保留运行。
- readonly_tmp 平台诊断：预检日志中 `/tmp/...Read-only` 出自 harness 自身 `preflight.sh` 的 mktemp，
  isa-l 测试均为内存计算、无临时文件；配方既有可写目录 helper（TMPDIR/TMP/TEMP 优先级解析 + 落盘探测 +
  generate/build 双域透传）已覆盖该能力，无需新增改动、不跳过任何测试。
- 修复：`conanfile.py` 新增幂等 `_apply_raid_wordsize_fix`（`__SIZEOF_LONG__==8` 兜底，glibc 行为不变）与
  `_apply_ohos_adler_fallback`（`__OHOS__` 早退到 `adler32_base`，Linux/Apple 不变），SVE 行内修复同步改为幂等；
  均走 in-recipe 精确替换、无补丁文件。工作树未提交，待 HMBS 真机复检验证。

## 已知限制

- igzip_rand_test 为随机数据往返测试，耗时随机器性能波动；
  若真机超时，将评估后在补充说明中如实记录。
- 2.32.1 的 zlib 兼容 shim 为实验性质，未纳入本配方验证范围。
