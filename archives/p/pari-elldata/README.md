# pari-elldata

PARI/GP 椭圆曲线数据包 — J. E. Cremona 椭圆曲线数据库的 PARI/GP 版本
（上游数据源 https://github.com/JohnCremona/ecdata/）。

包含导数（conductor）小于 500000 的全部有理椭圆曲线等度同类表示，
供 PARI/GP 的 `ellsearch`、`ellidentify`、`ellgenerators` 使用
（要求 PARI/GP 2.2.11+）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 20210301 | built | noarch 纯数据包（500 个 ell* 数据文件，157MB） |

## 打包形态

- **纯数据包**：上游 tarball 只含数据文件，无源码无编译
- noarch（`package_id` cleared），数据装到 `share/pari/elldata/`
- `PARI_ELLDATA_DIR` 环境变量导出数据目录（build/run env）
- 测试：数据完整性验证（文件集精确匹配 + 逐文件 pin sha256 + 内容健全性），
  详见 `20210301/reports/test-report.md`
