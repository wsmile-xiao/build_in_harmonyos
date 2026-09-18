# DRAFT-hashmap-0.8.1-set-returns-null-on-insert — hashmap_set() 成功插入返回 NULL，失败须用 hashmap_oom() 判据

- 触发事件：hashmap 0.8.1（tidwall/hashmap.c）test_package 消费者用例运行时
  报 `set alice failed`，首轮 conan-verify G2 失败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-hashmap-0.8.1-set-returns-null-on-insert

## 现象

test_package/test.c 按通用容器 API 直觉编写：

```c
if (hashmap_set(map, &alice) == NULL) { fprintf(stderr, "set alice failed\n"); return 1; }
```

运行输出 `set alice failed`（exit 1），conan-verify G2 的 test() 失败。

## 根因

tidwall/hashmap.c 的 `hashmap_set()` 返回语义与常见容器相反：

- **成功插入新键** → 返回 NULL（`hashmap.c:294-295`：`map->count++; return NULL;`）
- **替换已存在键** → 返回旧值指针（`hashmap.c:301-303`：拷贝旧值到 map->spare 并返回）
- **分配失败（OOM）** → 同样返回 NULL，但置 `map->oom = true`

因此"返回非空 = 成功"的判断把每一次成功插入都当成失败。

## 修复（已在本轮验证）

```c
hashmap_set(map, &alice);
if (hashmap_oom(map)) { fprintf(stderr, "set alice OOM\n"); return 1; }
// 替换路径才断言返回值非 NULL：
const void *old = hashmap_set(map, &alice);
if (!old) { /* 未发生替换，按语义处理 */ }
```

## 验证

- test_package/test.c 重写后：conan-verify G2 PASS（`1/1 Test #1: test_hashmap Passed`，
  直接运行 `hashmap consumer test PASSED`，exit 0）
- 鸿蒙专项测试 tests-ohos/ohos_test.c（插入/更新/扩容路径）同样按此语义：PASSED（exit 0）

## 适用边界 / 反例

- 适用：tidwall/hashmap.c 及遵循"插入返回 NULL、替换返回旧值、独立 OOM 查询"
  约定的库；所有直接消费其公开 API 的消费者用例与上层业务。
- 反例：stb 风格（set 返回新项指针）的库不能套用；`hashmap_get()` 的
  "未找到返回 NULL"语义不受影响（get 的 NULL 就是未找到）。

## 关系

- similar_to: []（无相似条目；E392 是配方 conf 问题，与 API 语义无关）
- caused_by: [] / prerequisite_of: [] / conflicts_with: []
