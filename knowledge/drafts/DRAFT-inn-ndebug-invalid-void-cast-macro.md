# DRAFT-inn-ndebug-invalid-void-cast-macro — NDEBUG 分支下的非法宏体

## 可复现症状与稳定错误签名

```
article.c:275:5: error: expected ')'
    VALIDATE_HASH_TABLE();
    ^
article.c:37:41: note: expanded from macro 'VALIDATE_HASH_TABLE'
#    define VALIDATE_HASH_TABLE() (void(0))
                                        ^
article.c:275:26: error: expected expression
```
签名正则：`expected '\)'` + `\Q(void(0))\E`，并伴随 `expected expression`。

## 根因与最小复现

- 上游 `innfeed/article.c`：
  ```c
  #if defined(NDEBUG)
  #    define VALIDATE_HASH_TABLE() (void(0))     /* ← 非法 */
  #else
  #    define VALIDATE_HASH_TABLE() hashValidateTable()
  #endif
  ```
- `(void(0))` 把 `void(0)` 当作**表达式**，但 `void` 是类型名，不能像函数一样调用。
  展开到 `VALIDATE_HASH_TABLE();` 后即 `(void(0));` → 语法错误。
  正确写法是把值为 0 的表达式转成 void：`((void)0)`。
- **只有 Release 命中**：`-DNDEBUG` 才走这一分支。conan 的 `build_type=Release`
  会加 `-DNDEBUG`，而手工 `-O2`（无 NDEBUG）构建不会 → 这就是"本地手工编过、
  conan create 失败"的原因。

最小复现（3 行确认 clang 语义）：
```bash
printf '#define V() (void(0))\nint main(void){ V(); return 0; }\n' > m.c
clang m.c -o m      # error: expected ')'
printf '#define V() ((void)0)\nint main(void){ V(); return 0; }\n' > m2.c
clang m2.c -o m2    # OK
```

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 手工 `./configure && make -O2`（无 NDEBUG） | **通过** —— 掩盖了问题，误导判断 |
| `conan create`（Release，带 -DNDEBUG） | 失败（本条触发），说明必须按 CI 的 build_type 复现 |
| 补丁 `((void)0)` | **通过，采用** |

> 教训：**本地复现必须与 CI 的 build_type 一致**。上游代码里 NDEBUG 分支的问题
> 只在 Release 出现，用 Debug/无 NDEBUG 手工验证会漏。

## 最终方案、输入输出与真实验证

补丁 `patches/0004-innfeed-validate-hash-table-void-cast.patch`：
```diff
-#    define VALIDATE_HASH_TABLE() (void(0))
+#    define VALIDATE_HASH_TABLE() ((void)0)
```
- 验证：inn2/2.7.4 `conan create`(Release) exit 0；`conan-verify` G2 PASS；
  W3 本地 CI 模拟 PASS。
- 性质：这是**上游事实性缺陷**，与 HarmonyOS 无关（Linux Release 同样会报），
  故补丁标 `patch_type: upstream-bug` / `platform_only: False`，并建议回馈上游。

## 注意事项

1. **不要**用"注释掉调用点 / 定义空宏"来绕过——那会把类型错误改成静默去掉
   内部一致性校验（R51 掩盖而非解决，且 Debug/Release 行为分叉被隐藏）。
2. 同类模式见 `E259`：Conan Release 的 `-DNDEBUG` 让 `assert(含副作用表达式)`
   整体不求值，触发上游 latent bug。两者都属"**NDEBUG 才暴露的上游缺陷**"，
   排查时应把"CI 是 Release"作为首要差异项。
3. 补丁虽小，仍应作为独立文件入库（便于上游合并时逐个摘取）。
