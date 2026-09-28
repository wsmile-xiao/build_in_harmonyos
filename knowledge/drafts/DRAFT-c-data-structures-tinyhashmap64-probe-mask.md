# DRAFT-c-data-structures-tinyhashmap64-probe-mask — 开放寻址哈希表初始容量必须为 2^n-1(全 1 掩码)

- 触发事件:c-data-structures 0.0-git0c2d777456(schellingb,c-data-structures)首轮适配。
  上游 test.c 在 test_hmap64 挂死(timeout 124,VmSize 涨至 2GB+),test_buf/test_hmap 正常。
- 路径:Path B(知识库扩展)
- 编号:DRAFT-c-data-structures-tinyhashmap64-probe-mask

## 现象

上游 test.c 编译运行后输出 `Testing buf...` 即停住(实际已过 test_buf/test_hmap,
卡在 test_hmap64),进程 CPU 100%、VmSize 涨至 2GB+ 后仍不结束,timeout 杀死。

## 根因

tinyhashmap64.h 的 `hmap64__grow` 首次分配:

```c
size_t new_max = (old_ptr ? old_hdr->maxlen * 2 + 1 : 16);   // ← 16 是笔误
```

探测循环依赖 maxlen 为 2^n-1(全 1 掩码):

```c
for (i = key;; i++)
    if (hdr->keys[i &= hdr->maxlen] == key) { ... }
```

`maxlen=16`(0b10000)时 `i &= 16` 只产生槽 0 或 16。插入两个字符串键
"foo"(hash&16=16)+"bar"(hash&16=0)后,查询缺失键 "baz"(hash&16=0,
与 "bar" 冲突)→ `i++` 后再次 `& 16` 永远回到 0/16 → 线性探测死循环。
同库 32 位版 tinyhashmap.h:172 用 `15` 正确(全 1 掩码),64 位版是复制笔误。

## 修复(已在本轮验证)

`patches/0001-fix-tinyhashmap64-initial-new-max.patch`:`: 16` → `: 15`。
修复后 -O0/-O2 全量 test.c 通过(exit 0),鸿蒙专项 + test_package 消费者全过。

## 验证

```bash
clang -O2 -Wall -Wextra test.c -o upstream_test && ./upstream_test   # 修复前挂死
# 修复后:
clang -O2 test.c -o upstream_test && ./upstream_test   # Testing buf/hmap/hmap64 + Done, exit 0
```

## 适用范围与反例

- 适用:任何使用 `i &= maxlen` 线性探测的开放寻址哈希表,初始容量必须 2^n-1。
- 反例:分离链接(链地址)哈希表不受影响;负载因子驱动的 rehash 上限判断
  (`new_max / 2 <= res`)不正确时也可能溢出但在位宽内不会死循环。
- 边界:只有首次分配(old_ptr==NULL)路径使用该常量,后续 grow 用
  `maxlen * 2 + 1` 自动保持 2^n-1;因此只修首次值即可。