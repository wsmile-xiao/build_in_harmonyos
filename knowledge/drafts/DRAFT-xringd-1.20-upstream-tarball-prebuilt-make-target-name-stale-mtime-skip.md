# 上游老 tarball 自带"与 make 目标同名"的预编译件：make 会不会真编译取决于陈旧 mtime 的先后

- 草稿 ID：`DRAFT-XRINGD-1.20-UPSTREAM-TARBALL-PREBUILT-MAKE-TARGET-NAME-STALE-MTIME-SKIP`
- 触发实例：xringd 1.20（任务 12186，构建主机 B，2026-09-27）
- 关联 Issue：#3505
- 门禁面：W3 `conan create`（build/package）、G2、L 系列产物一致性

## 一句话

199x 年的发布 tarball 常把**当时编好的可执行件**和源码一起打包，且这些可执行件的**文件名正好等于 Makefile 的目标名**；
解包后目标件与源件的 mtime 都被还原成同一年，`make` 依"目标不比源新就跳过"的规则**是否真编译取决于时间戳先后**
（本包 `uartcount: uartcount.c` 是直接源规则、随包件 1997-07-09 07:14 比源文件 1996-01-17 08:02 新 ⇒ **必然跳过**；`xringd: $(OBJ)` 是链接型、包内无任何 `.o` ⇒ **必然重编**）。⚠ 至今没有 `is up to date` 的日志读数，跳过结论由规则形态推出。配方必须在 `make` 之前显式清除这些同名件，否则会把**外来架构的二进制当成交付物**，
而 `make` 退出码照样是 0、W3 与 CI 全绿。

## 一手证据（xringd 1.20）

| 读数 | 实测值 |
|------|--------|
| 官方发布点 | `https://www.ibiblio.org/pub/linux/system/network/daemons/xringd-1.20.tgz` |
| HTTP | `200`，`size=31787`，`last-modified: Mon, 21 Jul 1997 22:27:32 GMT` |
| 上游自述（包内 `xringd-1.20.lsm`） | `Source and an aout bin are included` |
| `file` 包内 `xringd` / `uartcount` | `ELF executable, 32-bit LSB 386, dynamic (/lib/ld-linux.so.1), stripped` |
| 与 make 的关系 | 两者都是 Makefile 的目标名 ⇒ 命中"同名目标"条件 |
| 处置 | 配方 `build()` 在 `make` 前 `os.remove` 这两枚 1997 年件 |
| 交付复验 | 消费者测试用 `elf_machine()` 读 ELF 头机器码字段断言交付件**不是** 386 |

## 根因链

1. 那个年代的作者直接把本地编好的二进制塞进发布归档（后来 `make dist` 惯例才把二进制剔掉）。
2. `tar` 解包还原归档里的时间戳 ⇒ 预编译件与源件同为 1997 年。
3. `make` 的判定是纯时间戳比较，不比内容、不比架构 ⇒ 谁"看起来更新"完全取决于打包/解包时的顺序细节。
4. 一旦跳过编译，`build()` 没有失败信号；`package()` 把 386 ELF 拷进 `bin/`，交付给 aarch64 平台。
5. 故障面被推迟到运行期（`Exec format error` / 找不到 `/lib/ld-linux.so.1`），
   极易被误判成"OHOS 工具链/平台能力问题"，甚至把一个本可修的包错转成"平台不可行"。

## 处方（推荐）

`build()` 内、`make` **之前**显式删除与目标同名的上游预编译件，并把被删件的 `file` 原文读数留在 notes（可复核，
⛔ 只写"已清理"）。

```python
# conanfile.py build() 片段（xringd 1.20 实物）
for stale in ("xringd", "uartcount"):
    p = os.path.join(self.source_folder, stale)
    if os.path.isfile(p):
        os.remove(p)   # 上游 1997 年随包带的 32-bit 386 预编译件
self.run("make")
```

### 备选（不便删除时）

用 `make -B`（或 `make clean && make`）强制绕开时间戳判定；收口仍要 `file`/`od -c -N 16` 复验产物架构，
⛔ 只看退出码。

## 禁止做法

| 反模式 | 为什么危险 |
|--------|------------|
| 直接 `make` 并以退出码判成功 | 跳过编译时退出码仍是 0，故障推迟到运行期 |
| 靠"我这台机编出来了"外推成通用结论 | 结论绑定的是本机解包顺序与时间戳，他机不可复推 |
| 只在 notes 写"已清理陈旧件" | 没有 `file`/`od` 读数，接手人无法复核被删的到底是什么 |

## 判据三步（可直接搬到别的包）

```sh
find <解包目录> -type f ! -name '*.*'          # 无扩展名件（只能出题，不能定案）
file <候选件> && od -c -N 16 <候选件>          # 魔数与架构字节才定案
grep -nE '^(<目标名>)[[:space:]]*:' Makefile   # 是否与 make 目标同名
```

## 适用范围与反例

- **适用**：上游发布物为 199x 年 tar/tgz、包内自带与构建目标同名可执行件的包（带 `.lsm` 自述 `include bin` 的那批尤甚）。
- **不适用**：①预编译件与目标不同名（make 必然重编）；②现代 `make dist` 纯源码归档；
  ③已 `make -B`/`clean` 强制重编的场景（清除虽非必需，仍建议清以免 package 误拷贝）。
- ⚠ 判型纪律：`find ! -name '*.*'` 只能**出题**不能**定案**——同批次另一包里，无扩展名的
  `src/convert/vcard2pal` 实测是 2024B 的 awk 脚本而非 ELF。判类型必须落到 `file` + `od -c -N 16` 的读数。

## 与既有条目的差异化

| 条目 | 因 | 处方 | 与本条关系 |
|------|----|------|------------|
| `DRAFT-conan-downloader-xgzip-content-encoding`（基线已入库） | 站点把已 gzip 的 `.tgz` 又声明 `Content-Encoding: x-gzip` ⇒ 下载通道透明解压 | `source()` 走 urllib 原始字节回退 | 同包另一面，取源阶段，与本条（构建/打包阶段）不同因不同处方 |
| `knowledge/graph/E485`（串口/设备节点缺失家族） | 运行期 `/dev/*` 节点不存在 | 如实申报不可行 | 只在运行面相关，不覆盖"预编译件冒充产物" |
| `knowledge/drafts/E429-draft-BCF5.kv` L42/L50 | 补丁使随包**生成文件** mtime 变新 ⇒ make 多跑一次重生成 doc | make 前刷新 mtime | 反方向（多做 vs 少做），处方相反 |
| `knowledge/drafts/E479-draft-5CC4.md` L98 | 目标不依赖 CFLAGS ⇒ make 报 `up to date` 静默复用**自己上次**编的产物 | `rm -f` 目标再 make | 复用主体是自己产物 vs 上游随包件；成因与签名不同 |
| `knowledge/drafts/E549-draft-7554.kv` L36/L50 | m4 再生产物需用 `os.utime` 钉同一时间戳 | 主动钉时间戳 | 目的是让 make 别多做，与本条让 make 必做相反 |

## 检索依据（判 create 的全树重扫）

W4 独立审计棒整仓扫 `knowledge/` 4039 件 + 本仓通用池 24 稿，对"上游 tarball 自带与 make 目标同名的预编译件 ⇒
陈旧 mtime 使 make 跳过真实编译 ⇒ 外来架构二进制被当交付物"这一机制 **on-point 命中 0**，故升独立条目。
