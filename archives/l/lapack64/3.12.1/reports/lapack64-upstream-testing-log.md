# lapack64 3.12.1 上游测试真机运行证据（逐字转写）

- 运行环境：HarmonyOS PC 设备原生（os=OHOS，aarch64/armv8），上游 make 全路径构建（BLAS/SRC → INSTALL 探针 → SRC → testing/MATGEN → testing/LIN → testing/EIG），make.inc 与配方同语义：`flang -fdefault-integer-8`（ILP64）、TIMER=NONE、dlamch.o `-O0`。
- 驱动签名：`/data/service/hnp/bin/binary-sign-tool sign -inFile X -outFile X -selfSign 1`（20 个驱动，含 DMD 备用）。
- 运行命令（官方 runner，LAPACK 3.12.1 源码自带）：

```
E=$HOME/ws/tmp/lapack64-3.12.1/exploration
mkdir -p $E/run/TESTING && cp $E/lapack-3.12.1/testing/*.in $E/run/TESTING/
cd $E/run && python3 $E/lapack-3.12.1/lapack_testing.py -r -b $E/lapack-3.12.1/bin
# RUNNER_EXIT=0
```

> 布局说明：runner 固定 `os.chdir('TESTING')` 并以 `-b <bin>` 定位驱动；设备工作区
> （HMDFS）大小写不敏感，源码树内已有小写 `testing/` 目录，故 TESTING/ 建在独立
> run/ 目录（无同名冲突），输入文件复制其中，驱动经绝对路径 bin 引用。

## 汇总表（官方 runner 输出逐字）

```
			-->   LAPACK TESTING SUMMARY  <--
SUMMARY             	nb test run 	numerical error   	other error
================   	===========	=================	================
REAL             	1569648		0	(0.000%)	0	(0.000%)
DOUBLE PRECISION	1570470		0	(0.000%)	0	(0.000%)
COMPLEX          	980455		0	(0.000%)	0	(0.000%)
COMPLEX16         	1030797		0	(0.000%)	0	(0.000%)

--> ALL PRECISIONS	5151370		0	(0.000%)	0	(0.000%)
```

- 结论：**N = 5,151,370 项测试全量运行，数值错误 0、其他错误 0（通过率 5151370/5151370，100%）**。覆盖 14 驱动 × 74 次运行（消耗 47 个不同输入文件；上游 .in 清单共 67 个，glm/nep 等跨精度共用、bak/bal/dmd 等 20 个不在默认全量内）：xlintst{s,d,c,z}（LIN）、xlintstds/xlintstzc（混合精度 proto）、xlintstrf{s,d,c,z}（RFP）、xeigtst{s,d,c,z}（EIG）。
- 运行日志含 74 条逐类别 "passed:" 行，无 FAILED/WARNING 条目。

## 原件索引（本文件为逐字转写，非原件）

| 原件 | 设备路径（$E=~/ws/tmp/lapack64-3.12.1/exploration） | SHA-256 | 字节/行数 |
| --- | --- | --- | --- |
| runner 全日志 | $E/runner-all.log | 97662bff5a41d5693893b45fe0f253bbbe02fd122698026a51375fe4cfa7eed4 | 8642 B / 175 行 |
| 74 个 .out 哈希清单 | $E/run/out-hashes.txt | 27a202086ac2638a0dbf6e77a7702b1a683259c64bfdb497a8e98ea861990cef | 74 条；.out 合计 126,273 B |
| dlamch 探针输出 | $E/lapack-3.12.1/testdlamch.out | 50c64d053dba131786e54a33a343370839448200f8dccc9865eb3cfd71a39a34 | IEEE 双精度机器常数（Epsilon=1.11e-16、Precision=2.22e-16） |
| BLAS 构建日志 | $E/lapack-3.12.1/build-blas.log | d59ceaeb002d57c1179f7f3b2c4e00fba0189247ea3134c03c6d75541e63b546 | — |
| SRC 构建日志 | $E/lapack-3.12.1/build-src.log | 21dec7ff905f885d3f823261b0490a297e289b94a92577a2e23ecb29b8907a13 | — |
| MATGEN/LIN/EIG 构建日志 | build-matgen.log / build-lin.log / build-eig.log | cc533854d0d81f492fc4f8ea376d73ccd2eec61c5c38ae641f0513b690b3e946 / e92b02298789de1ddae7e9f6a6a60d6e34c312501b0de15602e45a6a99e94203 / 9201f1a804ea392c9c3e49613ed841eca2b7714fb300349790a890cd17463bb2 | — |
| INSTALL 探针构建日志 | build-install.log | a72f0ab40747bf3dd9b5a9aa3e8345cef18104b56bf7fe2d160755845856819c | — |

- 源码包：Reference-LAPACK v3.12.1 官方 tarball，SHA-256 `2ca6407a001a474d4d4d35f3a61550156050c48016d949f0da0529c0aa052422`（与 conandata.yml 一致）。
