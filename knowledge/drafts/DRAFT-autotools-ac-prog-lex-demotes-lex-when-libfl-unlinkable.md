# DRAFT: AC_PROG_LEX(yywrap) 在链接不到 yywrap 库时把 LEX 静默降级为 ':'，scanner 规则空转导致构建失败——应在 make 前按上游原命令行预生成生成物

- 申报域（八分类）: **构建系统语义**
- 机理分层: **L1（平台/构建系统语义层，单库发现即可申报）**
- 阻塞面: **构建失败**（真实 configure 降级日志 + 设备链接探针 + 确定性失败机理链）
- 来源 run: dictd-1.13.3（candidate 3bff290f0500428b51a18426d70ebb44705be915）
- 状态: 草稿，最终编号由知识库主编确认

## 1. 一句话规则

凡 autotools 项目用 `AC_PROG_LEX`/`AM_PROG_LEX(yywrap)` 且源树不含 scanner 生成物，在该环境默认链接路径找不到 `libfl` 时，configure 会**静默**把 `LEX` 降级为 `:`（仅一条 WARNING），make 的 scanner 规则随即空转失败——必须在 make 前用上游原命令行预生成 scanner/parser 产物，或显式给 configure 提供 libfl 搜索路径。

## 2. 机理链（工具实现证据 → 触发命令 → 失败点 → 归类）

1. **工具实现证据（configure 宏语义）**：`AC_PROG_LEX(yywrap)` 先选中 flex，再用 `-lfl` 链接探测 `yywrap` 符号。探测失败与否取决于 **libfl 是否在默认链接搜索路径**，而不是 flex 是否存在。
2. **平台布局证据（设备实测探针）**：OHOS 设备 flex 2.6.4 自带 `libfl.a`，但位于 `/data/service/hnp/flex.org/flex_2.6.4/lib`，不在 clang 15 默认搜索路径。实测：
   - `clang probe.c -lfl -o probe` → `ld.lld: error: unable to find library -lfl`（默认路径，探测必然失败）
   - `clang probe.c -lfl -L/data/service/hnp/flex.org/flex_2.6.4/lib -o probe` → 成功
3. **真实降级日志**：dictd 1.13.3 设备构建日志中 configure 输出
   `checking for flex... flex` + `configure: WARNING: yywrap not found; giving up on flex`，
   随后 `LEX=":"`、`LEXLIB` 为空。**configure 不报错、不中止**。
4. **触发命令**：`./configure && make`。上游 tarball 按惯例不含 scanner/parser 生成物（dictd 的 `servscan.c/servparse.c/clientscan.c/clientparse.c` 均为构建产物），Makefile.in 规则为 `$(LEX) $<` + `mv lex.yy.c $@`（yacc 侧 `bison -tdv` + `y.tab.h/y.tab.c` 改名）。
5. **失败点**：make 执行规则时 `:` 空转返回成功，`mv lex.yy.c servscan.c` 因文件不存在而失败（或后续编译缺 scanner .c）→ **构建失败**。失败前无任何指向 LEX 降级的报错，诊断面极差。
6. **归类**：构建系统语义（autoconf 宏探测语义 × 设备库布局）。

证据日志：本机 `D:/ohos_zcode/runs-v2/dictd-1.13.3/builder/validate-create-9.log`（L133–137 降级 WARNING；L99/L103 为 recipe 抢先预生成命令）与 `builder/ci-run3.log`（权威 CI，同样含降级 WARNING，预生成后构建/测试全过）。

## 3. 方案空间

### rec（主方案）：make 前按上游原命令行预生成
- 逐字取上游 `Makefile.in` 规则命令（例：`flex servscan.l && mv lex.yy.c servscan.c`；`bison -tdv servparse.y` 后 `cmp -s` 再 `mv y.tab.h/y.tab.c`），在 recipe `build()` 内、`make` 之前执行。
- 不改源树、不打补丁，源树保持可向上游提交；scanners 自带 yywrap 的包无需引入 `-lfl`。
- 实测：dictd 四个 scanner/parser 预生成后 `make -j1` 与 `make test` 全量通过（权威 CI PASS，1/1）。

### fallback（退路）：给 configure 暴露 libfl 搜索路径
- `LDFLAGS="-L/data/service/hnp/flex.org/flex_2.6.4/lib" ./configure ...` 使 yywrap 探测通过、`LEX` 保持 `flex`。
- 诚实权衡：路径绑定设备 hnp 布局，布局一变即失效；且对 scanners 自带 yywrap 的包引入非必需的 `-lfl` 链接依赖。**仅作退路。**

### forbid（反模式）
1. **伪造生成物**（`touch`/`echo`/占位文件冒充 `servscan.c` 等）：掩盖生成失败而非修复，编译能过但词法/语法行为与 `.l/.y` 源不一致，问题延迟到运行期且不可审计。
2. **事后改写 Makefile 或 `make LEX=flex`**：只绕过降级结果，不解决 libfl 不可达的探测根因；重新 configure 即复发，修复不可迁移。

## 4. 自包含 verification_cmd（设备新 shell 可复现）

```sh
# (a) 默认链接路径无 libfl —— AC_PROG_LEX 探测失败的根因
printf 'int yywrap(void){return 1;}\nint main(void){return 0;}\n' > /data/storage/el2/base/probe-fl.c
/data/service/hnp/bin/clang /data/storage/el2/base/probe-fl.c -lfl -o /data/storage/el2/base/probe-fl
#   预期: ld.lld: error: unable to find library -lfl
/data/service/hnp/bin/clang /data/storage/el2/base/probe-fl.c -lfl \
  -L/data/service/hnp/flex.org/flex_2.6.4/lib -o /data/storage/el2/base/probe-fl
#   预期: 成功（libfl 存在，仅不在默认路径）
rm -f /data/storage/el2/base/probe-fl.c /data/storage/el2/base/probe-fl

# (b) 降级事实：对任一含 .l 且不带生成物的 autotools 源树
./configure ... && grep -E '^LEX' Makefile      # 预期: LEX = :
grep -n 'giving up on flex' config.log          # 预期: 命中 WARNING 行
```

## 5. 挂钩与泛化

- `principles`: P-AUTOTOOLS-002（configure 检测语义必须真实可用）、P-ENV-001（环境与构建系统语义冲突）。
- `affected_scope`: 任何在 flex 库不在默认链接搜索路径的环境（鸿蒙设备即此布局）上、使用 AC_PROG_LEX/AM_PROG_LEX(yywrap) 且源树不含 scanner/parser 生成物的 autotools 项目。
- `similar_to`: E386（configure/shell 能力探测族）、E146（依赖/符号探测失败的处理）、E277（build() 内补齐构建系统缺失环节）。

## 6. 查重记录（确认去重证据）

检索范围：`knowledge/graph/`、`knowledge/drafts/`、`knowledge/doc/`（设备 baseline 8f05a4eb33 worktree）；检索命令与命中：

- `grep -rli 'getcwd'` / `'giving up on flex'` / `'AC_PROG_LEX'` / `'yywrap|lex\.yy|libfl|-lfl'`
- 命中且排除：`DRAFT-bison-pure-parser-yylex-signature`（主题为 bison pure-parser 的 yylex 签名，非 LEX 降级）、`E062`（FLEXIBLE_ARRAY_MEMBER，仅字面 flex）、`E146`（依赖预编译包，非 lex）、`E549-draft-BEBE`（ANTLR 生成器/运行时分离，非 lex）。
- `giving up on flex`：**零命中**。
- 结论：knowledge/graph 与 drafts 均无本条问题类的机理记录，本条为新增。

## 7. 本 run 内的其他观察（均未占 B 配额，理由备查）

| 观察 | 判定 | 理由 |
|---|---|---|
| HMDFS 路径上 bash 启动 getcwd 失败 → `export PWD=<dir> && cd <dir>` 前缀 + el2/base tmpfs | 域内但已覆盖 → 经验仓 | `DRAFT-autoconf269-config-shell-unset-not-empty`（preset-PWD-env fallback）+ `E386` 已收录同机理与方案；本 run 为第二实例（强化既有草稿，不新增） |
| libmaa 无 recipe → recipe 内 vendored 静态构建 | 已覆盖 → 经验仓 | `E277` 已收录"库自带 vendored 依赖且 registry 无配方时在 build() 内编译"同模式 |
| config.guess/config.sub 不识别 linux-ohos → 双 patch | 已覆盖 → 无需沉淀 | 全仓 1334 处先例 + `DRAFT-E564-oldstyle-config-guess-ohos-reanchor` 等既有条目 |
| libmaa mkc 宏误诊纠正（排除 timer.c 会链接失败，实为缺 `-DSIZEOF_LONG=8`/`-DHAVE_HEADER_SYS_RESOURCE_H=1`） | L3 库内 quirk → notes.md + 经验仓 | 讲不出跨库平台机理，属 libmaa 私有构建细节 |
| `dict --version`/`dictd --version` 上游设计 exit(1) | L3 库内 quirk → notes.md + 经验仓 | 非平台机理 |
| dictunzip 按 argv[0] 分派、以 dictzip 链接提供 | L3 库内 quirk → notes.md | 非平台机理 |
| nodetach 组绑定固定端口 26281，并行 CI 撞端口 | 测试方法论 → 经验仓 | 域外（测试方法论） |
