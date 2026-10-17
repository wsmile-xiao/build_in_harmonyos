# DRAFT-boxfort-ohos-39bit-user-va-map-fixed-limit：DRAFT-boxfort-ohos-39bit-user-va-map-fixed-limit

> Status: **Draft**（待审核 promote）| severity: `3` | category: `platform|kernel|memory` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-boxfort-ohos-39bit-user-va-map-fixed-limit.kv`

---

## 触发面

- trigger_tool: `clang|meson|任意使用高地址预留窗口的分配器`
- phase: `build`

**匹配关键词**：MAP_FIXED, mmap, EINVAL, VA, virtual address, arena, reservation, high address, shm_open, bxf_arena_init

## 错误签名（error_signature）

```text
mmap.*Invalid argument|MAP_FIXED.*EINVAL|bxf_arena_init.*-22| arena_init.*EINVAL|Cannot map.*arena
```

## 根因（root_cause）

OHOS (HUAWEI MateBook Pro, OHOS 6.1.1, aarch64) 用户态虚拟地址空间上限为 39 位 (512 GiB)。实测 shm fd 映射: MAP_FIXED @0x4000000000 (256 GiB) 成功, @0x8000000000 (512 GiB) 及更高 (0x10000000000/0x200000000000) 全部 EINVAL(22); 不带 MAP_FIXED 的提示地址会被内核忽略并返回常规低地址 (~0x5axxxxxxxx)。 上游 64 位库常用的 [32 TiB, 125 TiB) 预留窗口 (如 boxfort mmap_base=0x200000000000) 在 OHOS 上整体不可用, bxf_arena_init 因此 10 次重试全失败返回 -EINVAL (诊断表现为 bxf_context_init rc=-22)。

## 影响范围（affected_scope）

所有使用固定高地址窗口的内存分配器/arena/JIT/句柄表; boxfort 0.1.2 的 bxf_arena_init (已通过 0001-src-arena.c.patch 将 OHOS 窗口移至 [4 GiB, ~259 GiB) 修复)

## 推荐方案（rec_approach: `ohos-lower-mmap-window`）


## 验证方式（verification_cmd）

```text
shm fd + MAP_FIXED 于 0x4000000000/0x8000000000 探测 EINVAL 边界; boxfort 适配后 bxf_context_init rc=0, context sample PASS (feat/boxfort-0.1.2 设备日志)
```

## 补充关键词

MAP_FIXED, EINVAL, mmap, 39-bit, VA, 虚拟地址, arena, 预留窗口, boxfort, 高地址, shm, 共享内存

---

*本文件由 `knowledge/drafts/DRAFT-boxfort-ohos-39bit-user-va-map-fixed-limit.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
