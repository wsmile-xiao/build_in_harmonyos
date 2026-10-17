# DRAFT-mecab-rcfile-ohos-consumer — MeCab 系词典在 OHOS 的运行期消费：默认 rcfile 硬编码 + 错误被吞

> Contributor: AtomCode (glm-5.3) / Status: **DRAFT** / Updated: 2026-09-20 / Severity: 2 (medium)
> Prospect ID: `DRAFT-mecab-rcfile-ohos-consumer`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E251` | 图谱 | OHOS 上 NLP 词典**构建**模式（mecab-dict-index 索引生成、hash、UTF-8 校验） | E251 管"把词典制品**构建**出来"；本条管"消费者**运行期**怎么正确把词典用起来"——rcfile 加载链、dicrc 布局约束、失败静默特征。构建全绿的制品仍会因本条问题在消费端全灭 |
| `DRAFT-ohos-library-consumer-runtime-data-absent` | draft | 库消费者需**独立交付**的运行期数据（cracklib pw_dict 缺失→断言预期错误码） | 该条数据**未随包交付**、策略是"固化缺口"；本条数据**就在包里**、缺的是**加载参数**（--rcfile）与**布局**（dicrc 同目录），策略是"正确传参与共装"——方向相反 |

**全库查证**：对 `mecabrc`、`rcfile`、`MECAB_DEFAULT_RC`、`dicrc` 关键词全库 grep——
除本条外零命中；MeCab 三词典（ipadic/jumandic/ko-dic）的配方与 notes 均未记载
此消费链约束。

## Scope（何时用）

- 任何 **OHOS 上消费 MeCab 系词典制品**的代码与消费者测试
  （mecab-ipadic / mecab-jumandic / mecab-ko-dic / 自编词典）；
- 任何 **MeCab 词典类 Conan 配方**的 package() 布局设计（dicrc 安装位置）；
- 症状：`mecab_new2` / `mecab_model_new2` 返回 NULL，且 `mecab_strerror(0)`
  给出**空串**——"无错误的失败"。

## Symptom

```c
mecab_model_t* m = mecab_model_new2("-d /path/to/dic");   // 只传 -d
// → m == NULL，且 mecab_strerror(0) 返回空串
```

CLI 同样：

```console
$ mecab -d /path/to/dic "今日は…"        # 不带 --rcfile
（无输出 / 静默失败或空错误）
```

## Root Cause（实测证据：mecab-jumandic 7.0-20130310 适配，mecab 0.996）

1. **默认 rcfile 是构建期硬编码路径**。`src/param.cpp:69` 一带：rcfile 未显式
   指定时回落 `MECAB_DEFAULT_RC`，本仓 mecab/0.996 制品中该宏展开为
   `//etc/mecabrc`。OHOS 只读根文件系统不存在此文件 → open ENOENT →
   模型创建失败。（strace `openat("//etc/mecabrc") = -1 ENOENT` 实证）
2. **失败时错误信息为空**。tagger/model 未建好前错误上下文未挂上，
   `mecab_strerror(0)` 返回空串——极易被误判为"词典数据损坏"或"链接问题"。
3. **dicrc 布局约束**。即便 `--rcfile` 指向了包内 dicrc，mecab 的
   `load_dictionary_resource`（`src/utils.cpp:384-388`）还会对 `-d` 的 dicdir
   无条件加载 `<dicdir>/dicrc`。`mecab-dict-index` 只产出 5 个二进制索引
   （char.bin/matrix.bin/model.bin/sys.dic/unk.dic）、**不复制 dicrc**；
   上游 Makefile.am 靠 `dic_DATA` 把 dicrc 装进词典目录——配方若只拷索引
   就漏了这一环。

## Recommended Solution

**消费端 + 配方端两端配合**（priority 1）：

```c
// 消费端：显式传 dicdir 与 rcfile
mecab_model_t* m = mecab_model_new2(
    ("-d " + dicdir + " --rcfile " + dicdir + "/dicrc").c_str());
```

```python
# 配方端：build() 生成二进制索引后，把 dicrc 复制到索引输出目录
copy(self, "dicrc", src=srcdir, dst=index_outdir)   # 与 .bin 同目录进 package
```

词典制品 `package_info()` 应把 `--rcfile` 用法写进消费者提示。

诊断口诀：**NULL + 空错误串 ≈ rcfile 缺失**。别信空 strerror；用 strace 或回读
param.cpp 的 `model failed` 路径定位。

### 回退方案（priority 2）

制品附最小 mecabrc，消费者 `--rcfile` 指向它（等效换 rc 内容）；或环境层
`MECABRC=<可写路径>/mecabrc`——OHOS 上该文件仍需真实存在，不如 `--rcfile` 直接。

### 禁止做法

- ❌ 因 `mecab_new2` 返回 NULL 就判定"词典数据/索引损坏"去改打包或数据字节
  ——默认失败形态几乎总是 rcfile 路径问题；
- ❌ 把空 `mecab_strerror` 当"无错误"证据——那是错误上下文未挂上；
- ❌ 词典配方只复制二进制索引不装 dicrc——消费者侧必然运行期失败。

## 实测证据（2026-09-20，mecab-jumandic 7.0-20130310）

| 项 | 结果 |
|---|---|
| 只传 `-d` 的 mecab_new2 | **NULL**，strerror 空串 |
| strace | `openat("//etc/mecabrc") = -1 ENOENT` |
| `-d <dicdir> --rcfile <dicdir>/dicrc` | 3 个固定日文样例 golden 分词**全对** |
| OHOS aarch64 工具链一致性 | mecab/0.996 的 mecab-dict-index（OHOS aarch64 原生）产出索引被 OHOS aarch64 libmecab 正确消费 |
| 修正后消费者测试 | C++ test_package 3/3 样例通过（本仓 mecab-jumandic test_package/src/test_package.cpp） |

## 关联条目

- 相似：`E251`（词典**构建**模式；本条是其**消费侧**补全）
- 对照：`DRAFT-ohos-library-consumer-runtime-data-absent`（数据未交付 vs 加载参数缺失）
