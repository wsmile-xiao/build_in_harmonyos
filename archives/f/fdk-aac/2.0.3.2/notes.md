# fdk-aac 2.0.3.2 鸿蒙 PC 适配笔记

## 任务背景

- 任务 13999:fdk-aac / C++ / 2.0.3 / 5 火种,2026-09-27 认领,10/04 19:41 释放。
- R37 铁律:2.0.3 已在官方 main 与制品仓,同赛道竞争者 MR #12445(2.0.3)、
  #12643(2.0.3.1, CI 通过)占位 → 本 MR 递增至 **2.0.3.2**,上游源码不动。

## 上游分析

- Fraunhofer FDK AAC 编解码库,官方 SourceForge 发行包
  fdk-aac-2.0.3.tar.gz,sha256 829b6b89…。cmake 原生构建,零 patch。
- 官方自带测试套件:`test-encode-decode` 工具 + `test/run-test.sh` +
  `test/ref-stereo.txt` / `ref-mono.txt`(字节级确定性验证):
  输入 wav → 按声道数跑全模式矩阵(mono 11 模式;stereo 25 模式,含
  AAC-LC / HE-AAC / HE-AACv2 / AAC-LD / AAC-ELD 及 VBR 变体)→ 所有模式
  编码/解码块累计进同一对全局 SHA-1 → 两行哈希与 ref 比对,退出码 =
  failures 数(各模式解码 avg_diff 超上游阈值即计 failure)。
- **跨架构位元一致性实证(真机)**:官方 ref 生成于 x86。MinGW x86_64
  本地跑官方 wav → 哈希与 ref 逐字节一致;鸿蒙真机 aarch64 跑同一套件
  → 全模式 0 failures(质量门禁全过)但哈希不同。根因:`FDK_archdef.h:117`
  把 `__aarch64__` 统一定义为 `__arm__`,进而选择
  `ARCH_PREFER_MULT_32x16` + `SINETABLE_16BIT`/`POW2COEFF_16BIT`/
  `LDCOEFF_16BIT` 等 16-bit 系数表——上游刻意按架构选不同精度定点表,
  码流跨架构**设计上非位元一致**,不是构建问题。测试策略见「测试设计」。
- `BUILD_PROGRAMS=ON` 时 test-encode-decode 只留在构建树、**不随 install
  安装** → 官方工具源文件 vendor 进 test_package 与消费者探针同批重编。

## 适配设计

| 项 | 决策 |
| --- | --- |
| 版本 | 2.0.3.2(R37 递增,见上) |
| patch | 零(上游 cmake 原生可构建) |
| 源 | SourceForge 官方 URL 直连(竞争者 CI #60899 同源通过) |
| 构建 | cmake;`BUILD_PROGRAMS=ON`;真机 ninja `--parallel 8`(进程配额) |
| 测试 | 消费者探针 18 断言(合成 PCM 编码往返 + SHA-1)+ 上游官方套件(官方 wav fixture 哈希比对按架构分流:x86 位元/其他架构上游质量门禁)+ 合成 wav 烟测兜底 |

## 消费者探针(fdk_aac_probe, 18 断言)

1. 编码器:确定性合成 PCM(441Hz 正弦表 + LCG 噪声,2s@44.1kHz mono,
   纯整数运算、与 libm 无关)→ AAC-LC/ADTS,逐帧喂入 + flush,镜像上游
   test-encode-decode.c 循环语义;
2. 解码器:ADTS 流 1024B 块 Fill + DecodeFrame 往返(镜像上游 decode());
3. 结构断言:frameLength=1024、帧数 ≥86、样本数闭合、能量非零、往返
   误差(max<6000 / mean<1000)、非法采样率被拒绝;
4. 聚合 SHA-1(与上游同口径)打印,便于跨平台位元比对(注:仅同架构内
   可比,跨架构差异见「上游分析」)。

## 真机验证(已完成, 2026-09-27)

- conan-verify 八门禁(G0-G4 + L2/L4/L5)全绿,无 EACCES,报告留档
  `reports/conan-verify-report.md`(可标记 status: published)。
- test_package 三阶段全跑:probe 18 断言全过;官方两个 wav fixture 置入
  后 phase 2 真机 aarch64 全模式矩阵 0 failures(上游质量门禁),哈希
  与 x86 ref 不同(架构定点表位宽差异,见「上游分析」,test.sh 已按架构
  分流);phase 3 合成 wav 烟测过。
- 构建日志与探针输出留档 reports/。
- 探针输入改为纯整数正弦表 + LCG 后复验(2026-09-27):
  - 本地 MinGW x86_64:18/18 断言,encode hash d0e71916…/decode hash
    56a94cc9…;官方双 wav 哈希仍与 ref 逐字节一致(x86 位元性不变)。
  - 真机 aarch64(2026-09-27 复验):18/18 断言;phase 2 按质量门禁分流
    全过(stereo/mono 均 0 failures + NOTE),哈希与首验一致
    (18bca4c9…/8b75d6c8…、e4cdfdcf…/cb13f43b…,确定性复现);
    phase 3 烟测过;日志 reports/device-test-full.log。
