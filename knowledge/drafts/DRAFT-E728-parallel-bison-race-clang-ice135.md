# DRAFT-E728-parallel-bison-race-clang-ice135

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-E728-parallel-bison-race-clang-ice135.kv`

**标题**：旧 autotools+yacc 包：.y 规则 target 与产物名不匹配致 bison 每轮必跑，-j>1 并发覆写生成物 → 编译器 ICE（clang exit 135）表象，配方钉 -j1

**阶段: `compilation` · 触发: `build|cc` · 类别: `build, autotools, parallel, race, yacc, toolchain` · 严重级: `2`**

## 错误签名（error_signature）

```text
"clang frontend command failed with exit code 135|PLEASE submit a bug report to https://github.com/llvm/llvm-project/issues|parsing function body '_calc_complement'"
```

## 根因（root_cause）

>
  上游 Makefile.am 的 yacc 规则 target 名与实际产物不一致（genders: target
  `genders_query.c`，而 `$(YACC) -d -b genders_query` 产出 `genders_query.tab.c`），
  target 永不落地 ⇒ 每轮 make 都重跑 bison；BUILT_SOURCES 让多个消费者各自触发同一
  规则。make -j>1 时多个 bison 进程并发覆写同一文件 → 交叉写坏的半截生成物被 clang
  编译 → 编译器前端崩溃（genders 实测 clang-15 exit code 135、崩点伪随机落在
  `_calc_complement` 等函数解析）。A/B 实测：同一源树 -j4 必现（bison×3 + ICE、
  make rc=2），-j1 rc=0——纯并发竞态，不是 clang 或上游代码缺陷。
  排查陷阱：ICE 栈里出现具体源码位置会把人引向「编译器 bug / 代码 UB」，真正的判据是
  串并行 A/B 与 bison 执行次数（grep 'bison -y' 日志计数）。

## 方案（rec_approach）

pin-serial-make

## 关键词

bison, yacc, -j4, 并发, 竞态, BUILT_SOURCES, genders_query, tab.c, clang ICE, exit code 135, 生成物, 交叉写坏, 串行, -j1

## 来源

本条目取自 `knowledge/drafts/DRAFT-E728-parallel-bison-race-clang-ice135.kv`；promote 后对应 `knowledge/doc/E###.md`。
