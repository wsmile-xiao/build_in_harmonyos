# pari-galdata 20080411 适配笔记

## 编译环境
- 构建系统: data（纯数据包，无编译）
- 构建日期: 2026-09-04
- 编译器: 无（数据包）
- 状态: built

## 包的性质

pari-galdata 是 PARI/GP 的 Galois 群数据包：`polgalois` 计算度 8..11
多项式的 Galois 群时需要的群名表与陪集/预解式数据。上游 tarball 解包后
是 `data/galdata/` 目录，344 个文件：

- **NAM8/9/10/11**（4 个文本）：度 8..11 的 Galois 群名字表（GP list
  字面量格式，如 `["C(8)=8", "4[x]2", ...]`）
- **COS\<p>\_\<n>\_\<k>**（197 个二进制）：陪集作用数据（"p n k" 头 +
  字母数字陪集编号体）
- **RES\<...>**（143 个二进制）：预解式数据

**无源码、无构建系统、无编译无链接**，打包 = "解包 → 数据文件安装到
share/pari/galdata/"。完全复用 pari-elldata 20210301 沉淀的纯数据包
范式（knowledge/drafts/E999-draft-B37A）。

## 打包方案（noarch 数据包范式，与 elldata 同构）

- `package_type = "unknown"` + settings 四项全声明（L0p 门禁）+
  `package_id(): self.info.clear()` → noarch
- `build()` 跑同一验证器的 --source-root 模式（损坏下载 create 即失败）
- `package()`：`data/galdata/*` → `share/pari/galdata/`；tarball 无
  COPYING/README → recipe 自写 `licenses/COPYING`（许可参考文本，包随
  PARI/GP 生态为 GPL-2.0-or-later）
- `package_info()`：libs/includedirs/libdirs/bindirs 全空，resdirs=
  ["share"]，`PARI_GALDATA_DIR`（buildenv+runenv+conf_info）

## R34 测试豁免口径（数据包无 API 可调用）

同 elldata：验证以数据完整性为准，9 项断言：

1. **结构完整性**：344 文件精确集合（census：4 NAM + 197 COS + 143 RES）
2. **载荷同一性**：逐文件 sha256 与官方 20080411 载荷 pin 表比对
3. **内容健全性**：
   - NAM8 是 GP list 字面量且以循环群 `C(8)=8` 开头
   - NAM11 含 Mathieu 群 `M(11)` 与对称群 `S11`
   - COS10_10_4 二进制头 `A 5 \x00\x00`（p n k 头 + 陪集数字体）

故障注入实测：篡改 COS10_10_4 字节 → `sha256 mismatch` 拦截（真实
exit 1）；删除 NAM9 → `found 343 entries` 拦截（真实 exit 1）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | package() FileNotFoundError: licenses/COPYING | conan package 目录没有预建 licenses/，直接 open(w) 失败 | os.makedirs(licenses_dir, exist_ok=True) 后再写 |
| 2 | 故障注入显示 exit=0 | 管道后取的是 tail 的退出码，非脚本本体 | 单独跑脚本验证真实退出码：损坏=1，完好=0 ✅ |

## 源码修改

无补丁（数据包，零源码修改）。

## 依赖版本

无任何 conan 依赖（纯数据包）。上游由 PARI/GP ≥ 2.2 的 polgalois 消费。

## 验证结果

```bash
$ conan create archives/p/pari-galdata/20080411 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing
pari-galdata/20080411: Calling build()          # source 模式 9/9
[PASS 01..09]（344 文件 census + sha256 全对 + NAM/COS 内容健全性）
pari-galdata: 9/9 data-integrity assertions passed
pari-galdata/20080411 (test package): Running test()   # package 模式 9/9
[PASS 01..09]
Package 'da39a3ee5e6b4b0d3255bfef95601890afd80709' built   # noarch
```

产物：`share/pari/galdata/`（344 文件，2.8MB），`licenses/COPYING`。
