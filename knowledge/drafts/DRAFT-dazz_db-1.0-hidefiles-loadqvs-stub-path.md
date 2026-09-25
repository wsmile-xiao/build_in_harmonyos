# HIDE_FILES 隐藏前缀约定下 Load_QVs 拼接可见 stub 路径错位：按 root[1]=='.' 还原

> Contributor: pc7-11 | Status: Draft | Updated: 2026-09-22
> Source: dazz_db 1.0（thegenemyers/DAZZ_DB 官方 tag V1.0，commit 40bb7e4）
> 适配：conan create 全绿、test_package 41/41 + 消费者 8/8

## 错误特征

对带质量值（quiver）数据的数据库执行读取类命令时，报：

```
DBshow: Cannot open ./.GQ/GQ.db for 'r'
```

`DBshow -q <db>` 与 `DBshow -Q <db>` 均以 exit 1 失败；而 `DB2quiva`、
`quiva2DB`、`DBstats` 等入口全部正常。同一二进制里只有经 `Load_QVs`
读取质量值的路径触发，说明是**路径拼接缺陷**而非数据或符号问题。

## 触发条件

- 构建系统: 任意（实测 raw makefile，HIDE_FILES 常量默认开启）
- 阶段: 运行时（读 QV 时打开可见 stub）
- 前提: 数据库路径按隐藏前缀形态存储（PATHSEP="/."），且读取函数用
  "取最后 '/' 之后 +2" 的方式还原可见 stub 名

## 根因分析

`HIDE_FILES` 打开时（DB.h），辅助文件以 "." 前缀命名（`.GQ.idx`/`.GQ.bps`/
`.GQ.qvs`），`PATHSEP="/."`。`Open_DB` 把 `db->path` 存成隐藏前缀形态：

```
db->path = Catenate(pwd, PATHSEP, root, "")   // "./.GQ"
```

而 `Load_QVs` 打开可见 stub 时用固定偏移：

```c
root = rindex(db->path,'/') + 2;              // "./.GQ" -> 越过 '/'，落到 'G' 之后?
istub = Fopen(Catenate(db->path,"/",root,".db"),"r");
// 拼出 "./.GQ/GQ.db" —— 把 "./.GQ" 当目录，真实可见 stub 是 "./GQ.db"
```

`+2` 偏移是为普通形态（pwd + "/" + root，如 "./GQ"）设计的：越过 `/` 和
root 首字符前的分隔。但 HIDE_FILES 形态多了一个 "." 前缀，固定偏移错位，
于是拼出不存在路径。

## 修复方案

打开可见 stub 前先判断是否带隐藏前缀并还原（与上游 2025-02 快照
a3eefd4 的修复形态逐行一致）：

```c
root = strrchr(db->path,'/');
if (root[1] == '.')
  { *root = '\0';                                  // 临时截断 "/."
    istub = Fopen(Catenate(db->path,"/",root+2,".db"),"r");
    *root = '/';                                   // 还原
  }
else
  istub = Fopen(Catenate(db->path,"","",".db"),"r");
```

即：带隐藏前缀（root[1]=='.'）时，路径头已含 `/.<root>`，可见 stub 应在
去掉前缀后的目录里按 `<root>.db` 拼；不带前缀时直接 `db->path + ".db"`。

## 验证

- 修复前：`DBshow -q GQ` → `Cannot open ./.GQ/GQ.db`（exit 1，实测）
- 修复后（patches/0003）：`DBshow -q GQ`、`DBshow -Q GQ` 均 exit 0，
  输出真实 quiva 内容；test_package 质量值流节 7/7 断言全过
- `DB2quiva`/`quiva2DB` 往返逐字节一致不受影响（对照）

## 适用边界

- **适用**：HIDE_FILES 隐藏辅助文件约定 + Load_QVs 系读取路径的 DAZZ_DB
  生态工具；任何"路径存为隐藏前缀形态、再按偏移拼接可见文件名"的老 C 代码
- **边界/反例**：未开 HIDE_FILES（PATHSEP="/"）时 db->path 无 "." 前缀，
  不触发；绕过 Load_QVs 的读写入口不受影响（仅 DBshow -q/-Q 等暴露）；
  若源码自行使用 `.qvs` 全路径打开（不经 stub 还原）也不触发

## 查重关系

- `similar_to` 无（四范围零命中）
- `caused_by` 上游 V1.0 Load_QVs 路径拼接缺陷 + HIDE_FILES 前缀约定
- `conflicts_with` 无；`prerequisite_of` 无
- 与 E570（rindex→strrchr）不同错误、不同根因、不同修复文件，不构成重复
