# pari-galdata 20080411 — Test Report

- 日期: 2026-09-04
- 构建系统: data（纯数据包，无编译）
- 平台: noarch（`package_id` cleared；OHOS aarch64 profile 下创建验证）
- 结论: **PASS**（9/9 数据完整性断言，conan create 全绿）

## 1. 数据包性质与测试口径（R34 豁免说明）

pari-galdata 是 PARI/GP 的 Galois 群数据包：上游 tarball 只含
`data/galdata/` 数据文件（4 个 NAM 群名表 + 197 个 COS 陪集数据 +
143 个 RES 预解式数据，共 344 个），**无源码、无库、无头文件、无
可执行文件、无 API 可调用**（供 gp 的 `polgalois` 度 8..11 使用）。

因此常规 "test_package 编译 consumer 调用被测包 API" 的测试形态不适用
（先例：wireless-regdb/2026.05.30、mbrola-hu1/1.002、pari-elldata/
20210301 同口径），验证以**数据完整性**为准。

## 2. conan create 结果

```
$ conan create archives/p/pari-galdata/20080411 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing

pari-galdata/20080411: Calling build()          # source 模式验证
[PASS 01] pinned payload hash table covers all 344 data files
[PASS 02] data directory holds exactly the 344 known files (found 344 entries)
[PASS 03] file census matches the release: 4 NAM + 197 COS + 143 RES
[PASS 04] no packaged data file is empty
[PASS 05] all 344 data files match the official 20080411 payload sha256
[PASS 06] NAM8 is a GP list literal starting with the cyclic group "C(8)=8"
[PASS 07] NAM11 lists the Mathieu group M(11) and the symmetric group S11
[PASS 08] COS10_10_4 binary header is 'A 5 ' followed by two zero bytes
[PASS 09] COS10_10_4 body is pure alphanumeric coset digits (A-Z0-9)
pari-galdata: 9/9 data-integrity assertions passed
pari-galdata/20080411 (test package): Running test()   # package 模式验证
[PASS 01..09] 同上 9/9
Package 'da39a3ee5e6b4b0d3255bfef95601890afd80709' built
```

（da39a3ee… 为 noarch 空 package_id，符合 `package_id().clear()` 预期。）

## 3. 数据安装说明

- 安装路径：`share/pari/galdata/`（344 文件：NAM8/9/10/11 + COS*×197 +
  RES*×143，2.8MB）
- 许可：`licenses/COPYING`（tarball 无 COPYING/README；recipe 写入
  GPL-2.0-or-later 许可参考，包随 PARI/GP 生态授权）
- 运行期定位：`PARI_GALDATA_DIR`（buildenv_info + runenv_info +
  conf_info）指向数据目录

## 4. 故障注入（验证测试真实拦截能力）

| 注入 | 结果（真实退出码） |
|---|---|
| 篡改 COS10_10_4 字节（seek=20 写 X） | `ValidationError: COS10_10_4: sha256 mismatch`，exit 1 ✅ |
| 删除 NAM9 | `ValidationError: found 343 entries`，exit 1 ✅ |
| 还原后 | exit 0 ✅ |

## 5. 上游测试对照

上游无独立测试套件；上游对数据的消费方式是 gp 解释器的 `polgalois`
（度 8..11 Galois 群计算）。gp 不作为 test_package 依赖（循环依赖 +
版本矩阵解耦），故 upstream_scenarios_executed = 0，以数据完整性断言
（9 项）等效替代。
