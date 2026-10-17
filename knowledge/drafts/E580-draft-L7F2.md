# E580 — musl 系 sysroot（OHOS）无 `<bits/wordsize.h>`：以 `__WORDSIZE` 推导的 ABI 常量退回 32 位

- **状态**: 草稿（contributor L7F2）
- **严重度**: 3
- **触发工具**: make / clang / gcc / test
- **阶段**: compilation / testing
- **来源事件**: libpfm4/4.13.0-git106-g3e4031b aarch64 交叉编译（tests/validate 报 5 个结构体 ABI size 错误）

## 症状

- 库本身编译、链接全部成功，无任何告警；
- 运行期 ABI 校验失败：libpfm4 的 `tests/validate` 输出 5 行 `ABI size` 错误
  （`pfm_pmu_info_t` / `pfm_event_info_t` / `pfm_event_attr_info_t` / `pfm_perf_encode_arg_t`），
  `pfmlib.h` 中的 `PFM_PMU_INFO_ABI0`、`PFM_PERF_ENCODE_ABI0` 等常量与 `sizeof(struct)` 不等；
- 消费者按公共头的常量填充 `attr.abi_sz` 时同样命中 `if (asz != sizeof(*attr))` 检查点。

## 根因

`__WORDSIZE` 来自 glibc 的 `<sys/types.h>` → `<bits/wordsize.h>`；musl 系 sysroot（OHOS）
不提供该头。上游以 `#if __WORDSIZE == 64` 选择 ABI 常量与结构体字段的平台守卫，宏缺失时
该分支不成立 → 常量取 32 位值，而结构体仍按 LP64 对齐填充，公共头给出的 ABI 契约与真实
布局不一致。

## 推荐方案（rec_approach: portable-lp64-macros）

用编译器内置 LP64 宏替代 glibc 专属宏，产出可移植补丁（同时改公共头，保证库与消费者一致）：

```c
#if defined(__LP64__) || defined(_LP64) || \
    (defined(__SIZEOF_POINTER__) && __SIZEOF_POINTER__ == 8)
```

```bash
patch -p1 < patches/0001-include-perfmon-pfmlib.h.patch
patch -p1 < patches/0002-include-perfmon-pfmlib_perf_event.h.patch
```

libpfm4 实测：补丁后 `make` + 上游 `validate` 全绿（85 段通过、0 error，All tests passed），
无需任何额外编译宏。

## 兜底方案（fallback_approach: force-define-wordsize）

`-D__WORDSIZE=64` 只能修本库自身的编译单元；消费者包含公共头时仍按 32 位常量编译，ABI
依旧不一致（libpfm4 实测 validate 结构体检查照样报错）。仅作应急。

## 禁止做法

用 `__OHOS__` 把原判定包一层（平台专属补丁）：无法上游化，且同一问题在 Alpine 等其它 musl
平台继续复发。

## 验证

```bash
grep -rn "__WORDSIZE\|bits/wordsize.h" include     # 定位判定点
./tests/validate 2>&1 | grep -i "abi size"         # 期望：无输出
```
