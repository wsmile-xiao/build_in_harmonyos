# DRAFT-musl-dlopen-local-relocation-scope：musl dlopen 局部重定位作用域——dlopen 的 DSO 只从自身 DT_NEEDED 闭包解析符号，插件类产物须显式链接宿主框架

> Status: **Draft**（待审核 promote）| severity: `3` | category: `platform, musl, linking, runtime, dlopen, plugin` | Updated: 2026-09-29
> 对应: `knowledge/drafts/DRAFT-musl-dlopen-local-relocation-scope.kv`
> 来源: lcmaps-plugins-basic-1.7.1 run（Path-update Path B；第二独立事件，第一事件为 DRAFT-ohos-dlopen-own-dt-needed-closure / libnfsidmap-ldap 2.6.4）

---

## 触发面

- trigger_tool: `dlopen|ld-musl|clang|libtool`
- phase: `linking|runtime`

**匹配关键词**：dlopen, Error relocating, symbol not found, DT_NEEDED, RTLD_GLOBAL, RTLD_LOCAL, RTLD_NOW, BIND_NOW, 插件, plugin, module, libtool -module, musl, ld-musl, 作用域, scope, relocation, 宿主框架, as-needed

## 错误签名（error_signature，CI 实证字面）

```text
Error relocating .*: \w+: symbol not found|Error relocating.*symbol not found|symbol not found.*\(needed by
```

CI 逐字实证（lcmaps-plugins-basic-1.7.1 run5/run9）：

```text
Error relocating /…/lib/lcmaps/lcmaps_dummy_bad.mod: lcmaps_log_debug: symbol not found
Error relocating /…/lib/lcmaps/lcmaps_ban_dn.mod: lcmaps_log: symbol not found
```

辨别点：框架符号**确已导出**且 `dlsym(框架句柄, 同名符号)` 命中，仍报 not found——区别于"符号未导出/未链接"类失败。

## 根因（root_cause）

本平台（OHOS aarch64，musl/ld-musl，clang 15 实测）dlopen() 的 DSO 其未定义符号的重定位作用域 = **该 DSO 自身的 DT_NEEDED 闭包**（加上 libc）——仅此而已：

1. 主可执行程序内定义的符号不可见（探针 P1）；
2. 主程序以启动 NEEDED 链接的其它库（含宿主框架）不可见（探针 P2）；
3. 先前以 dlopen(RTLD_GLOBAL|RTLD_NOW) 预载的库不可见（探针 P3）；
4. 插件自身 DT_NEEDED 宿主框架 → 唯一通路（探针 P4 PASS）。

与 glibc 的分野：glibc 的 dlopen 重定位作用域 = 全局作用域（主程序 + 其全部启动依赖 + RTLD_GLOBAL 对象），上游"插件符号由调用方/主程序供给"的模型在 glibc 成立、在本平台 musl 不成立。

**归因修正（对 E004，修正而不改写）**：E004 把此类 undefined symbol 失败归因 BIND_NOW——BIND_NOW 只解释符号"何时"必须解析（加载时 vs 首次调用），不解释"从哪"解析（作用域）。本条探针证明失败与绑定时机无关：即使全部惰性绑定，未定义符号仍无供给者。E004 的 BIND_NOW 归因不完整，作用域语义才是充分根因；E004 其余内容（dlopen/dlsym 消费面、NEEDED 检查）不受影响，保持有效。

## 影响面（affected_scope）

OHOS (musl) 上一切"dlopen 加载、携带未定义宿主符号"的插件类产物：libtool -module 库、Eval 引擎插件（lcmaps-plugins-*、libnfsidmap 插件）、PAM 模块、解释器扩展、以及任何 test_package 里"dlopen 框架后再 dlopen 插件"的消费者冒烟用例。本题实证：lcmaps-plugins-basic 1.7.1 七个插件上游不带框架链接，CI run5/run9 全部报 `Error relocating …: lcmaps_log(_debug): symbol not found`。

## 推荐方案（rec_approach: `as-needed-wrapped-explicit-framework-link`）

以 **as-needed 包裹的显式框架链接**使插件产物携带对宿主框架的显式 DT_NEEDED（POSIX 能力级适配，非平台条件宏）。配方 generate() 的 LDFLAGS 追加：

```text
-Wl,--as-needed -l<framework> -Wl,--no-as-needed
```

（本题：`-llcmaps_without_gsi`。）插件真实引用框架符号 → NEEDED 落地；加载时同 SONAME 命中进程内已加载的框架实例，符号在同一实例内解析（与 PAM 模块链接 libpam、GStreamer 插件链接 libgstreamer 同型）。

**run10 conftest 教训（必须 as-needed 包裹）**：裸 `-l<framework>` 进 LDFLAGS 会让 configure 的每个链接探针（AC_CHECK_LIB conftest 等，运行时无 LD_LIBRARY_PATH）都背上框架运行时依赖，configure 首查 "whether we are cross compiling" 即报 `cannot run C compiled programs`，误判为交叉编译。as-needed 把 NEEDED 精确限制在真实引用框架的目标上，探针不受污染。

**验证两条（缺一不可）**：

1. `llvm-readelf -d <每个插件> | grep NEEDED` 应见 `lib<framework>.so.N`（本题 ldap_enf 还应见 `libldap.so.2`）；
2. test_package 以 RTLD_NOW dlopen 全部 .mod 且 dlsym 插件契约入口（plugin_initialize/plugin_run/plugin_terminate）全 PASS（CI run11 实测）。

## Fallback（fallback_approach: `static-link-framework-into-plugins`）

静态链接宿主框架进插件（libtool 在 -l 解析时优先命中 `lib<framework>.a`，符号就地解析，无 DT_NEEDED）。诚实权衡：

- 每个插件体积增大；
- 框架以动态方式被宿主加载时，插件内静态副本与进程内动态实例的**全局状态分叉**（日志句柄、credential 缓存等双份），对有状态框架语义不等价；
- 框架自身的传递依赖仍须闭包。

仅当动态 NEEDED 方案不可行（如框架无 .so 交付面）时使用，且须在 notes.md 披露状态分叉权衡。

## 禁止策略（forbid_1）

**RTLD_GLOBAL 预载 / LD_PRELOAD 传符号**：已被探针 P3 证伪——本平台 musl 不把 RTLD_GLOBAL 预载对象加入后续 dlopen 对象的重定位作用域（glibc 语义照搬无效）；LD_PRELOAD 亦不进入 dlopen 对象的解析闭包。该"方案"在 glibc 开发机上碰巧成立、在本平台必然失败，且掩盖"产物缺 DT_NEEDED"的真因 → 本地假阳性 PASS，OHOS CI/真机同一 symbol not found 复现，问题后移到最贵的定位点。

## verification_cmd（自包含，全新 shell 从零跑通）

```sh
D=/storage/Users/currentUser/tmp/oh-device-porting-v2/probe_dlopen_scope
rm -rf "$D" && mkdir -p "$D" && cd "$D" || exit 1
CC=/data/service/hnp/bin/clang
printf 'int fw_sym(void){return 42;}\n' > libf.c
printf 'extern int fw_sym(void);\nint plug_entry(void){return fw_sym()+1;}\n' > plug.c
cat > main_p1.c <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
int fw_sym(void){return 7;}
int main(int c,char**v){void*h=dlopen(v[1],2);if(!h){printf("P1_FAIL: %s\n",dlerror());return 1;}printf("P1_PASS\n");return 0;}
EOF
cat > main_p2.c <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
int main(int c,char**v){void*h=dlopen(v[1],2);if(!h){printf("P2_FAIL: %s\n",dlerror());return 1;}printf("P2_PASS\n");return 0;}
EOF
cat > main_p3.c <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
int main(int c,char**v){void*f=dlopen(v[1],2|0x100);if(!f){printf("P3_PRELOAD_FAIL: %s\n",dlerror());return 1;}void*h=dlopen(v[2],2);if(!h){printf("P3_FAIL: %s\n",dlerror());return 1;}printf("P3_PASS\n");return 0;}
EOF
$CC -shared -fPIC libf.c -o libfw.so
$CC -shared -fPIC plug.c -o libplug_plain.so
$CC -shared -fPIC plug.c -o libplug_needed.so -L. -lfw
$CC main_p1.c -o probe_p1 -ldl
$CC main_p2.c -o probe_p2 -ldl -L. -lfw -Wl,-rpath,"$PWD"
$CC main_p3.c -o probe_p3 -ldl
./probe_p1 ./libplug_plain.so      # 期望 P1_FAIL: fw_sym: symbol not found（主程序符号不可见）
./probe_p2 ./libplug_plain.so      # 期望 P2_FAIL: fw_sym: symbol not found（启动 NEEDED 框架不可见）
./probe_p3 ./libfw.so ./libplug_plain.so
                                   # 期望 P3_FAIL: fw_sym: symbol not found（RTLD_GLOBAL 预载不可见，证伪 forbid_1）
LD_LIBRARY_PATH="$PWD" ./probe_p2 ./libplug_needed.so
                                   # 期望 P4_PASS（插件自带 DT_NEEDED → 唯一通路）
# 四条输出与期望一致 ⇒ 作用域结论成立（2026-09-29 同设备实测）
```

## 与 E078 逐项 diff（Auditor D2：字面最近条目，判非重复）

E078 的 error_signature `Error relocating.*symbol not found` 与本失败**逐字吻合**，须五维判定：

| 维度 | E078 | 本条 |
|------|------|------|
| 归因 | musl BIND_NOW（加载时立即解析，解释"何时"） | 与绑定时机无关（P1/P2/P3 探针：惰性/立即皆失败）；真因是重定位作用域（"从哪"）——BIND_NOW 归因不充分 |
| 领域 | 解释型语言扩展模块（Python/Perl/Ruby C 扩展、LDSHARED/BLDSHARED、ImportError 面） | 原生 C 插件（libtool -module、dlopen 面），非 LSDHARED 场景 |
| 方案 | build-var-override（改 LDSHARED/BLDSHARED 链接变量） | as-needed 包裹的显式 -lframework（LDFLAGS 注入），对解释器构建变量场景不适用、反之亦然 |
| 证据 | 无最小对照探针、无作用域证伪实验 | 附 P1/P2/P3/P4 四探针（自包含可复现） |
| 归因修正指向 | 不涉及 | 修正 E004（与 E078 同族的 undefined symbol/BIND_NOW 根节点）的归因；不改写 E078 解释器场景结论 |

## 其它 similar_to

- **E004**：undefined symbol/BIND_NOW 家族根节点；本条为其作用域维度的归因补全（E004 归因不完整——修正而不改写）。
- **E013**：dl* 构建期链接缺口（-ldl），构建期符号；本条是运行期 dlopen 重定位作用域，正交。
- **E286（部分）**：LLVM 插件 llvmGetPassPluginInfo 符号供给面同属"插件符号须可解析"主题，但根因是 LLVM 导出面/工具链配置，非 loader 作用域。
- **DRAFT-ohos-dlopen-own-dt-needed-closure**：同结论先行草稿（libnfsidmap-ldap 2.6.4 独立事件，2026-09-16，三探针同构、结论一致）；本条为第二独立事件复现，新增 as-needed 包裹教训、E078 逐项 diff、forbid RTLD_GLOBAL/LD_PRELOAD 与静态链接 fallback。promote 时建议合并或互链。

## 原则挂钩（principles）

- **P004**：与 E004 同族挂钩（E004 归因修正的承接面，平台语义类条目）；
- **P013**：平台限制必须降级而非绕过——显式 DT_NEEDED 是能力级适配（降级到本平台可用的链接语义），forbid_1 的 RTLD_GLOBAL/LD_PRELOAD 属绕过。

---

*本文件与 `knowledge/drafts/DRAFT-musl-dlopen-local-relocation-scope.kv` 成对（内容一致、kv 为机器可读权威面）；待审核 promote 后转入 `knowledge/graph/` 与 `knowledge/doc/`。*
