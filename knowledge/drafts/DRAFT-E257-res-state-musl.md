# E257（草稿）— musl 不导出 glibc `_res` 解析器全局：resolv 状态直接引用编译失败

> severity: 🟡 medium | category: libc, musl, portability, headers | 状态: 草稿

## 错误特征

```
/.../src/core/resolve.c:190:5: error: use of undeclared identifier '_res'
```

（多处连发：`_res.retrans` / `_res.retry` / `_res.nscount` / `_res.options` 等字段访问
与 `match_search_list(&_res, …)` 调用）

## 触发条件

- 目标 libc 为 musl（OHOS sysroot 即 musl 语义）
- 源码直接引用 glibc `<resolv.h>` 导出的全局解析器状态 `_res`
- 上游用无条件编译宏包裹该代码（平台分支无法排除），如 kamailio `Makefile.defs`
  无条件 `-DHAVE_RESOLV_RES`

## 根因分析

glibc `<resolv.h>` 导出 `extern struct __res_state _res;`，网络软件常直接读写
`_res.retrans/_res.retry/_res.nscount/_res.options` 调整 DNS 解析器行为。musl
`<resolv.h>` 仅声明 `struct __res_state` 类型（`typedef struct __res_state {...}`），
`_res` 实例为 libc 内部静态、不对外导出 → 编译期 `undeclared identifier '_res'`。

## 解决方案（构建配置优先，不改源码）

1. **定位宏在编译行中的位置**：若包裹宏之后还有可注入的独立变量
   （kamailio：`$(CC) ... $(C_DEFS) $(DEFS) -c`，`$(DEFS)` 在 C_DEFS 之后），
   用**环境变量**后置 `-U` 撤销（clang/gcc 标志按行序，后置胜出，已实验验证）。
2. **两条不可行路径（kamailio 6.1.3 实测）**：
   - make 命令行 `DEFS=-U…`：命令行变量锁定 in-file 赋值，吞掉 `main.o` 的目标特定
     `DEFS+=-DMODS_DIR` → `main.c` 报 `MODS_DIR` 未声明；
   - `extra_defs='-U…'`：位于 C_DEFS 头部，被后写的 `-D` 覆盖。
3. **回退（无 #else 分支且宏不可撤销时）**：最小补丁追加反向守卫宏
   （glibc 默认不定义 → 行为不变；目标平台经 `extra_defs` 定义 → 走回退分支）。
   补丁不得含平台宏（如 `__OHOS__`），须在 PR 说明理由。

## 验证

```bash
# 撤销宏后应命中上游 #else 回退分支（kamailio: "no resolv options support" 警告）
env DEFS=-UHAVE_RESOLV_RES make -j4 extra_defs='<平台宏集>'
llvm-readelf -d src/kamailio | grep NEEDED   # 仅 libc.so
./src/kamailio -v                            # 版本与 flags 正常
```

## 来源

- kamailio core 6.1.3 OHOS aarch64 适配实测（2026-09-29，
  见 `archives/k/kamailio/6.1.3/notes.md` §2 core delta 2）
- 关联: [E429 草稿]（kamailio Makefile.defs 平台分支缺失，本条目为其 libc 面独立 delta）
