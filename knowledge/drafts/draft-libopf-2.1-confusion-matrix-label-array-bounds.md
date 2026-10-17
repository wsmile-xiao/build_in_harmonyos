# Draft: 统计矩阵按类别数分配却按运行时 label 索引导致堆越界

(配套 knowledge/drafts/draft-libopf-2.1-confusion-matrix-label-array-bounds.kv)

## 错误特征

example5（无监督聚类）部分数据场景（data3/data4 等）`opf_accuracy` 在
"Computing accuracy ..." 处 **Signal 11 (core dumped)**；ASan 定位
`opf_ConfusionMatrix`（OPF.c:1688）heap-buffer-overflow：
`CM[truelabel][label]++` 的 label 越出按 `nlabels+1` 分配的行数组。

## 根因

libopf 的 `opf_ConfusionMatrix` 与 `opf_Accuracy` 均以 `sg->nlabels + 1` 分配
矩阵（列索引用 label），但**无监督聚类（opf_cluster）输出的簇标签以簇数编号**，
簇数可以大于真实类别数 nlabels（实测 data3 → 13 簇、nlabels=5）。越界 label
写入堆 → SIGSEGV。example5 的 CM 行全零/nan% 场景与崩溃高度相关。

## 修复

两函数分配前先扫描节点取最大 label 作为维度上限，其余循环/统计语义不变：

```c
int maxlabel = sg->nlabels;
for (i = 0; i < sg->nnodes; i++)
    if (sg->node[i].label > maxlabel) maxlabel = sg->node[i].label;
/* 矩阵/误差数组、循环边界全部用 maxlabel+1 / maxlabel */
```

修复后 example5 全 5 场景 rc=0；鸿蒙专项测试构造 label=3 > nlabels=2 场景，
`opf_ConfusionMatrix`/`opf_Accuracy` 返回 acc=50.00% 有效数值、无越界；
conan create 干净构建 G2 PASS（2/2 测试）。

## 与既有知识的关系

四范围查重（正式知识/图谱索引/草稿）均未命中"统计矩阵按类别数分配、按运行时
label 索引越界"条目。与 C1（哨兵字段无符号）同源于本库两个独立缺陷，修复
相互独立，此处单列。

## 适用范围与反例

- 适用：混淆矩阵、误差矩阵、直方图、计数表等按"声明类别数"分配、却用程序
  产生的标签值（聚类/分类输出）做索引的 C 库；无监督/半监督场景尤其典型。
- 反例：矩阵维度按实际最大标签动态扩展、或 label 保证在 [1, nlabels] 内的
  库不适用；钳制 label 仅能临时兼容并会失真，不建议长期采用。