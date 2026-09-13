# pari-elldata 20210301 — Test Report

- 日期: 2026-09-04
- 构建系统: data（纯数据包，无编译）
- 平台: noarch（`package_id` cleared；OHOS aarch64 profile 下创建验证）
- 结论: **PASS**（6/6 数据完整性断言，conan create 全绿）

## 1. 数据包性质与测试口径（R34 豁免说明）

pari-elldata 是 PARI/GP 的椭圆曲线数据包（J. E. Cremona 数据库）：
上游 tarball 只含 `data/elldata/` 数据文件（500 个 `ell*` 文件 + README），
**无源码、无库、无头文件、无可执行文件、无 API 可调用**。

因此常规 "test_package 编译 consumer 调用被测包 API" 的测试形态不适用
（与仓库既有先例 wireless-regdb/2026.05.30、mbrola-hu1/1.002 同口径），
验证以**数据完整性**为准：

1. 结构完整性（文件集合精确匹配：500 个 ell* 文件）
2. 载荷同一性（每个文件 sha256 与官方发布载荷逐一 pin 比对）
3. 内容健全性（最小导数曲线 11a1 记录、README 覆盖范围声明）

## 2. conan create 结果

```
$ conan create archives/p/pari-elldata/20210301 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing

pari-elldata/20210301: Downloading 57.5MB dd551e64932d4ab27b3f2b2d1da871c2353672fc1a74705c52e3c0de84bd0cf6
pari-elldata/20210301: Sources correctly downloaded
pari-elldata/20210301: Calling build()          # source 模式验证
[PASS 01] data directory holds exactly the 500 ell* files plus README (found 501 entries)
[PASS 02] pinned payload hash table covers all 500 data files
[PASS 03] no packaged data file is empty
[PASS 04] all 500 data files match the official 20210301 payload sha256 (first failures: [])
[PASS 05] ell0 contains curve 11a1 with Weierstrass coefficients [0,-1,1,-10,-20]
[PASS 06] README documents the Cremona database and the 500000 conductor range
pari-elldata: 6/6 data-integrity assertions passed
pari-elldata/20210301 (test package): Running test()   # package 模式验证
[PASS 01] share/pari/elldata holds exactly the 500 ell* data files (found 500 entries)
[PASS 02..04] 500 文件逐一 sha256 与官方载荷全对
[PASS 05..06] 内容健全性
Package 'da39a3ee5e6b4b0d3255bfef95601890afd80709' build succeeded
```

（da39a3ee… 是 sha256 空串哈希，即 noarch 空 package_id，符合
`package_id(): self.info.clear()` 预期。）

## 3. 数据安装说明

- 安装路径：`share/pari/elldata/ell0 .. ell499`（500 文件，157MB）
- 文档：`share/doc/pari-elldata/README`
- 许可：`licenses/README`（tarball 无 COPYING；README 内含 GPL-2.0-or-later
  声明，与 PARI/GP 本体一致）
- 运行期定位：`PARI_ELLDATA_DIR`（buildenv_info + runenv_info + conf_info）
  指向数据目录；PARI/GP 侧由 `default(paridata)` 类机制或下游拼接使用

## 4. 故障注入（验证测试真实拦截能力）

| 注入 | 结果 |
|---|---|
| 截断 ell5（head -c 100） | `ValidationError: ell5: sha256 mismatch`，exit 1 ✅ |
| 删除 ell250 | `ValidationError: found 499 entries`，exit 1 ✅ |

## 5. 上游测试对照

上游无独立测试套件；上游对数据的消费方式是 gp 解释器
（`ellsearch("11a1")` / `ellidentify` / `ellgenerators`，要求 PARI/GP ≥ 2.2.11）。
gp 不作为 test_package 依赖（引入循环依赖 + 版本矩阵解耦），故
upstream_scenarios_executed = 0，以数据完整性断言（6 项）等效替代。
