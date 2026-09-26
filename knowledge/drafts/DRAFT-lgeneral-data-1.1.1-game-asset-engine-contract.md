# 游戏内容包要按「引擎读取契约」断言，不是按文件数：剧本清单 `scenlist` ↔ `scenarios/` 逐条核对，资产表格用单字节 0xBB 分隔

**来源**：`lgeneral-data 1.1.1` 适配（路径 B 知识库扩展）
**日期**：2026-09-19
**状态**：DRAFT ｜ 上游用例 N=0，本包新增断言 35/35

## 根因

1) 内容包不是"一堆文件"，而是引擎会**按名字索引**读的一棵树：`scenlist` 列出的每个
   剧本都必须在 `scenarios/kukgen/` 里存在，否则玩家点开那一场必然失败；
2) 资产格式本身也要校验：贴图 BMP 的 `BM` 魔数、音效 `RIFF….WAVE`、单位/国家表以 `@`
   开头并用**单字节 `0xBB`** 分隔 key/value（不是 TAB、不是逗号）；
3) "目录里有 23 个文件"这类断言对以上三种损坏全都不敏感。
   实测 lgeneral-data 1.1.1：7 个数据目录、22 个剧本 + 1 个 `.order` 点文件、59 个 BMP、
   8 个 WAV、61 个地图文件、若干单位/国家表段。

## 修法（可复用）

自检按"引擎契约"写三组：① 清单 ↔ 目录逐条核对（含 `.order` 点文件必须被拷出）；
② 资产本体格式（BMP/RIFF 魔数、表格 `@` + `0xBB` + `>` 结束符）；③ 许可与安装纯净性。
点文件丢失的通用成因见 `DRAFT-ieee-data-20260625-conan-copy-star-skips-dotfiles`。

## 判定 / 验证命令

```
cat <pkg>/share/lgeneral-data/scenlist                        # 22 条
ls <pkg>/share/lgeneral-data/scenarios/kukgen | wc -l        # 与清单逐条对齐
python3 test_package/test_lgeneral_data.py <package_folder>  # 35 条断言
```

## 与已有条目的边界

相似条目：[E255, DRAFT-ieee-data-20260625-conan-copy-star-skips-dotfiles]

`DRAFT-ieee-data-…` 处理 Conan `copy("*")` 丢点文件（打包侧通病）；本条把它作为**已知
成因引用**，增量在"内容包要按引擎读取契约断言"这一层（清单↔目录逐条、资产格式、
表格分隔符），两者不重复申报。

## 覆盖范围

所有游戏/模拟器内容包（lgeneral-data、openra 素材、freedroid 数据…）
以及任何"清单文件 + 被清单索引的资产"的数据包。
