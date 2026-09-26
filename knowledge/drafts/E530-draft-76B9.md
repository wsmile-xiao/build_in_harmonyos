# E530: musl open_memstream needs explicit fflush before fclose

## 基本信息
- **严重度**: 2
- **类别**: compat, libc, stdio, musl, ohos
- **来源**: pipewire 1.4.9 HarmonyOS PC 适配

## 错误特征
```
test-spa json_data: FAILED COMPARISON: spa_streq(f_ptr, result)   // got "[[]," expected "[[]]"
fork 模式下 SIGTRAP (signal 5) / double-free
探针: fclose 后 f_size=0, 缓冲未同步
```

## 触发条件
- 构建系统: meson
- 阶段: testing (test-spa-json json_data, test-support logger)

## 根因分析
musl (OHOS) 的 `open_memstream()` 只在显式 `fflush()` 时才把 stdio 缓冲写入外部
buf 并交接所有权；单独 `fclose()` 不保证同步。后果：
1. `fseek(-1)` 覆盖写（如数组闭合回退逗号）不生效 → 内容缺失
2. 先 `fclose()` 再 `free(f_ptr)` → 内部缓冲状态未交接 → double-free → SIGTRAP
而 glibc 的 open_memstream 在 fclose 时正常同步，行为差异导致上游测试在 musl 失败。

## 解决方案

### 推荐方案
```c
/* write buffered data, fseek overwrite, then: */
fflush(fres);
fclose(fres);
/* only now read back f_ptr or free it */
```
- 在 fclose 前显式 `fflush()`
- 覆盖写（fseek+fputc）后同样需要 `fflush()` 才生效
- 读回/释放返回的 buf 前必须已 flush

### 禁止做法
- ❌ fclose 后不 flush 直接 free 返回的 buf（double-free）
- ❌ 假定 fclose 单独即同步（glibc 行为，musl 不同）

## 验证
```bash
conan create archives/p/pipewire/1.4.9 --build=missing
meson test -C build test-spa test-support   # 48/48 全通过
```

## 关联条目
- 相关: E302 (open_memstream capability detection)
- 相关: E409 (flush before abort/exit to preserve output)