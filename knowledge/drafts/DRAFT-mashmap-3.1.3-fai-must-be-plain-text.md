# DRAFT — 被测程序用 `std::stoul` 解析 `.fai` 时，压缩过的索引会让目标进程 abort

> Status: **Draft**（待主编 promote） | severity: `2` | category: `build-system` | Updated: 2026-10-02
> 源文件：`knowledge/drafts/DRAFT-mashmap-3.1.3-fai-must-be-plain-text.kv`
> 来源：mashmap 3.1.3 适配（`feat/mashmap-3.1.3`）

---

**关键词**：stoul, std::invalid_argument, no conversion, .fai, bgzip, .gzi, signal 6, Aborted, 合成夹具

## 现象（error_signature）

```text
[mashmap::map] time spent computing the reference index: 1.54222 sec
libc++abi: terminating due to uncaught exception of type std::invalid_argument: stoul: no conversion
qemu: uncaught target signal 6 (Aborted) - core dumped
```

崩溃点在参考索引建好之后、比对开始之前，也就是「读取 query 序列长度」那一步。

## 根因（root_cause）

mashmap 3.1.3 的 `mapQuery()` 这样读 `.fai`（`src/map/include/computeMap.hpp`）：

```cpp
std::string fai_name = fileName + ".fai";
if (fs::exists(fai_name)) {
    std::ifstream in(fai_name.c_str());
    while (std::getline(in, line)) {
        auto line_split = CommonFunc::split(line, '\t');
        total_seq_length += std::stoul(line_split[1]);
    }
} else {
    std::cerr << "... WARNING, no .fai index found ... (slow)" << std::endl;
    /* 退化成读全文件累加长度 */
}
```

`fs::exists()` 只判断文件存在，不判断内容是不是文本。测试夹具若按「索引也该压缩」的直觉
把 `.fai` 一起 gzip，`std::stoul` 读到 gzip 魔数 `0x1f 0x8b` 立刻抛
`std::invalid_argument`；异常无人捕获 → `std::terminate()` → `abort()` → signal 6。

真正的约定在 samtools 世界里是：**`.fai` 永远是明文，被压缩的偏移索引另起名字叫 `.gzi`**。
上游 `data/` 目录三件套正是如此：

```text
scerevisiae8.fa.gz        # gzip 的 FASTA
scerevisiae8.fa.gz.fai    # 明文
scerevisiae8.fa.gz.gzi    # bgzip 偏移索引
```

与 OHOS 无关：同一份夹具在 x86_64 Linux 上一样 abort，很容易被误判成「交叉编译 / 模拟器问题」。

## 影响面（affected_scope）

自造 FASTA/FASTQ 夹具的所有适配任务，尤其当被测程序里出现
`stoul` / `stoi` / `stod` / `atoll` 解析索引列或表头列时。
只在「参考/查询带 `.gz` 后缀」时被触发——去掉 `.gz` 就不走这条路，
所以「先跑通一次再去掉 .gz」会把问题彻底藏起来。

## 推荐方案（rec_approach）

按上游布局摆放夹具文件：

| 文件 | 形态 |
|------|------|
| `<name>.fa.gz` | gzip 压缩的 FASTA |
| `<name>.fa.gz.fai` | **明文** |
| `<name>.fa.gz.gzi` | bgzip 偏移索引（可选） |

断言时先校验 `.fai` 是 ASCII text，再跑目标程序：

```bash
file <fixture>.fa.gz.fai     # 期望：ASCII text
```

## 备选方案（fallback）

若被测程序对 `.fai` 的容错不可控，可以干脆不生成 `.fai`，让它走
`no .fai index found ... (slow)` 的慢路径。代价是小数据集变慢，收益是彻底绕开格式假设。
注意这会丢掉「索引解析分支」的覆盖，不适合拿它当默认解。

## 禁忌（forbid）

```python
gzip.open(fixture + ".fai.gz", "wb")   # ❌ 永远不要压缩 .fai
```

后果：W3 本地 `conan create` 在 `test()` 阶段以 signal 6 失败，报错只有一句
`stoul: no conversion`，与真实原因（夹具格式）相距甚远，容易被误判为平台/工具链不兼容
并触发无谓的调参螺旋（R43）。

## 关联

- `similar_to:`（暂无直接条目；与「上游 CLI 缺陷对构建不可见」类目相邻）
- `principles:` P001, P003
