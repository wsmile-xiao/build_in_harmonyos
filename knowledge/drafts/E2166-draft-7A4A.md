# E2166 — OHOS CI worker 拒载一切用户目录共享库的 dlopen/LD_PRELOAD（与签名无关），仅 exec 时加载可用

## 错误特征

CI worker 上任何进程启动后再映射用户目录 `.so` 的路径都被拒。探针矩阵（同一构建、同一 worker）：

```
E135PROBE FAIL .../isl-python-shared/.libs/libgmp.so.10: Permission denied   ← 构建期新自签
E135PROBE FAIL .../p/gmpaa.../lib/libgmp.so.10: Permission denied            ← 制品仓发布签名
E135PROBE FAIL .../isl-python-shared/.libs/libisl.so.23.5.0: Permission denied ← 构建期新自签顶层
```

musl 报错形态可反向定位拒绝位置（本条目最重要的判据）：

| 报错文本形态 | 含义 |
|---|---|
| `Error loading shared library <绝对路径>: Permission denied` | 被 dlopen 的**顶层对象**自身被拒 |
| `Error loading shared library <soname>: (needed by <路径>)` | 依赖链中该 **soname** 缺失/被拒 |
| `do_dlsym failed: Symbol not found: X so=<主程序>` | `CDLL(None)` 在全局作用域找符号（说明库根本没进进程） |

对照事实：**exec 时（DT_NEEDED）加载同一批新自签文件完全正常**——#33895 里 14/15 个 C 测试正是经 `LD_LIBRARY_PATH` 解析到 `.libs` 中构建期自签的 `libgmp.so.10` 而通过；但同轮 `LD_PRELOAD` 被静默忽略（预载库未进入全局符号域，无任何 ld.so 告警）。本机（交互式 HNP 环境）比 worker 宽松，**本地 dlopen 成功不能外推到 worker**。

## 触发条件

- 阶段：`make check` / test_package 中任何 ctypes、插件宿主、FFI 测试
- 环境：CI worker（任意一台，#33869 CI-006 / #33895 CI-004 / #33918 复现稳定）
- 前置：与 E135（本机 libintl dlopen 需签名）区隔——E135 的方案在 worker 上是必要不充分，"再签名"没有出路

## 根因分析

worker 的执行域策略作用于"进程启动后新增映射"这一类操作（dlopen、LD_PRELOAD），对用户存储目录下的 ELF 一律拒绝，与 `.codesign` 存在性/新鲜度/签发方无关；而进程启动时的 NEEDED 解析走的是另一条被允许的路径（同为新自签文件，一侧全拒一侧全过）。这解释了为什么"worker 上如何签好一个可 dlopen 的用户库"这个问题**不存在配方解**——只能换加载路径（见 E2167）或按平台边界上报。

## 解决方案

### 推荐方案（probe-then-route-to-exec-time）

1. 先取证：每个候选文件一次独立 `ctypes.CDLL`，**每文件一行短判决**（状态 + errno + OSError 消息尾部 ≤60 字符），顶层与依赖分开探。禁止对多行 traceback 做整体切片截断——#33806 之后 13 轮 CI 拿不到 reason 的元凶是配方自己的 `probe_output[:400]`，不是机器人截断。
2. 定案后换路：把目标库塞进被测进程的启动依赖（exec 路径），参考 E2167 的嵌入式启动器模式。
3. 无路可换时按 R41/R43 口径携探针矩阵上报平台边界，不 skip 不 stub。

### 禁止做法

- ❌ 把多行诊断缓冲整体 `[:N]` 截断（reason 永远在尾部）
- ❌ 对 `~/.conan2` 缓存路径执行 objcopy/签名等写操作（真实事故：诊断实验把制品仓下载的 `libgmp.so.10.5.0` 改成 514432 字节、签名失效，伪造出一天的"签名会过期"假政策；恢复靠 `conan remove gmp/6.3.0.1 -c && conan download gmp/6.3.0.1 -r=ohpcd`，还原后 08-12 的发布签名照常可加载）
- ❌ 用 skip/xfail/stub 糊弄 dlopen 类上游测试

## 验证

```bash
# 三文件各自独立进程探测（每行短输出），worker 上预期三条 Permission denied：
python3 -c 'import ctypes,sys
for p in sys.argv[1:]:
    try: ctypes.CDLL(p); print("PROBE OK", p[-58:])
    except OSError as e: print("PROBE FAIL", str(e)[-58:])' \
  "$PRIV/.libs/libgmp.so.10" "$PUB/libgmp.so.10" "$PRIV/.libs/libisl.so.23.5.0"
# 对照：NEEDED 链含同批新自签库的 C 测试二进制正常执行 = 边界只在 dlopen/preload
```

## 关联条目

- 相关: E135（本机签名后 dlopen 可行，worker 不适用本条更严）, E2164（任务私有副本需当场重签——exec 路径的前提）, E077（签名操作顺序）, E2167（本边界的配方级解法）
- 证据链: PR #6848 构建 #33869/#33895/#33918/#33932；`archives/b/barvinok/0.41.9/notes.md` 第 7 条
