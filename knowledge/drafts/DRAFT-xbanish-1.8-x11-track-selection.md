# DRAFT — X11 客户端包的 libx11 双轨选轨判据（含 libXi 即锁 6.4.0 轨）

- **包 / 版本**：xbanish 1.8（任务号 12042）
- **阶段**：W0 依赖解析（`conan install` 图解析），不是编译或链接期
- **日期**：2026-09-23

## 症状

给一个 X11 客户端包写 `requirements()` 时，把制品仓里"看起来是最新"的 X11 扩展库版本一起挂上，
conan 在**图解析阶段**就报：

```
ERROR: Version conflict: Conflict between libx11/6.4.0 and libx11/1.8.13 in the dependency graph.
Conflict originates from libxi/6.1.0
```

现象上有两个地方特别容易走错方向：

1. 它不是编译错误，也不是"依赖没发布"——`libxi/6.1.0`、`libx11/1.8.13` 单独都要得到配方与
   OHOS 二进制，`--only-recipe` 与精确 `--build=never` 都能命中，于是很容易被误判成依赖缺失；
2. 报文只说"结果冲突"，不说"是谁把 libx11 钉到了另一轨"，所以没人能从报错本身推出选轨依据。

## 根因

制品仓的 X11 客户端库是分两批发布的，形成两条互斥的 libx11 版本线：

- **Track A**：以 `libx11/1.8.13` 为头；
- **Track B**：以 cmd-pkgs 侧 `libx11/6.4.0` 为头。

部分 X11 子库的**已发布配方**在自己的 `requirements` 里把 libx11 钉死在其中一轨。实测：
`libXi` 的两个归档版本（`1.8.3` 与 `6.1.0`）**都钉 `libx11/6.4.0`** ⇒ 硬链接含 `-lXi` 的包
整体落 Track B；`libXt` 则相反，`libxt/1.3.1` 的配方**直接 `requires("libx11/1.8.13")`**
⇒ 硬链接含 `-lXt` 的包整体落 Track A。**钉轨方向因子库而异，禁止由一个子库推广到其它
子库**；`libXtst` 暂无实测，遇到时按验证命令现测。

## 为什么现有条目不够用

- **E480** 解决的是"同轨可用时，头文件级依赖直接用 `transitive_headers=True` 消费，不必写桩
  `.pc`、不必 vendor 头"。它明确写到"跨轨才会同图双 libx11 冲突，才需 **E338** 方案"——
  但 **E338 实际是 `OHOS getpwuid() 返回 NULL 导致 homedir() 为 NULL，程序启动 SIGSEGV`**，
  与 X11 完全无关。也就是说 E480 把跨轨情形指向了一个不存在的方案，后来者按图索骥必然落空。
- **E346** 的对象是"X11 子库**自身**在 configure 期需要拉不进图的 pkg-config 模块时怎么办"
  （用桩 `.pc` + vendor 头），是子库作者视角，不是消费方视角。
- 全库检索 `选轨` / `必须 6.4.0` / `只能 6.4.0` **零命中**。

后果已经在今晚显现：同一族包，一条线（dmenu）实测按 `1.8.13` 组，另一条线（xbanish、slock）
按 `6.4.0` 组，两个窗口互不知情、结论相反——因为它们都没有判据，只有各自的试错结果。

## 最小复现与判据（推荐做法）

判据只有一条：**跑一次只读组图，让报文自己点名钉轨者**。

```bash
# 复现冲突并读出钉轨者（报文尾部 originates from 即答案）
conan install --requires=libxt/1.3.1 --requires=libxi/6.1.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 --build=never

# 锁定 Track B 后整链试组，RC=0 才算选轨成立
conan install --requires=libx11/6.4.0 --requires=libxfixes/6.1.0 \
  --requires=libxi/6.1.0 --requires=libxext/6.4.0 --requires=xorgproto/2025.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 --build=never
```

xbanish 1.8 实测：第一条 RC=1 并点名 `libxi/6.1.0`；第二条按 Track B 取全集后
`RC=0`，连同传递依赖（`libxau` / `libxcb` / `libxdmcp` / `xtrans`）共 9 个 OHOS 二进制命中，
`preflight_check.sh xbanish/1.8` 由配方解析出 5 个依赖后 **RC=0**。

规则化表述：

1. 取硬链接集合（上游 Makefile / configure 里的 `-l...`），对照已实测钉轨子库表
   （libXi⇒Track B、libXt⇒Track A；不在表内的子库先按验证命令现测并补表）；
2. 按命中的钉轨者把整条 X11 依赖链锁到同一轨；未命中任何钉轨者 ⇒ 可按 E480 在同轨内消费；
3. 写进 `requirements()` 之前必须已有 `RC=0` 的组图证据，**不许按包名或版本号大小猜轨道，
   也不许由一个子库的钉轨方向推广其它子库**；
4. 两轨都组不出（本包同时需要钉不同轨的两个子库）⇒ **不要改他人已发布配方**，
   按 AGENTS §6 把钉轨者作为上游行 `block` 转手。

## 已试过的失败方向

- 顺着 E480 的指引去读 E338 找跨轨方案 —— 该条目是 `getpwuid` 段错误，方向完全不相干。
- 只把冲突一侧的版本号改成另一侧的最新版 —— 图里仍是两条轨同时存在，冲突照旧，
  因为钉轨者不是消费方指定的那个版本，而是被引入子库自己的 `requirements`。

## 适用边界

- 适用：任何硬链接 `libXi` / `libXt` / `libXtst` 或多个 X11 扩展库的客户端包
  （锁屏、屏保、窗口管理、剪贴板、截屏类工具最常见）。
- 不适用：纯 XCB 栈的包（无 `-lX11`/`-lXi`，走 E480 同轨 `transitive_headers`）；
  以及"要修的是 X11 子库自身构建"的情形（走 E346）。
- 时效性：一旦制品仓把两轨收敛成单轨（或某个子库补发跨轨版本），本判据的"含 libXi 即锁
  6.4.0"会失效；但**"用只读组图的 `originates from` 找钉轨者"这个判据方法本身不变**，
  所以优先记方法、把具体版本号作为当期事实附在后面。

## 关联知识缺陷（不在本 PR 内修）

E480 → E338、E346 → E347 两处跨引均为错链（E347 实为 GitLab 418 反爬拦截）。
按"知识库/框架改动单独 PR"的规矩，本窗只做上报与就地绕开，不擅自改 `knowledge/`。
