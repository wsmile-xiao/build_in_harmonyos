# DRAFT-cmp-20-cmocka2-api-migration：cmocka 2.x 移除旧测试 API 的上游测试迁移

## 现象

HarmonyOS PC（OHOS musl / clang 15）适配 cmp 20（camgunz/cmp）时，编译上游测试
`test/test.c`（旧 cmocka API 写法）失败：

```text
test/test.c:37:5: error: expected ')'
    unit_test(test_msgpack),
    ^
test/test.c:60:7: warning: call to undeclared function 'run_tests'
  if (run_tests(tests)) {
      ^
...
ld.lld: error: undefined symbol: run_tests
```

## 根因

- 制品仓中的 cmocka 是 2.0.2（ohpcd），而 cmp 20 的上游测试 main 面向旧 API：
  `const UnitTest tests[17] = { unit_test(...) }` + `run_tests(tests)`。
- cmocka 2.x 头文件中 `unit_test()` 旧宏仍在但被标记 deprecated，展开
  `CMOCKA_DEPRECATION_WARNING`（GNU 语句表达式）在严格 C99 下报语法错误；
- `run_tests()` 函数在 cmocka 2.x 已被**删除**，链接必然 `undefined symbol`。

## 可复用修复模式

1. 把测试入口 main() 迁移到新 API：

```c
int main(void) {
  const struct CMUnitTest tests[] = {
    cmocka_unit_test(test_msgpack),
    cmocka_unit_test(test_fixedint),
    /* ... 保持原有 #ifndef CMP_NO_FLOAT 条件 ... */
  };
  return cmocka_run_group_tests_name("cmp", tests, NULL, NULL);
}
```

2. 若源码仍引用残存旧宏（如单元内直接调用 `unit_test`），编译时加
   `-DCMOCKA_DISABLE_DEPRECATION_WARNINGS` 使旧宏在 clang 下可展开。
3. 迁移只改注册/运行机制，不改变测试函数实现，不引入平台宏；
   完成后必须重新编译并完整运行全部上游用例（cmp 20：17/17 通过）。

## 验证

```bash
clang -c test/test.c -std=c99 -DCMOCKA_DISABLE_DEPRECATION_WARNINGS -I<cmocka include>
clang -o cmpunittest cmp.o test_main.o tests.o buf.o utils.o -lcmocka
./cmpunittest   # [ PASSED ] 17 test(s)
```

## 适用范围与反例

- 适用：任何使用旧 cmocka API（UnitTest/unit_test/run_tests）编写测试入口的
  C/C++ 三方库在 OHOS PC 适配，且依赖 cmocka 2.x 制品包。
- 反例：若制品仓仍提供 cmocka 1.x，旧 API 原样可用，无需迁移；
  若测试源自身完全不依赖 cmocka 框架，也不适用本模式。

## 与既有知识的关系

- similar_to: E531（同为 cmocka 相关测试问题，但 E531 是 qsort_r libc 兼容，
  与本条 API 迁移不同面）；E269/E410 涉及 run_tests 字样但均为 Python 场景，无关。
- 无 exact/causal duplicate；无 trigger_overlap（触发面不同：编译期 API 语法）；
- solution_overlap: 无；combination_novelty: 高（cmocka 2.x API 迁移
  在 OHOS PC 场景未见既有条目）；boundary_novelty: 中（C99 严格模式 +
  deprecated 宏展开的组合边界）；test_migration_novelty: 高（迁移上游测试
  入口而非跳过）。
