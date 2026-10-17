# DRAFT：clang -Werror -Wnewline-eof 拦截上游 C 源文件缺文件尾换行

- **ID**: DRAFT-arena-allocator-20260923-newline-eof
- **来源库**: arena-allocator 20260923（ccgargantua/arena-allocator，单头文件 C89 arena 分配器）
- **触发**: `make tests`（clang 15.0.4，上游 Makefile 使用 `-Werror -Wall -Wextra -pedantic`）

## 问题

上游 `arena.c` / `rktest.c` / `rktest.h` 三个源文件在文件末尾缺少换行符。
clang 在 `-Werror` 下将 `-Wnewline-eof` 告警升级为错误：

```
arena.c:3:19: error: no newline at end of file [-Werror,-Wnewline-eof]
#include "arena.h"
                  ^
```

## 根因

POSIX 文本文件以换行结尾；上游文件缺文件尾换行，clang 的
`-Wnewline-eof`（`-Wall`/`-Wextra`/`-pedantic` 组合常见告警）配合
`-Werror` 直接编译失败。

## 方案

仅追加文件尾换行符，不改变任何逻辑：

```bash
printf '\n' >> arena.c rktest.c rktest.h   # 或等价方式
od -c <file> | tail   # 核对末尾为 "\n"
```

用 `track-edit add` 记录修改。补丁仅含换行，无平台宏、无逻辑改动（R6/R8）。

## 验证（arena-allocator 20260923 OHOS armv8）

- `make tests` 编译通过
- `./test`：5/5 上游 rktest 用例全 PASS
- `conan create`（conan-verify G2）通过
- 鸿蒙专项测试 `./test_ohos`：17/17 PASS

## 适用边界/反例

- 仅当 clang 启用 `-Wnewline-eof` 且 `-Werror` 时构成硬失败；gcc 默认
  不报错时不阻塞。
- 修复必须"仅追加换行"，不得顺手改逻辑/格式，避免 diff 噪声
  （例如先 printf 覆盖文件再恢复内容会引入额外改动，应直接 append）。

## 查重

已核对 knowledge/graph/index.tsv 与 knowledge/doc/：无 newline /
Wnewline-eof 同根因条目（exact/causal/trigger/solution 均未命中），
属新增差异（combination_novelty=true、boundary_novelty=true）。

## 关联

- similar_to: none
- caused_by: none
- prerequisite_of: none
- conflicts_with: none