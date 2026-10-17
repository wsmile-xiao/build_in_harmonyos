# xbyak_aarch64 1.1.3 适配笔记（HarmonyOS PC / aarch64）

## 一、概述

xbyak_aarch64 是 Fujitsu 的 C++ **JIT 汇编器**：在运行期把 AArch64 / NEON / SVE
指令编码进可执行内存，刷新指令缓存后直接调用。交付物为静态库
`lib/libxbyak_aarch64.a` 与头文件目录 `xbyak_aarch64/`。

- 上游：https://github.com/fujitsu/xbyak_aarch64
- tag：`v1.1.3`
- tarball SHA256：`dd65de6fb34fb3d4c74a924d739500d6bd53587c7b3db3e6524a794b9492307a`
- 许可证：Apache-2.0

## 二、路径 C 证据（源码 / 构建 / 测试配置）

### 2.1 运行期代码生成 + 可执行内存 + 指令缓存刷新

`Xbyak::CodeGenerator` 在堆/`mmap` 出来的缓冲区里写入机器码，`ready()` 之后
`getCode<T>()` 返回函数指针直接调用。测试与 sample 都是这个模式
（`sample/add.cpp`：`add(w0,w1,w0); ret();` 然后调用）。

### 2.2 上游测试不是字符串比对

`test/test_all.sh`（上游 CI `.github/actions/test_action/entrypoint.sh` 实际执行
`./test_all.sh -q`）逐个助记符做**三重验证**：

```sh
${AS} -march=${AARCH64_TYPE} -mcpu=all -acdnl=a.lst a.asm   # GNU as 参考编码
cat a.lst | ... | awk '{print substr($3,7,2) substr($3,5,2) ...}' > ok.lst
${EMULATOR} ./${TEST_FILE} jit > nm.cpp                     # xbyak 生成助记符源码
${CXX} ... -o nm_frame nm_frame.cpp ../lib/libxbyak_aarch64.a
${EMULATOR} ./nm_frame > x.lst                              # xbyak JIT 编码
diff -w x.lst ok.lst                                         # 逐条编码比对
```

即：**每条指令的机器码都要与 GNU 汇编器的输出逐字节一致**。

### 2.3 鸿蒙上的可行性实测

| 需求 | 鸿蒙 PC 实况 |
|---|---|
| GNU `as` 且支持 `-acdnl=` | ✅ `/data/service/hnp/bin/as` = **GNU assembler (GNU Binutils) 2.45**，实测 `-acdnl=` 产出格式完全匹配 |
| `objdump` | ✅ `/data/service/hnp/bin/objdump` |
| 模拟器 | **不需要** —— 原生 aarch64，`setenv-qemu` 只在非 aarch64 主机上设 `EMULATOR=qemu-aarch64` |
| `g++` | ❌ 设备无 g++；测试脚本硬编码 `CXX=g++`，用 PATH 前置 `g++ -> clang++` 包装脚本解决 |
| `awk` / `sed` | ✅ |

## 三、上游测试统计

| 测试类型 | 上游用例数 | 统计命令 | 环境要求 | OpenHarmony 可执行性 |
|---|---:|---|---|---|
| 编码测试（test/，nm 系列） | **8** | `grep -oE "nm_list=\"[^\"]*\"" test/test_all.sh` | GNU as + C++ 编译器 | ✅ **真机 8/8 通过** |
| 集成测试（test/，integrated 系列） | **3** | 同上 `integrated_list=` | 同上 | ✅ **真机 3/3 通过** |
| 指令模式测试（test2/） | **15** | `grep -oE 'PTN="[^"]*"' test2/test_all.sh` | 同上 | ✅ **真机 15/15 通过（见 §3.1）** |
| **合计** | **26** | | | **26 可执行，0 未执行** |

**本包的上游测试统计口径**：

| 指标 | 数值 |
|---|---:|
| 上游发现总数 N | 26（test/ 11 + test2/ 15） |
| 当前架构适用数 A | 26 |
| OpenHarmony 实际执行数 E | 26 |
| 通过数 P | 26 |
| 失败数 F | 0 |
| 未执行数 A−E | 0 |
| 执行覆盖率 E/A | **26/26 = 100%** |
| 已执行通过率 P/E | **26/26 = 100%** |

### 3.1 `test2/` 的 15 个指令模式场景（真机实测）

上游 `test2/test_all.sh` 的 `PTN` 列表逐个执行
`./test.sh test_ptn_cpp/instructions_<PTN>.cpp`，每个场景做一次
**GNU as 参考编码 vs xbyak JIT 编码**的逐行比对。

运行方式（`test.sh` 内硬编码 `AS=aarch64-linux-gnu-as`、`CXX=g++`，
用 PATH 前置的符号链接适配到设备工具链）：

```bash
cd test2
export PATH=<shim>:$PATH     # aarch64-linux-gnu-as -> /data/service/hnp/bin/as
                             # g++                    -> /data/service/hnp/bin/clang++
for i in a b c f e l m n p r s t u w x; do
    bash ./test.sh test_ptn_cpp/instructions_$i.cpp
done
```

| PTN | 比对编码条数 | diff 差异 | 退出码 | PTN | 比对编码条数 | diff 差异 | 退出码 |
|---|---:|---:|---:|---|---:|---:|---:|
| a | 504 | 0 | 0 | r | 426 | 0 | 0 |
| b | 630 | 0 | 0 | s | 8324 | 0 | 0 |
| c | 784 | 0 | 0 | t | 310 | 0 | 0 |
| e | 216 | 0 | 0 | u | 4105 | 0 | 0 |
| f | 1535 | 0 | 0 | w | 1528 | 0 | 0 |
| l | 2799 | 0 | 0 | x | 76 | 0 | 0 |
| m | 326 | 0 | 0 | | | | |
| n | 74 | 0 | 0 | | | | |
| p | 168 | 0 | 0 | | | | |

**合计 21805 条指令编码，0 条差异，15/15 场景退出码 0。**

> 判据说明：`test.sh` 末行是 `diff -y ${DUMP_FILE} ${EXP_FILE} > ${RESULT_FILE}`，
> 因此**脚本退出码即 diff 的退出码**；`diff -y` 会并排打印所有行（相同行也打印），
> 所以「行数等于输入」是正常现象，真正的判据是**输出的差异标记数为 0**。
> 两处独立证据一致：退出码 0，且 `grep -c "|" result` 全为 0，
> 且 `exp`/`dump` 行数相等且非空（`n` 场景 74 行为例，首行 `04E83D08` 与
> GNU as 输出逐字节相同）。
> 原始日志：`path-c-evidence-20260929/xbyak-aarch64/test2-run/SUMMARY.txt` 及
> `logs/ptn_*.log`（15 个），逐场景 `tmp.instructions_*.result` 全为 0 差异。

- `test/test_all.sh` 的 `nm_list`（8）：`make_nm`、`make_nm_branch`、`make_nm_fp`、
  `make_nm_load_store`、`make_nm_simd`、`make_nm_simd_fp_load_store`、`make_nm_sve`、
  `make_nm_sve_addr`
- `integrated_list`（3）：`mov`、`mov_imm`、`add_sub_adds_subs_imm`
- `test2/test_all.sh` 的 `PTN`（15）：`a b c f e l m n p r s t u w x`

**每个场景内部包含数以千计的指令编码**，例如 `make_nm_sve` 生成的 `nm.cpp` 达
**1.65 MB**，逐个与 `as` 的输出比对。

## 四、适配修改（补丁 `patches/0001-ohos-portability.patch`，9 文件 / 25 行）

| # | 位置 | 现象 | 处置 |
|---|---|---|---|
| 1 | `src/util_impl_linux.h:388-391` | glibc 私有 `sysconf(_SC_LEVEL1_ICACHE_SIZE/_SC_LEVEL1_DCACHE_SIZE/_SC_LEVEL2_CACHE_SIZE/_SC_LEVEL3_CACHE_SIZE)`，musl 未声明 → 编译失败 | 用 `#if defined(...)` 保护该回退块；libc 未提供时保留上游注释已声明的默认（假定 L1+L2）并把 size 置 0。**主路径不受影响**：`cacheInfoDict` 查表与 sysfs 设备遍历保持原样 |
| 2 | `test/make_nm*.cpp`（8 个文件） | `uint jj;` —— `uint` 是 glibc `sys/types.h` 的 typedef | 改为**等价**的 `unsigned int jj;`。`uint` 即 `unsigned int`，**测试逻辑、断言、期望值一字未改** |

**未做的事**：没有删除任何测试、没有放宽任何断言、没有跳过任何场景、没有把失败改成通过。
`test/` 的 11 个与 `test2/` 的 15 个场景**全部在鸿蒙真机上执行**（§3、§3.1），
合计 26/26 通过，没有任何场景被跳过或降级。

## 五、test_package（消费者测试，单独统计，不计入上游 N）

- **第 1 层 `ohos_abi_check.py`**（纯 Python，任意宿主）：AArch64 ELF 目标文件、
  公共头文件齐备、编译器实现符号（`CodeGenerator` / `Xbyak`）确实在归档内、
  无 Mach-O/PE 泄漏。
- **第 2 层 `test_xbyak.cpp`**（仅 `can_run()`）——**在鸿蒙真机上验证 JIT 全链路**：
  - T1：运行期生成 `add w0,w0,w1`，`ready()` + `getCode()` 后调用，返回 42
  - T4a：校验生成的编码字确为 `0x0B010000`
  - T2：运行期生成 `cmp` + `csel`，验证取较大值
  - T3：运行期生成 NEON `add v0.4s,v0.4s,v1.4s`，验证 4×int32 向量加结果
  - T5：运行期生成较长序列 `mul` + `lsl`，验证返回 84

## 六、构建产物

| 文件 | 说明 |
|---|---|
| `lib/libxbyak_aarch64.a` | 静态库（8.7 MB） |
| `include/xbyak_aarch64/*.h` | 公共头文件 |

## 七、风险与边界

- **`test2/` 需要 PATH 上的两个 shim**：`test.sh` 硬编码
  `AS=aarch64-linux-gnu-as`、`CXX=g++`，设备上分别是 `/data/service/hnp/bin/as`
  与 `clang++` 的符号链接。这是**运行环境适配**，未改动 `test.sh` 本身，也未改动
  任何断言；上游在 aarch64 Linux 上借助同名交叉工具即可直接运行同一脚本。
- **补丁 1 的行为边界**：在 musl 上 `getCacheSize()` 的 L1–L3 容量将返回 0。
  上游注释本身承认 sysconf 路径“不总是返回正确值”，且 `test/`、`test2/`、
  `sample/` 均未调用该 API，故不影响交付范围与测试结论。
- **SVE 测试耗时**：`make_nm_sve` 生成的 C++ 文件由 clang 编译需十余分钟
  （单文件 1.65 MB），属正常现象而非卡死。
