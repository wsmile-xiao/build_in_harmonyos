# OHOS 设备「依赖二进制存在却被拒绝映射」知识包（loader-refused-map gap）

> 一句话：消费者/测试运行时加载依赖库失败，错误点名的 `.so` **文件明明存在**，
> 但设备加载器拒绝把它映射进进程——这不是缺库，也不是配方缺陷，
> 需要按「设备侧映射策略」单独判定与处置。

本知识包解决的问题类别（既可用于人工判读，也可脚本化执行）：

- ① 识别：给出错误签名与「拒绝映射 vs 真缺库」的机器可判定判据（`detect_loader_refused_map.py`）
- ② 处置：本仓库落地形态（test_package 运行期分类 + 符号级降级验证），以及不可绕场景的上报口径
- ③ 文档：触发场景 / 适用库范围 / 限制与反例（本文）
- ④ 样例库：`archives/x/xmhtml/1.1.10`（本知识包与样例同 PR 交付，实测案例）

---

## 1. 触发场景

运行期（不是构建期）加载共享库失败，且失败点在设备加载器，而非库文件缺失：

| 场景 | 表现 |
| --- | --- |
| `conan create` 的 `test_package/test()` 执行消费者二进制 | 消费者退出 127，`ConanException: Error … while executing`，日志停在加载错误 |
| W3 `conan-verify` G2 | `conan create 失败` + 错误签名（本项目 G2 判 FAIL） |
| CLI 冒烟测试 / 已发布包的运行期用例 | `Error loading shared library <soname>: (needed by <path>)` 后级联 `symbol not found` |
| `dlopen()` 探测 | `dlerror()` 报 `<soname>: Permission denied` |

**关键区分**：库文件存在（`-e` 成立、可 `md5sum`、可 `cat`），但加载器拒绝映射；
同时同设备上**其它**依赖内容可以正常映射。

## 2. 错误签名（怎么认）

musl exec 路径（可执行文件启动时解析 NEEDED）：

```
Error loading shared library libXft.so.2: (needed by ./test_consumer)
Error loading shared library libfontconfig.so.1: (needed by ./test_consumer)
Error loading shared library libXft.so.2: (needed by /…/p/lib/libXmHTML.so.1.1)
Error relocating /…/p/lib/libXmHTML.so.1.1: XftNameParse: symbol not found
Error relocating /…/p/lib/libXmHTML.so.1.1: FcPatternCreate: symbol not found
```

注意两点（实测，2026-10-04）：

1. **exec 期消息的“原因”段是空的**——形如 `libXft.so.2: (needed by …)`，
   没有 `Permission denied`、也没有 `No such file or directory`。
   只有 `dlopen()` 路径才把原因带出来：`<soname>: Permission denied`（EACCES）。
   ⇒ **不要用“日志里有没有 Permission denied”做判据**，会漏判。
2. 后面的 `symbol not found` 是**级联**（依赖没映射进来导致符号解析失败），
   不是“缺符号”类缺陷；按它们判定会把设备策略误判为配方问题。

## 3. 判据：拒绝映射 vs 真缺库（机器可判定）

对错误日志里每个 `Error loading shared library <name>:` 点名的 `<name>`：

1. `<name>` 为绝对路径 → 直接看该路径是否存在；
2. 否则在运行期库路径（`LD_LIBRARY_PATH` 的每个目录）中查找同名文件；
3. **全部命中** ⇒ 属于「存在但被拒绝映射」（设备策略面）；
   **任一未命中** ⇒ 属于「真缺库」（配方/打包缺陷，如 CI 漏投依赖，必须修）。

`detect_loader_refused_map.py` 实现上述判据，退出码：

| 退出码 | 含义 | 后续动作 |
| --- | --- | --- |
| 0 | 判为「存在但被拒绝映射」 | 按 §5.1 处置（测试脚本分类放行 + 符号级降级验证 + 如实记录） |
| 1 | 判为「真缺库」 | 按缺依赖处理：补齐依赖后重跑（R36）；不得用策略分支放行 |
| 2 | 无加载错误（库可正常加载/消费者成功） | 无需本知识包介入 |

## 4. 适用库范围

- **受影响**：链接了 `HAVE_XFT` 一类可选字体/图形栈的库（Xft → fontconfig → freetype/libxml2 链）、
  任何其**已发布依赖二进制**被目标设备映射策略拒绝的包；表现为运行期加载失败而构建链接全绿。
- **命中的库形态**：本案例中 `libXft.so.2`、`libfontconfig.so.1` 两个**已发布二进制**
  被拒；同设备上 `libXrender`、`libXm`、`libxml2`、以及本包自身 `libXmHTML` 均可正常映射。
- **不受影响**：纯静态链接包（无运行期加载）；只依赖 libc/libstdc++ 等平台自带库的包；
  依赖可正常映射的设备与 CI（本分支不触发）。

## 5. 处置策略

### 5.1 推荐：test_package 运行期分类 + 符号级降级验证（本仓库落地形态）

样例：`archives/x/xmhtml/1.1.10/test_package/test_xmhtml_consumer.sh`（与消费者同 PR 交付）。

- 先**真实执行**消费者二进制（R34：不得退化成打印字符串）：成功 ⇒ PASS；
- 失败则分类：①本包自身库加载失败 → FAIL；②点名的依赖在运行期库路径中不存在 → FAIL；
  ③点名的依赖**存在却拒绝映射** → 打印 `PLATFORM_POLICY_SKIP` 证据块（逐库给出解析到的
  绝对路径 = present-but-refused 证据）+ **符号级降级验证**（`nm -D` 校验本包库确实投递并
  导出公共 API/widget 类符号）后放行；
- 依赖可加载的设备/CI 上，①②③ 都不触发放行分支 ⇒ CI 侧仍是完整运行期验证。

要点：放行分支必须**只有**在“点名依赖都能解析到文件”时成立，且必须打印证据、
不得静默通过（否则会掩盖真实缺库）。

### 5.2 构建期就命中（链接/configure 阶段）——不可绕场景的上报口径

若依赖在**构建期**就无法使用（头文件/链接符号/工具链层面），运行期没有可绕路径：
按 `env_unsupported` 上报（`result --status env_unsupported --failed-reason …`），
不要用 stub 顶替、不要跳过验证宣称成功。

### 5.3 禁止做法（踩过或可预见）

| 禁止 | 原因 |
| --- | --- |
| 用同名空壳/弱符号 stub 顶替被拒依赖，让测试“通过” | 掩盖真实链路；消费者行为与真实部署不一致（与 R8 平台宏空壳同一性质） |
| 只改权限位/改名/复制/objcopy 重写被拒库 | 实测全部无效（见 §6），浪费轮次 |
| 把 test_package 改成只打印字符串/只断言编译产物存在 | 违反 R34；CI L0d/PF3 会拦，且失去运行期验证能力 |
| 反复清缓存重下依赖指望字节变化 | 实测重建产物（本地源码重建）同样被拒 |

## 6. 限制与反例（实测边界）

- **不可按需复现**：拒绝随**内容**走，同一目录、同一创建方法下，其它内容可正常映射
  （对照实验：`a_Xrender.so` 可映射 / `b_Xft.so`、`c_fontconfig.so` 被拒 / `d_libXm.so` 可映射 /
  `e_libxml2.so` 可映射）。⇒ 不能靠“换个目录/换种写文件方式”绕过。
- **与权限位无关**：0750/0755/0770、软链先删后建、`llvm-objcopy` 重写均无效；
  同一写入方式产出的文件权限完全相同，仍按内容分派。
- **与 ELF 结构无关**：被拒与被允许库的程序头/动态段标签一致
  （`LOAD=R,RX,RW,RW`、`GNU_STACK=RW`、`TEXTREL=False`、`BIND_NOW=False`、`FLAGS=0x8`、`FLAGS_1=0x1`）。
- **无法静态绕开**：本案例静态链接消费者后出现 116 条 undefined（`XftDrawChange`、`XftNameParse`、
  `FcPatternCreate` …）⇒ 库本体确实需要 Xft/fontconfig 符号。
- **系统无兜底**：`/lib`、`/lib64`、`/usr/lib`、`/system/lib64`、`/vendor/lib64` 均无 X 库。
- **设备间不可迁移假设**：CI/其它设备可能**没有**该策略（依赖可正常加载）——
  因此处置必须做成“两侧都成立”的形式（§5.1），而不是让 CI 永久跳过。

## 7. 复现与检测

```bash
# ① 直接判读既有构建日志（推荐：把 conan create 输出落文件后再跑）
python3 detect_loader_refused_map.py --log <conan-create.log> \
        --lib-path "$LD_LIBRARY_PATH"

# ② 端到端复现（在本机缓存依赖被拒时给出证据；依赖可加载时如实报“未复现”）
#    --libpath 需含依赖的**完整运行期路径**（含传递依赖目录），否则判据会如实报 missing
#    （判据的“真缺库”分支是特性：路径不全时必须报缺，不得放行）
bash reproduce.sh

# ③ 只看依赖文件本身是否可解析（不跑消费者）
python3 detect_loader_refused_map.py --probe libXft.so.2 libfontconfig.so.1
```

脚本均为纯 stdlib（`--log`/`--probe`/复现脚本用 `cc`），不写死本机绝对路径，
路径一律来自命令行参数或 `LD_LIBRARY_PATH`。

端到端实测（2026-10-04，XmHTML 1.1.10 案例）：`reproduce.sh --libpath <完整闭包>` →
最小消费者以 127 退出、判据 `present-but-refused`（**exit 0**）；
`--libpath` 不含传递依赖目录时同一脚本报 `missing`（**exit 1**，真缺库分支，不会误放行）。

## 8. 证据与关联（样例：XmHTML 1.1.10）

- 样例库：`archives/x/xmhtml/1.1.10`（Motif HTML widget；`HAVE_XFT=1` ⇒ 直接依赖
  `libxft/2.3.9` + `fontconfig/2.18.3`）。
- 构建：库与消费者编译链接全部成功（`libXmHTML.so.1.1.10` / `libXmHTML.a`），
  `DT_NEEDED` 13 项全部可解析；**仅运行期加载失败**。
- W3 处置后：`conan-verify` G0/G1/G2/G3/G4 + L2/L4/L5 全绿（本机策略分支生效、
  依赖可加载环境走严格路径）。
- 排除实验与真因链：见 `archives/x/xmhtml/1.1.10/notes.md`「本地环境限制」一节
  （含对照实验表与 musl 消息形态说明）。
- 同类历史线索：`knowledge/drafts/` 下既有条目中「loader/relocating」类问题
  （如静态全局变量引用、DT_SONAME 缺失）与本类**不同**：那些是产物自身缺陷，
  本类是设备对被依赖**已发布二进制**的映射策略。

## 9. 相关文件

| 文件 | 作用 |
| --- | --- |
| `detect_loader_refused_map.py` | 判据实现（日志/探测两模式），退出码 0/1/2 |
| `reproduce.sh` | 端到端复现脚本（构建最小消费者 + 抓取证据 + 调判据） |
| `DRAFT-xmhtml-1.1.10-ohos-loader-refused-dependency-map.{kv,md}` | 知识图谱条目（草稿） |
| `archives/x/xmhtml/1.1.10/test_package/test_xmhtml_consumer.sh` | 处置落地样例（§5.1） |
