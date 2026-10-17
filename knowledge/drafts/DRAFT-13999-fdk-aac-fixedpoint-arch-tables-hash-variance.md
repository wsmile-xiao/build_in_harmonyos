# 定点编解码库码流跨架构非位元一致:官方哈希 ref 测试必须按架构分流

- **草稿 ID**: DRAFT-13999-fdk-aac-fixedpoint-arch-tables-hash-variance
- **来源**: fdk-aac 2.0.3 HarmonyOS PC 适配(真机 aarch64 与 MinGW x86_64 双端跑官方 test-encode-decode 全模式矩阵对照)
- **分类**: testing / fixed-point / audio-codec / cross-arch / determinism
- **状态**: 本地草稿(路径 B 知识库扩展申请中)

## 问题 / 错误签名

- **哈希分叉但质量门禁全过**:鸿蒙真机 aarch64 跑官方 `test-encode-decode` 全模式矩阵(mono 11 模式 / stereo 25 模式,AAC-LC/HE-AAC/HE-AACv2/AAC-LD/AAC-ELD + VBR 变体)退出码 0、**0 failures**,但输出哈希与官方 `ref-stereo.txt`/`ref-mono.txt` 不同;同一 tarball、同一工具在 MinGW x86_64 上哈希与 ref 逐字节一致。
- **诱因假设错误**:默认"定点构建 ⇒ 跨平台位元一致"会把真机哈希差异误判为适配缺陷或编译器问题,浪费排查时间,甚至诱导出修改上游系数表的错误"修复"。

## 根因

1. **上游按架构选择定点系数表位宽**:`FDK_archdef.h:117` 把 `__aarch64__` 统一映射为 `__arm__`,ARMv8 路径选择 `ARCH_PREFER_MULT_32x16`(32x16 定点乘法)与 `SINETABLE_16BIT`/`POW2COEFF_16BIT`/`LDCOEFF_16BIT` 等 **16-bit 系数表**;x86 走 32-bit 表。
2. **心理声学模型全程定点,但表精度按架构变**:编码器用 `FIXP_DBL` 定点常量计算,系数表位宽差异直接进入码流 → 码流跨架构**设计上非位元一致**,这是上游刻意的精度/性能权衡,不是构建问题。
3. **官方 ref 的单架构属性**:官方 `test/ref-stereo.txt`、`test/ref-mono.txt` 生成于 x86,天然只对 x86 成立;其他架构直接 `diff` 必挂,官方 `run-test.sh` 同样只在其生成环境可位元复现。

## 最小修复方案

测试入口(如 test_package/test.sh)对官方套件哈希比对按 `uname -m` 分流:

- **x86(含 i686/i386)**:严格 `diff` 官方 ref——本架构下位元一致是强断言,保留它。
- **其他架构(aarch64 真机等)**:以上游工具自身质量门禁为准——退出码 0(各模式解码 avg_diff 全部落在上游阈值内,上游以 failures 计数退出)+ 哈希行形状正则(`^encode hash: [0-9a-f]{40}$`)校验,并打印 NOTE 说明差异源于架构定点表位宽,防止被误读为缺陷。

```sh
if ! diff -u log-stereo.txt "$SRC_DIR/upstream-test/ref-stereo.txt"; then
    if [ "$(uname -m)" = "x86_64" ] || [ "$(uname -m)" = "i686" ] || [ "$(uname -m)" = "i386" ]; then
        echo "FAIL: stereo hash diff vs official ref (x86 须位元一致)"; exit 1
    else
        echo "NOTE: $(uname -m) 哈希与 x86 官方 ref 不同(上游定点表位宽平台差异),以上游工具质量门禁为准"
        grep -q '^encode hash: [0-9a-f]\{40\}$' log-stereo.txt || exit 1
    fi
fi
```

配套:确定自身测试输入时禁用 libm——`math.sin` 跨实现非位元一致(musl vs MSVCRT),合成 wav/PCM 改用**编译期整数正弦表 + 整数 LCG**,保证同架构跨工具链可复现,把"架构差异"与"libm 差异"两类变量分离。

## 验证结果

| 环境 | 结果 |
|------|------|
| MinGW x86_64(本地) | probe 18/18;官方双 wav 哈希与 ref-stereo.txt/ref-mono.txt 逐字节一致(x86 位元性实证) |
| HarmonyOS PC aarch64 真机 · Conan 2.29.1 + clang 15 · ohos-aarch64 | conan-verify 八门禁 G0-G4 + L2/L4/L5 全绿;probe 18/18;官方双 wav 全模式矩阵 0 failures(上游质量门禁),哈希 stereo 18bca4c9…/8b75d6c8…、mono e4cdfdcf…/cb13f43b…,与 x86 ref 差异经 archdef 根因确认 |
| 识别法 | `grep -n "SINETABLE_16BIT\|POW2COEFF_16BIT" libSYS/include/FDK_archdef.h` 确认架构表位宽宏 |

## 禁止策略

- 禁止对任何架构无条件 `diff` 官方 ref——真机必挂,把上游设计行为误判为适配缺陷。
- 禁止 patch `FDK_archdef.h` 强制统一系数表位宽——改变编解码输出,与上游各平台官方二进制不互操作,且不可向上游提交(P005)。
- 禁止删除/跳过官方哈希套件——avg_diff 门禁是真机上唯一权威的行为级验证,删除即删质量证据。

## 相关

- 原则:P005(补丁必须可向上游提交,约束"统一系数表位宽"类伪修复)
- 同类议题:libm 跨实现非位元一致(math.sin 在 musl/MSVCRT 间不保证同值)——确定性测试输入应使用编译期整数表而非 libm 函数。
