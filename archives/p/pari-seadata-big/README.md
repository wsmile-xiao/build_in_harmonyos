# pari-seadata-big

PARI/GP 的大阶 **Atkin 模多项式**数据包 — `seadata-big`，为 `ellcard`
（SEA 点计数算法）与 `ellmodulareqn` 提供素数阶 500 < p < 800 的模多项式
（44 个 `sea<p>.gz`，覆盖 `gp` 在约 1100 位以内有限域上的计算需求）。

数据由 David R. Kohel 计算，取自 ECHIDNA 数据库
（<http://echidna.maths.usyd.edu.au/kohel/dbs/>）。

- 上游主页: https://pari.math.u-bordeaux.fr/packages.html#seadata
- 官方源:   https://pari.math.u-bordeaux.fr/pub/pari/packages/seadata-big.tar （98.7 MB，2017-04-18）
- 许可证:   GPL-2.0-or-later
- 性质:     **纯数据包** —— 无编译、无 configure、无自动化测试；无任何强制第三方库依赖

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 20170418 | built | noarch 纯数据包（44 个 `sea<p>.gz`，98.7 MB 原始归档） |

## 打包形态

- **纯数据包**：上游归档只含数据文件，无源码无编译
- noarch（`package_id` cleared），数据装到 `share/pari/seadata/`
- `PARI_SEADATA_BIG_DIR` 环境变量导出数据目录（build/run env）
- `source()` 对官方 HTTPS 源使用**精确字节区间并发下载**（8 连接，逐段校验
  HTTP 206/Content-Range/长度，拼接后整体校验大小与 SHA-256）；CI 预下载缓存
  （`file://`）路径仍走 Conan `get()` 完整校验
- 测试：数据完整性验证（文件集精确匹配 + 逐文件 pin sha256 + gzip 全量解压
  完整性 + 内容健全性），详见 `20170418/reports/test-report.md`

## 消费方式

包安装后数据位于 `<package_folder>/share/pari/seadata/`。PARI/GP 的
`seadata_cache()` 会**先**加载基础 `sea0`（来自 `pari-seadata` /
`seadata-small`），因此消费方需把本包的 `seadata/` 内容与基础数据合并到同一
数据目录，再让 `gp` 指向它：

```gp
default(datadir, "/应用可写目录/pari");
e = ellmodulareqn(503);
[poldegree(e[1], x), e[2]]   /* [504, 1] */
```

## 目录

- `20170418/conanfile.py` — Conan 配方（数据安装 + 源端完整性校验）
- `20170418/conandata.yml` — 官方源 URL + sha256 + size
- `20170418/test_package/` — 内容级校验（R34）+ 上游无测试声明
- `20170418/notes.md` — 适配笔记
