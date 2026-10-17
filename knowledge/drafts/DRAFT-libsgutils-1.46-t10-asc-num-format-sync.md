# DRAFT-libsgutils-1.46-t10-asc-num-format-sync：sg_chk_asc / t10.org 2024 现行表格式同步

> Contributor: pc1-40 | Status: Draft | Updated: 2026-09-17
> Source: libsgutils (sg3_utils) 1.46 适配（task libsgutils-1.46-r03-pc1-40-20260917T015652Z）

## 问题

上游测试 `testing/sg_chk_asc`（ASC/ASCQ 附加 sense 码表与 t10.org 一致性检查）对
t10.org 现行 `asc-num.txt`（2024-11-28 版）运行报 27 项差异：

```text
0,23 differ, ref: OVERLAPPING ATOMIC COMMAND IN PROGRESS, sg_lib_data: <missing>
20,5 differ, ref: OBSOLETE, sg_lib_data: WRITE TYPE OPERATION WHILE IN READ CAPABLE STATE (OBS)
2c,1 differ, ref: TOO MANY WINDOWS SPECIFIED {%, sg_lib_data: TOO MANY WINDOWS SPECIFIED
...
```

差异分三类：**3 条 `<missing>`**（现行表新增码，库缺失）、**3 条文本改为 "OBSOLETE"**、
**21 条带 `{%`(Now-Obsolete) 标注后缀**。

## 根因

t10.org `asc-num.txt` 现行表格式演进：过时条目描述后追加 `{%` (Now-Obsolete) 标注，
部分条目描述直接改为 "Obsolete"。`sg_chk_asc`（v1.09/v1.10）以固定 `offset=24`
读取文件原始文本，与 `sg_lib_data.c` 内置表逐字比对（大小写归一化）。1.46 内置表
未跟随 t10.org 演进 → 27 项 differ。

## 方案（逐字同步至 t10.org 现行表）

1. **新增缺失码**：现行表已收录而库缺失的条目（如 `{0x00,0x23,"Overlapping
   atomic command in progress"}`、`{0x38,0x09,...}`、`{0x67,0x0E,...}`）按现行表文本补入。
2. **Obsolete 文本同步**：被现行表改为 "Obsolete" 的条目（20,5 / 24,2 / 24,3）
   文本同步为 `"Obsolete"`。
3. **`{%` 标注逐字保留**：Now-Obsolete 标注是文件原始文本的一部分，`sg_chk_asc`
   读原始文本比对，必须逐字保留（如 `"Too many windows specified {%"`），
   剥离标注会导致比对失败。

同步后重编库与 sg_chk_asc，重跑差异行必须为 0。

## 验证

- libsgutils 1.46：`sg_lib_data.c` 表同步 27 项后 `sg_chk_asc` 重跑差异行 = 0
  （2026-09-17），全量通过率 3/17 → 4/17（sg_chk_asc 修复通过），实际执行 4/4 = 100%。
- 补丁：archives/l/libsgutils/1.46/patches/0004-lib-sg_lib_data.c.patch（+27/-24），
  已登记 conandata.yml。

## 适用边界 / 反例

- 仅对内嵌 SCSI ASC/ASCQ 表并与 t10.org 对齐的库有跨库复用价值（sg3_utils 系消费者）。
- 纯消费 `sg_get_asc_ascq_str()` 的库无需关心标注。
- 若 t10.org 改回无标注格式则差异自然消失；`sg_chk_asc` 工具恒返回 1
  （`ret` 初始化 1 且无置 0 路径），通过判据是 stderr 无 "differ" 行。

## 查重差异（对既有知识）

- 四范围（knowledge/graph、doc、drafts、文档）grep `t10.org`/`asc-num`/`sg_chk_asc`/
  `ASC/ASCQ` 零命中，exact/causal/trigger/solution 均未覆盖，combination/boundary
  有新意（"2024 表格式 + offset=24 逐字比对 + 逐字表同步"组合），new_draft。
- 相关：E007（autotools 工具链对现行生态适配族）、
  DRAFT-libsgutils-1.46-ohos-missing-drand48-r（同为本库 OHOS 上游差异族）。