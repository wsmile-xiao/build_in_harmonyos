# DRAFT: CLI 工具 test_package 断言设计三坑（数据大小写 / 无行为选项 / 计数与退出码）

> 草稿。与同 stem `.kv` 成对。触发事件：wordplay 9.0.1 F1–F20 功能用例真机回填
> （r3 13/20 → r4 20/20）。查重：知识库无「数据文件大小写折叠」「文档化选项无行为
> 的断言降级」主题条目；skipIf 换行坑（E056）与 regrtest 竞态（E057）是 Python 侧
> 另一类测试坑，不重叠。

## 适用场景

上游无测试框架的 CLI 工具包（no_tests 处理），test_package 需要**从零设计**功能
断言（sh 脚本驱动打包后的二进制）。本条是三个「源码阅读看不出来、必须实跑才暴露」
的断言陷阱。

## 坑 1：数据文件大小写 → 断言必须大小写折叠

词表/词典类数据文件常为**全大写**（wordplay 的 words721.txt：AARHUS、AARON…），
且程序把输入大写化后输出（`wordplay sotp` 输出 `POST/SPOT/STOP`）。预设断言
`grep -qx "stop"`、`canon(line)==canon(input)` 全军覆没。

```sh
# anagram/字母多重集合校验：折叠大小写后再排序比较
canon() { printf '%s' "$1" | sed 's/ //g' | fold -w1 | sort | tr 'A-Z' 'a-z' | tr -d '\n'; }
# 词匹配一律 -i（必要时加 -x 整行）
grep -qix "stop" out.txt
```

## 坑 2：文档化选项实际无行为 → 断言降级为「接受性 + 输出合法性」

wordplay 的 `-i`（include input phrase）在 usage 里写得明明白白，但真机
`diff <(带-i) <(不带-i)` 在 silent 和 header 模式下**逐字节相同**——上游实现无
可观察效果。硬按文档语义断言必假失败。降级写法：

```sh
# 断言：选项被接受（rc=0）且输出仍是合法结果（对 anagram 即字母多重集合匹配）
"$wp" sotp -s -i -f "$words" > f6 2>/dev/null; rc=$?
[ "$rc" -eq 0 ] && [ 输出行全部合法 ] && [ -s f6 ]
```

并**在 MANIFEST.yml 记录降级原因**（"真机实测 -i 无输出差异，diff 逐字节相同"），
让 reviewer 可核验，而不是静默改断言。

## 坑 3：退出码与计数差一

- 无参数 usage 常是 `exit(-1)` → rc=**255** 不是 1：断言写 `rc -ne 0`，别写 `rc -eq 1`
  （exit(-1)→255 这一事实本身已有先例条目：DRAFT-E682 sc-im、DRAFT-libdv-tools；本条
  把它归入"断言写 rc -ne 0"的预设规则）。
- `printf '%s' "$x" | wc -c` **不含换行**：4 字母词 wc -c 是 4，不是 echo 语义的 5
  （wordplay F10 首版就差在这 1 字节）。

## 通用原则

1. 源码阅读只能给出**断言草案**；真机首跑后必须回填，且回填与 MANIFEST 同 commit。
2. 诊断实际输出时，conan 缓存包在 /storage（HMDFS）**不可直接执行**
   （`inaccessible or not found`），复制到非 HMDFS 分区
   （`/data/storage/el2/base/haps/entry/files/`）再跑；临时文件走 `$TMPDIR`
   （/tmp 只读，E002）。
3. 断言优先「确定性强 + 由输入唯一决定」（字母多重集合、行数、rc、逐字节确定性），
   避免依赖数据文件具体内容（换词表就碎）。

## 证据

wordplay/9.0.1：r3 基于源码阅读的断言 13/20（F4–F10 败于坑 1/2/3）；
按本条修正后设备直跑 20/20，shadow CI r4 全绿。断言修正与 MANIFEST 说明同 commit
（见 archives/w/wordplay/9.0.1/test_package/）。
