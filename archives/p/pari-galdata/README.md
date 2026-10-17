# pari-galdata

PARI/GP Galois 群数据包 — `polgalois` 计算度 8..11 多项式 Galois 群
所需的群名表与陪集/预解式数据。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 20080411 | built | noarch 纯数据包（344 文件：4 NAM + 197 COS + 143 RES） |

## 打包形态

- **纯数据包**：上游 tarball 只含数据文件，无源码无编译
- noarch（`package_id` cleared），数据装到 `share/pari/galdata/`
- `PARI_GALDATA_DIR` 环境变量导出数据目录（build/run env）
- 测试：数据完整性验证（344 文件 census + 逐文件 pin sha256 +
  NAM/COS 内容健全性），详见 `20080411/reports/test-report.md`
