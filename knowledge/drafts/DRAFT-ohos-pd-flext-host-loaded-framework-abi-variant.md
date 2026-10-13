# 宿主加载型 C++ 框架库的编译期 ABI 变体协议（flext / Pd 外接）

> 草稿：`draft: true` · contributor_id：`frj__` · 来源任务 pd-flext 0.6.4（任务号 9370）

## 错误特征

用"宿主加载型 C++ 框架库"编译的插件/外接对象，在**构建全绿**的情况下，被宿主
`dlopen` 加载时报未定义符号：

```
error: .../flextest.pd_linux:Error relocating .../flextest.pd_linux:
       _ZN17flext_root_singlenwEm: symbol not found
verbose(0): flextest 100
verbose(1): ... couldn't create
```

注意两点反直觉之处：**编译器/链接器没有报错**（`clang++ -shared ... -lflext-pd`
退出码 0）；报错发生在**宿主进程加载期**，且符号名带 `_single` 后缀，而框架库里
只有 `_shared` 后缀的同名符号。

## 触发条件

- 目标：OHOS PC / AArch64，用 Harmonybrew profile（宿主 `pd` 以 `-rdynamic`
  导出符号）。
- 构建系统：直接用 `clang++ -shared ... -L<flext>/lib -lflext-pd` **手工链接**，
  没有走框架包发布的编译元数据（pkg-config / Conan cxxflags）。
- 代码模式：框架把 **ABI/线程模型编码进编译期宏**——flext 用
  `FLEXT_SYS`（宿主：Pd=2 / Max=1）、`FLEXT_SHARED`（共享+多线程 / 单线程）、
  `FLEXT_EXPORTS`（导出侧 vs 消费者侧），并用 `FLEXT_CLASSDEF` 把基类符号改名。

## 根因分析

`flprefix.h` 里 `FLEXT_CLASSDEF(CL)` 随变体改名：

| 编译期选择符 | 生成的基础类符号 | 用途 |
|---|---|---|
| `-DFLEXT_SHARED`（+ 库侧 `-DFLEXT_EXPORTS`） | `flext_base_shared`、`flext_obj_shared`、`flext_root_shared` | 框架**共享库**导出、消费者引用 |
| （都不定义，或仅 `-DFLEXT_THREADS`） | `flext_base_single`、`flext_obj_single`、`flext_root_single` | 单线程/静态变体 |

框架共享库 `libflext-pd.so` 用 `-DFLEXT_SYS=2 -DFLEXT_SHARED -DFLEXT_EXPORTS`
编译，**只导出 `*_shared`**；消费者漏掉 `-DFLEXT_SHARED` 时引用 `*_single`。
因为产物是共享对象、默认允许未定义符号，链接期不报错；OHOS clang 默认
`BIND_NOW`，宿主 `dlopen` 时立即重定位 → `symbol not found`。

实测（`pd-flext 0.6.4`，宿主 `pd` 来自 `puredata/0.54.1`）：

| 观测 | 命令 | 结果 |
|---|---|---|
| 框架库 soname / 立即绑定 | `llvm-readelf -d libflext-pd.so.0.6.4` | `SONAME libflext-pd.so.0.6`；`FLAGS BIND_NOW` / `FLAGS_1 NOW`；`NEEDED libc++_shared.so, libc.so` |
| 内容是"宿主加载型" | `llvm-nm -u libflext-pd.so.0.6.4 \| wc -l` | **116** 个 UND，其中 `class_new`/`gfxstub_new`/`gfxstub_deleteforkey`/`outlet_new`/`pd_error` 等宿主符号（pd 以 `-rdynamic` 导出，加载时绑定） |
| 同变体消费者 | 带 `-DFLEXT_SHARED` 编外接 → `pd -open` | 通过：`FLEXT_TEST_INIT: 100` / `FLEXT_TEST_RESULT: 105` / `FLEXT_TEST: 105` |
| **异变体消费者** | **不带** `-DFLEXT_SHARED` 编同一外接 | 编译/链接 `RC=0`；`llvm-nm -u` 显示 `flext_obj_single`/`flext_base_single`/`flext_root_single`；`pd -open` 报 `flext_root_single ... symbol not found` + `couldn't create` |

## 解决方案

**推荐**：把变体选择符当作**库包的公共接口**发布，消费者只从包取，不手写。

```sh
# 库侧（导出）：库自身用
-D FLEXT_SYS=2 -DFLEXT_SHARED -DFLEXT_EXPORTS
# 消费者侧（导入）：从包的 cxxflags / pc 取
-DFLEXT_SYS=2 -DFLEXT_SHARED -pthread
```

Conan：`package_info()` 里
`self.cpp_info.cxxflags = ["-DFLEXT_SYS=2","-DFLEXT_SHARED","-pthread"]`；
并生成 `lib/pkgconfig/pd-flext.pc`：
`Cflags: -I${includedir} -I${pdincdir} -DFLEXT_SYS=2 -DFLEXT_SHARED -pthread`。

**禁止做法**：

1. 消费者不带与库一致的变体宏就链接共享框架库——共享对象允许未定义符号，
   **编译/链接静默通过**，错误被推迟到宿主 `dlopen`（BIND_NOW 立即重定位）。
2. 用 `--no-undefined` 或删/加选择符"绕开"报错——变体选择符是 ABI 语义的一部分，
   强行提前报错能暴露问题但不能替代"库与消费者同变体"。

**验证**：先 `readelf -d` 确认框架库的 SONAME 与 `FLAGS_1 NOW`；再对"带/不带
变体宏"各编一个消费者，不带者应能编能链但加载失败——这是最快的自证。

## 通用性证据（独立上游语料）

用**上游自带的 17 个 tutorial 外接源码**（非本仓自写用例）对已安装的
`pd-flext/0.6.4` 包编译链接：

| 语料 | 结果 |
|---|---|
| `tutorial/{1_simple1,1_simple2,1_simple3,2_adv1,2_adv2,2_adv3,3_attr1,3_attr2,3_attr3,4_bind1,4_buffer1,4_timer1,5_signal1,5_signal2,6_lib1,7_thread1,7_thread2}` | **17/17 编译+链接通过，0 失败** |
| `tutorial/{8_sndobj1,8_stk1,8_stk2}` | 跳过（需可选 SndObj/STK 依赖，本适配未启用） |

即"消费者必须带变体宏"并非我们自写用例的特例，而是该框架所有下游外接的共同约束。

## 查重反证（逐条 vs 既有条目）

- `node tools/kb-check.mjs flext FLEXT_SYS FLEXT_SHARED` → KB 0 / Draft 0。
- 最近的邻居 **E442**（host-loaded plugin, private host ABI, unresolved host
  symbols, libtool module, `no-undefined`）描述的是**插件自身的链接契约**
  （`-z defs`/libtool module/未定义宿主符号）；本条是**框架库包**用编译期宏
  标注 **ABI 变体**、并要求消费者同变体（修法层位=库包的编译元数据/cxxflags，
  变量协议=`FLEXT_SYS`/`FLEXT_SHARED`/`FLEXT_EXPORTS`），失败现象也从"链接期"
  移到"BIND_NOW 加载期"。属**不同子族**。
- 与 `DRAFT-E623-libheif-...-plugin-consumer-contract-and-dlopen-signing`、
  `DRAFT-E641-conan-baked-paths-relocatable-dlopen-plugins` 的区别：前者谈插件
  消费者契约与签名、后者谈可重定位路径；均不涉及编译期 ABI 变体宏协议。

## 证据

- 框架库：`llvm-readelf -d`（SONAME/FLAGS/NEEDED）、`llvm-nm -u`（116 UND）。
- 正/负对照：同变体消费者加载成功（3/3 断言）；异变体消费者 `RC=0` 但
  `pd` 报 `flext_root_single ... symbol not found`。
- 语料：tutorial 17/17。
- 关联 PR：（路径 B，随本 PR 提交草稿）。

## 元信息

- authors: `frj__ <241250055@smail.nju.edu.cn>`
- draft: `true` · contributor_id: `frj__`
