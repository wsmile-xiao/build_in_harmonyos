# DRAFT-156: 静态 glib 生态测试树 GType 多副本运行期冲突——PIC .a 合成单一共享库收敛注册表副本

> 来源：gst-plugins-bad1.0 1.28.5 适配（PR #11202，任务 #156）｜status: pending-editor-review
> 关联判例：E457（链接期双副本，回避式修法——与本条互补，见"查重区分"）

## 适用场景（何时读这条）

- OHOS 制品仓的 glib2/gobject **只有静态 .a**（动态构建实测失败），你的测试树要跑基于 glib 的上游单测
- 测试树里有 **≥2 个模块各自静态链 glib**：单测框架二进制、被测主件库、vendored 子项目库……
- 测试一跑就崩：`g_param_spec_boxed: assertion 'G_TYPE_IS_BOXED (boxed_type)' failed` / `type id '0' is invalid`——**链接干净、编译全绿、一运行就崩**

## 错误特征（error_signature）

```text
g_param_spec_boxed: assertion 'G_TYPE_IS_BOXED (boxed_type)' failed
type id '0' is invalid
CRITICAL ... g_type_register_static: assertion 'g_type_test_flags (node->...)
SIGSEGV ... gst_check ... crashed while testing
```

## 根因（为什么）

制品仓 glib2 是 PIC 静态形态。测试树三方链接时每个模块都内嵌一份完整的 GType 注册表：
- 类型 `GstFoo` 在**副本 1**（被测库）注册成功
- `g_param_spec_boxed()` 在**副本 2**（测试二进制）查 type id → 查不到 → 0 → 断言崩溃

GType 是**进程级全局注册表**，多个副本天然互不可见。这不是代码 bug、不是平台缺 API，
是"静态链接语义 × 进程级全局状态"的结构性冲突。

## 与 E457 的区分（查重）

| 维度 | E457（avahi-glib） | 本条（gst-bad 测试树） |
|---|---|---|
| 冲突阶段 | **链接期/发布形态**（.so 内嵌 + exe 外链） | **测试运行期**（测试树 N 模块） |
| 触发者 | 消费者建 shared 库 | 上游单测框架（gst_check）+ vendored 子项目 |
| 修法方向 | 回避式（consumer 禁 shared / 等 dep 出 .so） | **正向收敛**（合成单一共享库，副本=1） |
| 可回避性 | 可（改静态链） | 不可（测试框架/被测库/子项目必须同链 glib） |

E457 的修法在本场景失效：测试树无法"全改静态"回避——本来就是全静态，冲突照样发生。

## 解决方案（怎么修，可照抄）

把 conan 静态 glib 系 PIC .a **合成单一共享库**，测试树全模块只链它：

```bash
# 1) 收集 glib 系 PIC .a（依赖顺序：glib → gobject → gio → gmodule）
CONAN_LIBS=$(conan cache path glib2/2.88.0#<rrev>)/lib
# 2) whole-archive 合成（.a 是 PIC，直接可重定位入 .so）
$TOOLCHAIN/bin/clang -shared -o libglib-all-2.0.so \
  -Wl,--whole-archive \
  $CONAN_LIBS/libglib-2.0.a $CONAN_LIBS/libgobject-2.0.a \
  $CONAN_LIBS/libgio-2.0.a $CONAN_LIBS/libgmodule-2.0.a \
  -Wl,--no-whole-archive -lpthread -ldl
# 3) 测试树链接参数替换：-lglib-2.0 -lgobject-2.0 → -l:libglib-all-2.0.so
# 4) 运行时：合成库目录前置 LD_LIBRARY_PATH；GST_REGISTRY 指向测试树隔离路径
```

**实证效果**（#11202）：86/86 测试二进制全部运行至 gst_check 判定完成、零进程崩溃；
26/86 二进制 100% 全过（149 用例零失败）。原崩溃 100% 复现的场景完全消失。

**推广面**：所有 glib 系静态链库的测试场景（gtk4 系/pango 系/gstreamer 全家）；
同法可合成 `libgstcore-all-1.0.so` 解插件 dlopen 路径类失败（同根因）。

## 降级方案（fallback）

合成不可行（非 PIC .a / 循环依赖无法排序）时：
1. test_package 回避式降级：不调用 `gst_init()`，dlopen/dlsym 符号级验证 + SONAME
   readelf 结构校验（E457 回避思路的测试侧等价物），PR 正文如实申报结构性限制
2. 长期路径：推动制品仓发布动态 glib2——实测 `conan install glib2/2.88.0 -o shared=True`
   构建失败（Error 1），当前合成方案是唯一可行解

## 红线（不要做）

- ❌ 不要在 PR 里谎报"测试全过"——运行期崩溃是结构性的，如实申报逐项定性
- ❌ 不要试图给每个测试二进制单独"补 glib 副本对齐"——副本数随模块数增长，不可维护
- ❌ 不要混链（一半模块链合成 .so 一半链 .a）——回到多副本冲突

## 证据链

- 原始失败：本地测试树 testlog.txt（g_param_spec_boxed / type id '0' is invalid 存证）
- 修复 commit：9ef0f7bbc（合成方案落地）+ 74a2c88a6（e2e 消费者测试补全）
- CI 绿：#61125（2026-09-25 20:46）+ #61015 + #61009；AI review：✅ 未发现问题
- 上游测试实测：86 二进制全部实际执行，149/491 用例通过，342 项未通过逐项三类定性
  （插件生态依赖缺失 ~190 / 插件 dlopen 路径 ~120 / Vulkan 无 GPU 环境 34）
