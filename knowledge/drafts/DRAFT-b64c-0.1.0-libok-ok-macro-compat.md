# DRAFT-b64c-0.1.0-libok-ok-macro-compat：libok ok() 宏签名变更与老测试代码不兼容

## 问题（b64.c 0.1.0 真机实证）

`make test` 用 libok master 编译失败：

```
test.c:43:5: error: expected ')'
    t(b64_encode, (const unsigned char *) "bradley", "YnJhZGxleQ==");
deps/ok/ok.h:67:3: note: expanded from macro 'ok'
  LIBOK_PRINTF("ok %d - " format, count, ##__VA_ARGS__);
```

## 根因

| 版本 | ok() 宏 | 对 ok(tmp) 的支持 |
|------|---------|-------------------|
| libok master / 0.6.x | `#define ok(format, ...) LIBOK_PRINTF("ok %d - " format, ...)` | ❌ format 必须是字符串字面量才能拼接 |
| libok 0.5.0 及更早 | `#define ok(format, ...) LIBOK_PRINTF(format, ##__VA_ARGS__)` | ✅ format 作为 printf 参数，变量合法 |

b64.c 0.1.0（2023-01）的 test.c 用 `t()` 宏生成 `ok(tmp)` 传变量；tarball 不含
deps/ok（gitignored dev 依赖），`clib install --dev` 拉取的是 master（2023-10 的
0.6.5），宏签名已变 → 编译失败。这是依赖版本漂移，不是库缺陷。

## 方案

获取与库同期兼容的 libok **0.5.0** vender 到 deps/ok 后重编译：

```bash
curl -sSL https://codeload.github.com/jwerle/libok/tar.gz/refs/tags/0.5.0 \
  | tar xz --strip=1 -C deps/ok
make test && ./test
```

## 验证

- libok 0.5.0：`make test && ./test` → TAP `1..8` 全部 PASS（exit 0）
- libok master：编译失败（预期，宏签名变更）

## 适用边界

- 任何声明 `"development": {"jwerle/libok": "*"}` 的 clib 风格 C 库；
- 通用化：**测试框架宏签名会随版本漂移**，拉取开发依赖时应固定与库发布期兼容的版本；
- 与 E063 无关：本条是宏展开语法错误，不是隐式声明。

## 反例

- 误判"上游测试损坏"而删除 test.c / 裁剪断言 → 丢失质量证据；
- 未核对 deps/ok 版本直接用 master → 无效编译失败反复出现。