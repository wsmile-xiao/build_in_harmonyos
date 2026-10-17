# OHOS 的 libGLESv2.so 只导出 OES 后缀 VAO 名，核心 ES3 名在 libGLESv3.so

> Draft knowledge entry — 2026-09-23 — 作者 hw-3
> 来源：libstrato 1.0.19（StratoHAL）OHOS 适配实测

## 症状（稳定错误签名）

消费者加载产物时，加载器在**重定位阶段**直接失败并中止进程：

```
Error relocating /path/to/libstrato.so.1: glGenVertexArrays: symbol not found
Error relocating /path/to/libstrato.so.1: glBindVertexArray: symbol not found
Error relocating /path/to/libstrato.so.1: glDeleteVertexArrays: symbol not found
```

关键点：**同一次报错里，其它 `gl*`（glActiveTexture / glClearColor / glBindTexture…）
全部正常解析**，只有这三个 VAO 入口缺失 —— 这个"只缺 VAO"的形态本身就是诊断指纹。

## 根因

OHOS 的 GL 运行库是**分层 + 转发**结构，同一族符号在两个 `.so` 里并不重叠：

| 库 | 导出形态 | 实测 |
|---|---|---|
| `libGLESv2.so` | **单地址转发桩**：675 个导出符号全部指向同一地址 `0xa1b0` | VAO 只导出 **OES 后缀名**：`glGenVertexArraysOES` / `glBindVertexArrayOES` / `glDeleteVertexArraysOES`（各 1 个）；**核心名 0 个** |
| `libGLESv3.so` | 核心 ES3 入口 | **核心名 3 个**（`glGenVertexArrays` / `glBindVertexArray` / `glDeleteVertexArrays`）；**OES 名 0 个** |

复现命令（设备 sysroot，按符号名**精确**比对，不能只用子串 grep——`glGenVertexArrays`
是 `glGenVertexArraysOES` 的子串，会误判）：

```sh
SYS=~/usr/local/sysroot/usr/lib/aarch64-linux-ohos
llvm-nm -D --defined-only $SYS/libGLESv2.so | awk '$3=="glGenVertexArrays"'    # → 空
llvm-nm -D --defined-only $SYS/libGLESv2.so | awk '$3=="glGenVertexArraysOES"' # → 1
llvm-nm -D --defined-only $SYS/libGLESv3.so | awk '$3=="glGenVertexArrays"'    # → 1
```

再加上第三层机理：**OHOS 的 musl 加载器按 BIND_NOW 立即重定位**（`llvm-readelf -d`
可见 `FLAGS: BIND_NOW`、`FLAGS_1: NOW`）。库产物里凡 `DT_NEEDED` 集合中无人提供的
符号（含**函数**，不只是数据），加载期即硬失败 —— 不是运行期惰性解析，也不是静默落空。

于是：上游把 OHOS 的链接集合写成 `m GLESv2 OpenSLES librawfile.z.so`（Linux 上桌面
GLESv2 库同时提供核心名与 OES 名，所以这样写能过），而源码调用**核心 ES3 名**时，
这三个符号无人提供 ⇒ 任何消费者一加载该库就失败。

## 为什么容易误判

- **"编译链接都过了"** —— 构建机 sysroot 里有 `libGLESv2.so`，符号在链接时"看起来"
  由它满足；失败被推迟到加载期。用"能编能链"判定完成必然漏掉。
- **"是不是驱动不支持 ES3？"** —— 不是。该设备 `GL_VERSION` 正常显示
  `OpenGL ES 3.2`（实测 Maleoon 916），只是入口符号没接上。两者症状像、根因完全不同：
  真不支持时 `eglGetProcAddress` 也拿不到。
- **"Error relocating 是运行期问题"** —— 它是**加载器重定位阶段**打印的，进程已经起
  不来，根本还没走到 EGL 初始化 / 上下文创建。同签名的另一族根因见
  `DRAFT-lld-shlib-undefined-host-contract`（宿主应用提供的全局量）。

## 解法（推荐）

在原有 `GLESv2` 之外**同时链上 `GLESv3`**，让核心 ES3 名有提供者。上游自己的示例
App 就是这么做的（`target_link_libraries(engine ... EGL GLESv3 OpenSLES)`）—— 即
"App 层链接集合"里本来就含 GLESv3，打成库包时要把它**下沉到库自身**。

不改上游源码的配方侧写法：

```cmake
-DCMAKE_SHARED_LINKER_FLAGS="-lEGL -lGLESv3 -lhilog_ndk.z -lace_ndk.z -lace_napi.z"
```

验收：
1. `llvm-readelf -d <产物>.so | grep NEEDED` 出现 `libGLESv3.so`；
2. `llvm-nm -D --undefined-only <产物>.so` 里不再有这三个核心名；
3. **真实加载/执行一次**（仅编译通过不算）。

## 兜底（不推荐，仅过渡）

若目标 OHOS 版本确实只提供 GLESv2：

```cmake
-DCMAKE_C_FLAGS="-DglGenVertexArrays=glGenVertexArraysOES \
                 -DglBindVertexArray=glBindVertexArrayOES \
                 -DglDeleteVertexArrays=glDeleteVertexArraysOES"
```

代价：OES 变体语义与核心版不完全等价（某些驱动上 OES 版行为受限），且未来上游改回
核心名会静默失配。属过渡手段。

## 与已有条目的关系（查重结论）

`draft-review` 预审：质量预检 signature ✅ / root_cause ✅ / rec ✅；
相似正式条目 TOP3 = **E520 score=0.58 (sig=1.0 kw=0.07 cat=0.0)**、
E078 score=0.44、E509 score=0.44；预审建议 `merge-into → E520`。

**逐条比对后判定为 create（非重复）**：

| 已有条目 | 关系 | 是否同一机制 |
|---|---|---|
| **E520**（qsb 宿主工具需 LD_LIBRARY_PATH） | 预审建议 merge 的目标。E520 = **构建期宿主工具**运行缺库搜索路径，解法是 `cmake -E env LD_LIBRARY_PATH=...`；本条 = **交付产物自身的 DT_NEEDED 缺一个库**，解法是补链接。触发对象（宿主工具 vs 交付产物）、根因（运行期搜索路径 vs 链接集合）、解法（环境变量 vs 链接标志）、影响面（Qt6 子模块 vs 任意 GL 库）四者全不同 | ❌ 不同机制。0.58 主要来自 E520 的 `error_signature` 是宽泛字符串 `qsb: Error relocating symbol not found`，与本文共享 `Error relocating` 词面（故 sig=1.0），而 keyword 重合仅 0.07、category 重合 0.0 |
| **E078**（musl 默认 BIND_NOW 立即解析符号） | **组分**之一：本条引用的重定位模型。E078 讲"为什么加载期就解析"，不讲"哪个符号缺、去哪补" | 组分，非同机制 |
| `DRAFT-ohos-gl-symbols-are-dispatcher-stubs` | **同族、不同症状与解法**：该条讲"符号存在但是空桩 → **运行期静默落空**（glGetString 返回 NULL、绘制无报错）"，解法是 `eglGetProcAddress` + `-Wl,-Bsymbolic`；本条讲"符号**不存在于已链接集合** → **加载期硬失败**"，解法是补链接。二者不可互替 | 同族，非重复 |
| `DRAFT-ohos-egl-headless-no-gles1-baseline` | 同族基线：OHOS 无 GLES1。本条补上"GLES2/GLES3 之间**核心名 vs OES 名**的分工"，是该基线的细化 | 同族，非重复 |
| `DRAFT-lld-shlib-undefined-host-contract` | **同错误签名、不同根因**：该条是"宿主应用提供全局量（数据）"，解法是消费方补定义块；本条是"库自身缺一个系统库的链接"，解法是库补齐 `DT_NEEDED` | 同签名，非重复 |
| `E509`（harmonybrew 工具链二进制缺 libssl/libcrypto） | 同为"产物缺依赖库"，但那是**部署侧**缺文件，本条是**链接集合**缺声明；且 E509 无 GL/GLESv3 语义 | 非重复 |
| KB 正式库（`index.tsv`） | `grep -c 'GLESv3' knowledge/graph/index.tsv` = **0** —— 正式库中无 `libGLESv3` 相关条目 | 正式库零覆盖 |

### 组合型知识声明（对应「组合型知识不判重」）

**组分清单**：①E078 的 musl BIND_NOW 立即重定位模型；②
`DRAFT-ohos-gl-symbols-are-dispatcher-stubs` 揭示的"OHOS GL 符号是转发/桩"事实；
③`DRAFT-ohos-egl-headless-no-gles1-baseline` 的 OHOS GL 版本基线。

**组合后新增的解题路径与适用面**（新增价值所在）：

- **新事实**：`libGLESv2.so` 与 `libGLESv3.so` 的符号**互不包含** —— VAO 入口在
  GLESv2 里只有 **OES 后缀名**，**核心 ES3 名只在 GLESv3**。此事实在本条之前正式库
  与草稿库均无记载（`index.tsv` 中 `GLESv3` 命中 0）。
- **新判据**："只缺 VAO 三个符号、其余 gl\* 正常"是可直接复用的诊断指纹；且必须用
  `awk '$3=="名"'` 精确比对，不能子串 grep（`glGenVertexArrays` 是
  `glGenVertexArraysOES` 的子串，会误判为"已存在"）。
- **新解法**：`-lGLESv3` 补链接（而非 eglGetProcAddress / -Bsymbolic / 环境变量），
  并指出"上游把 GLESv3 留在 App 层链接"这一模式在**库包**场景必须下沉到库自身
  （属打包边界问题，不是上游 bug）。
- **适用面**：任何在 OHOS 上调用核心 ES3 入口的库（SDL / cogl / clutter / imgui /
  rsgl / 自研渲染后端），不限于本次的 libstrato。


## 实测出处

- 软件：libstrato 1.0.19（StratoHAL，上游自带 `STRATO_TARGET_OPENHARMONY` 目标）
- 上游链接：`target_link_libraries(strato PUBLIC m GLESv2 OpenSLES librawfile.z.so)`
- 调用点：`src/glrender.c` 第 658/659/742/1553 等行用核心 ES3 名
- 修复前：`conan create` 的 `test_package` 加载产物即报上述三行
- 修复后（追加 `-lGLESv3` 等）：22 条消费者断言 `# ALL PASS`，
  `conan-verify` G0/G1/G2/G3/G4/L2/L4/L5 全 PASS
