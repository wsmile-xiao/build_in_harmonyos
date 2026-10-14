# jshon

jshon — 命令行 JSON 解析工具。以栈式过滤器管道（`-e`/`-a`/`-p` 等）从 stdin
或文件（`-F`）提取、编辑与创建 JSON：`-t`/`-l`/`-k`/`-u` 读取类型/长度/键/原始
字符串，`-s`/`-n`/`-i`/`-d` 创建、插入、覆盖与删除节点。

- 上游: https://github.com/keenerd/jshon
- 许可: MIT
- 本仓适配版本: 20131105（上游最后一个正式 tag，2013-11-05）
- 依赖: jansson（复用制品仓 `jansson/2.15.1.1`，不 vendoring）

## 包内容

- 可执行文件: `bin/jshon`
- man 手册: `share/man/man1/jshon.1`
- 许可: `licenses/LICENSE`

## 用法

```console
$ echo '{"a":1,"b":{"c":"str"}}' | jshon -e b -e c -u   # 嵌套提取并去引号
str

$ echo '[10,20,30]' | jshon -e 1 -u                     # 数组下标
20

$ echo '{"x":true}' | jshon -e x -t                     # 类型
bool

$ echo '{}' | jshon -s hello -i greeting                # 创建 JSON
{
 "greeting": "hello"
}

$ echo '{"a":1,"b":2}' | jshon -d a                     # 删除 key
{
 "b": 2
}

$ echo '{bad' | jshon -t; echo $?                       # invalid JSON
json read error: ...
1
```

主要选项：`-e <key|idx>` 提取、`-a` 迭代、`-p` 出栈、`-t` 类型、`-l` 长度、
`-k` 键、`-u` 去引号、`-s <str>` 字符串、`-n <json>` 非字符串字面量、
`-i <key|idx>` 插入/覆盖、`-d <key|idx>` 删除、`-F <file>` 输入文件、
`-P` JSONP 容错、`-S` 键排序、`-Q` 静默、`-C` 容错继续、`--version` 版本。

## 构建与测试

- 配方: `20131105/conanfile.py`（纯 Makefile 包，无 configure；upstream flags
  全保留，两个 `-Wno` 抑制经 Makefile 的 `${CFLAGS}` 尾部注入，jansson 头/库
  路径经 `CPPFLAGS`/`LDFLAGS` 注入，`CC` 在 make 命令行钉住）
- 补丁: `20131105/patches/0001-include-sys-types.patch`（补缺失的
  `<sys/types.h>` 包含，修复 OHOS musl 下 `uint` 类型不可见；portability）
- 测试: `20131105/test_package/`（消费者测试，31 项断言：JSON 全类型读取、
  创建/修改/删除、invalid JSON 非零退出、ELF 专项）；上游本身**无任何测试**
  （详见 `20131105/notes.md` 与 `20131105/test_package/MANIFEST.yml`）

## OHOS 适配状态

版本 `20131105` 本地验证完成（本机即 OHOS aarch64 真机）：conan create 构建
通过（upstream flags 全保留），test_package **31/31 断言通过**（JSON 全类型
读取、创建/修改/删除、invalid JSON 非零退出、ELF 专项全绿）；CI L1-L4 冒烟
待推送后执行，详见 `20131105/notes.md`。
