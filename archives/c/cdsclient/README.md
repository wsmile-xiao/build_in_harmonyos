# cdsclient

CDS (Centre de Données astronomiques de Strasbourg) 天文数据库命令行客户端工具集。

## 功能

- `aclient` — C 核心客户端，通过 socket 连接 CDS 服务器
- `vizquery` — VizieR 星表数据库查询
- `find_gen` / `find_gen1` — 大型星表通用查询工具
- `find2mass` / `findusno` / `findsdss` / `findgsc` / `finducac` 等 — 特定星表查询
- `catcat` / `lscat` — 星表列表与目录浏览
- `catClient.py` — Python 星表查询客户端
- `simref` / `simbib` — Simbad 参考文献查询
- `abibcode` — 天文文献代码处理

## 上游

- 上游版本: 4.07
- 官网: https://cdsarc.cds.unistra.fr/viz-bin/cdsclient
- 许可证: GPL-3.0-or-later