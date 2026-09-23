# pari-elldata 20210301 适配笔记

## 编译环境
- 构建系统: data（纯数据包，无编译）
- 构建日期: 2026-09-04
- 编译器: 无（数据包）
- 状态: built

## 包的性质

pari-elldata 是 PARI/GP 的椭圆曲线数据包：J. E. Cremona 椭圆曲线数据库
（导数 < 500000 的全部有理椭圆曲线等度同类）。上游 tarball 解包后是
`data/elldata/` 目录，含 500 个数据文件（`ell0`..`ell499`，每文件覆盖
1000 个导数区间）+ README。**没有 configure/make，没有源码，无编译无链接**，
打包 = "解包 tarball → 数据文件安装到 share/pari/elldata/"。

供 PARI/GP 的 `ellsearch`、`ellidentify`、`ellgenerators` 使用
（需要 PARI/GP 2.2.11+）。

## 打包方案（noarch 数据包范式）

- `package_type = "unknown"` + `package_id(): self.info.clear()` → noarch，
  所有平台共享同一个包
- `settings = ("os", "arch")` 仅保留消费者平台信息（构建器/编译器/构建类型
  全部不参与）
- `build()` 只跑确定性数据验证器（与 test_package 同一脚本）→ 损坏下载
  在 create 阶段就失败，而不是装完才发现
- `package()` 把 `data/elldata/ell*` 装到 `share/pari/elldata/`，README 装
  `share/doc/pari-elldata/` 和 `licenses/`（tarball 不带 COPYING，README
  内含 GPL-2.0-or-later 声明）
- `package_info()`：`cpp_info.libs=[]`、`resdirs=["share"]`，导出
  `PARI_ELLDATA_DIR` 环境变量（buildenv+runenv）供下游定位数据目录

## R34 测试豁免口径（数据包无 API 可调用）

数据包无库、无头文件、无可执行文件 → 常规 "编译 consumer 调 API" 的
测试形态不适用，**验证以数据完整性为准**（与 wireless-regdb / mbrola-hu1
先例一致）：

1. **结构完整性**：share/pari/elldata 恰好 500 个 `ell*` 文件，无缺失无多余
2. **载荷同一性**：每个数据文件 sha256 与官方 20210301 发布载荷逐一比对
   （hashes_elldata.py 内嵌 500 个 pin 值，从已校验的上游 tarball 实算）
3. **内容健全性**：ell0 含最小导数曲线 `11a1` 及其正确 Weierstrass 系数
   `[0,-1,1,-10,-20]`；README 记载 Cremona 数据库与 500000 导数覆盖范围

故障注入已验证：截断 ell5 → `sha256 mismatch` 拦截（exit 1）；删除 ell250
→ `found 499 entries` 拦截（exit 1）。

上游测试说明：上游通过 gp 解释器（ellsearch 等）消费数据，无独立测试套件；
gp 不作为 test_package 依赖（会引入循环依赖且 gp 与数据包的版本矩阵解耦），
故 upstream_scenarios_executed=0，豁免理由见 test_package/MANIFEST.yml。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 报 ModuleNotFoundError: hashes_elldata | export_sources 只拷了 test 脚本本体，没拷它 import 的哈希表模块 | export_sources 补拷 hashes_elldata.py |
| 2 | 手工 fakepkg 测试失败 | /tmp 只读（E002）+ 最初断言把 README 误算进数据目录 | 测试布局断言区分 source/package 两种模式：package 模式 README 在 doc 目录 |
| 3 | 首版 ell0 断言写 `[-10,-20] in text` | 该串不是 `[0,-1,1,-10,-20]` 的子串 | 改为完整系数串匹配 |

## 源码修改

无补丁（数据包，零源码修改）。

## 依赖版本

无任何 conan 依赖（纯数据包）。上游建议 PARI/GP >= 2.2.11 消费本数据。

## 验证结果

```bash
$ conan create archives/p/pari-elldata/20210301 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
pari-elldata/20210301: Calling build()
[PASS 01] data directory holds exactly the 500 ell* files plus README (found 501 entries)
[PASS 02] pinned payload hash table covers all 500 data files
[PASS 03] no packaged data file is empty
[PASS 04] all 500 data files match the official 20210301 payload sha256 (first failures: [])
[PASS 05] ell0 contains curve 11a1 with Weierstrass coefficients [0,-1,1,-10,-20]
[PASS 06] README documents the Cremona database and the 500000 conductor range
pari-elldata: 6/6 data-integrity assertions passed
pari-elldata/20210301 (test package): Running test()
[PASS 01..06] package 模式 6/6 通过（500 文件 sha256 全对）
Package 'da39a3ee5e6b4b0d3255bfef95601890afd80709' build succeeded  # noarch 空 package_id
```

产物：`share/pari/elldata/ell0..ell499`（157MB），`share/doc/pari-elldata/README`，
`licenses/README`。
---

**编译结束**: 2026-09-04 02:03
**最终状态**: built
