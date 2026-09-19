# OHOS 真机上 SHF_MERGE 常量段运行时移位，PC 相对寻址取到错位常量

- **草稿 ID**: DRAFT-libisal-2.31.1-shf-merge-rodata-runtime-displacement
- **来源**: libisal 2.31.1 HarmonyOS PC 适配（frp 真机 make check 904 用例失败 → 运行时内存扫描定位 → 一行补丁修复）
- **分类**: platform / ohos / linker / rodata / simd / assembly / runtime
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **严重级**: 1（静默数据错误，无崩溃无告警）

## 问题 / 错误签名

- 上游 `checksum32_funcs_test` 在 OHOS 真机失败 904 用例：`fail checksum rand N = 0xXXXX 0xYYYY`，且**低 16 位（A 和）完全正确、高 16 位（B 和）错误**。
- 同一函数同一输入，直调与经 multibinary 分派调用给出**不同的错误值**；不同链接布局的二进制错误值也不同（delta 只依赖数据内容）。
- 静态分析完全自洽：指令逐条反汇编与源码一致、常量表字节在 .o 与链接后二进制中均正确、adrp/adr 目标地址与静态 VMA 精确吻合。

## 根因

1. 汇编内核把 SIMD 常量表放在 **SHF_MERGE 段**（`.section .rodata.cst16,"aM",@progbits,16`），如 libisal adler32 NEON 的 32..1 权重表。
2. 在两台 OHOS PC 真机上（GNU as 2.45 与 clang 集成汇编器产物均复现），该类段在**进程运行时相对静态布局移位**：运行时扫描发现 32 字节常量模式出现两份拷贝（相距 0x1000），真实表位置与链接期 VMA 不符。
3. `adrp+add` / 链接器松弛后的 `adr` 按静态布局计算地址，加载到**错位 0x18 字节**的"常量"，SIMD 内核用错误权重继续运算——不崩溃、只出错值。
4. C 编译的大数组 `.rodata`（如 CRC 查表）实测**不受影响**（libisal crc 系测试全过），问题集中在手写汇编的 merge 小常量段。

## ⚠ 诊断陷阱（本条最有价值的教训）

最初症状酷似"UMLAL2 指令在 OHOS 上是 no-op"：volatile 防折叠的 NEON intrinsics 微测试显示 umlal2 加载累加毫无效果。**这是假象**——微测试的静态初始化数组同样被 clang 放进 merge 段，umull2 的操作数本身就是错位加载来的（恰为全零），加零当然"看不出效果"。逐寄存器裸汇编 dump（固定输入、每步 st1 落盘）证明所有 SIMD 指令行为正确，才把嫌疑收敛到数据加载。

**通用诊断法**：测试程序打印函数运行时地址 → 向前扫描已知常量字节模式 → 命中偏移与 `objdump -d` 中 adr/adrp 静态目标偏移对比，不一致即为本条。

## 最小修复

```diff
-	.section	.rodata.cst16,"aM",@progbits,16
+	.section	.rodata,"a",@progbits
```

补丁 `0001-igzip-adler32-neon-drop-merge-section-flag.patch`（单行）。对健康平台零行为差异（仅放弃链接器常量去重合并）。修复后 frp 真机 make check **16/16 全绿**（此前 adler 相关全挂）。

## 影响面与推广

- 任何手写 aarch64 SIMD 汇编 + merge 段常量 + PC 相对寻址的库（isa-l_crypto 系列高度可疑——其 BUILD_TESTS=OFF 从未在真机跑过数值断言）。
- 避坑：SIMD 内核适配必须跑**数值断言**的功能测试；"编译通过 + 冒烟不崩"完全不够。
- 备选修法：小常量（≤64B）可在汇编内 movz/movk+ins 寄存器构造，彻底消除数据段引用。
