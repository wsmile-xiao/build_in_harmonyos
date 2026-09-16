# conan-verify 补充实测 — dicom3tools 1.00-20240118131615

> 末次采信轮 SHA：`48813722e1ccb489db358f51e973a6376ced5c03`
> 补测时间：2026-09-11
> 依据：`conan-verify` 的 G4 定位失败时 L2/L4/L5 会走「无 cache 路径」
> 分支，报告里同一行同时出现 `✅ PASS` 与 `⏭️ 跳过`，**以跳过为准**，必须人工补测。
>
> 本文件记录的是**末次采信轮**上的实跑结果；此前各轮的同一组判据结果相同，
> 差异只在缓存分片目录名（见「可复现性判别」）。
>
> **分片目录名逐轮重建，本文件不把任何结论绑定到具体目录名**：一律用
> `ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/dicom*/p` 现场定位（目录名形态是
> 「包名前 5 字符 + hash」，`ls -d p/b/dicom3tools*` 必然失配）。

## 证据与 SHA 的对应关系

| 证据 | 产生于 | 说明 |
| --- | --- | --- |
| 本文件、`conan-create-evidence.md`、`conan-verify-stdout.md`、`l2-consumer-test-evidence.md` | `4881372e` | 末次清缓存 `conan-verify` 的采信轮（下方表格第 7 行，6 补丁） |
| `w3-local-ci-evidence.md` | `4881372e` | 末次 `finish` 内嵌 W3 的运行 |

`4881372e` 之后的提交只改 `reports/**` 与文档：
前三类是本地/CI 门禁物料，后一类**不参与 `conan create`**——采信轮日志的导出段只有
`Copied 1 '.yml' file: conandata.yml`、`Copied 1 '.py' file: conanfile.py`、
`Copied 5 '.patch' files` 三行，`test_package/MANIFEST.yml` 从未被导出进 recipe，
只有 CI 的 L0e（`ci/conan/build_and_test.sh:373`）读它做「上游测试来源声明」检查。
因此这些 delta 不改变任何产物字节，五轮清缓存构建的两条聚合恒定即是佐证。

## 为什么要补测

`reports/conan-verify-report.md` 原文：

```
## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
```

G4 的真实触发点是 `conan list --format=json` 的顶层键带 `@user/channel` 而 `self.ref`
不带（工具缺陷，第 17 节已登记）。`package_type = "application"` 的包内既无 `lib/`
也无 `include/`，整组命中该路径，因此拿不到任何自动 L2/L4/L5 证据。

包目录定位（分片目录名是「名前 5 字符 + hash」，必须用 glob 兜底）：

```sh
PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/dicom*/p | head -1)
```

同一 ref 的 `conan cache path` 返回的是 **export 目录**（`…/e`），拿不到产物目录，
故产物一律用上面的 glob 定位。

## G4 — 产物清单与 package_info() 互证

```sh
find "$PKG" -type f | wc -l          # → 255（含 conaninfo.txt/conanmanifest.txt）
ls "$PKG"/bin | wc -l                # → 122
ls "$PKG"/share/man/man1 | wc -l     # → 130
ls "$PKG"/licenses                   # → COPYRIGHT
test -d "$PKG"/lib ; echo $?         # → 1（不存在，与 package_info 的 libdirs=[] 一致）
test -d "$PKG"/include ; echo $?     # → 1（不存在，与 includedirs=[] 一致）
```

`bin/` 逐文件按魔数分类（判据：前 4 字节是否 `\x7fELF`、前 2 字节是否 `#!`）：

```
bin total: 122   ELF: 102   shebang 脚本: 19   既非 ELF 也非 shebang: 1
```

第 3 类的那 1 个是 `bin/himrunid`：**0 字节**、装有执行位。它并非本适配引入——
上游 tarball 里的 `appsrc/dconvert/himr/himrunid.script` 本身就是 0 字节成员
（`tar -tvjf <tarball> | grep himrunid` → 大小 0），imake 的安装规则把它改名安装为
`bin/himrunid`。为保持补丁集最小、且不改变上游行为，本包按原样安装该空文件；
它是可执行位齐全的空文件（无 shebang，执行后静默返回 0）。总计 122 / ELF 102 两个
数字不受影响，受影响的只是第 3 类的**标签**。

结论：G4 PASS。产物与 `package_info()`（`bindirs=["bin"]`、`libs=[]`、`libdirs=[]`、
`includedirs=[]`）一致，全部 122 个文件都能在清单里找到来源。

## L4 — 静态安全属性

对 `bin/` 下全部 102 个 ELF 逐个 `readelf -h/-lW/-dW`：

```sh
for f in "$PKG"/bin/*; do
  readelf -h   "$f" | grep -q "DYN"                 # PIE
  readelf -lW  "$f" | grep -q "GNU_STACK.*RW"       # 非可执行栈
  readelf -lW  "$f" | grep -q "GNU_RELRO"           # RELRO
  readelf -dW  "$f" | grep -q "BIND_NOW"            # 立即绑定
done
```

结果：

```
L4: PIE+RELRO+BIND_NOW+非执行栈 全部满足: 102 ; 不满足: 0
```

结论：L4 PASS。

## L2 — 消费者实测

脚本：`reports/l2-consumer-test.sh`；输出逐字留档：`reports/l2-consumer-test-evidence.md`。

```
$ PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/dicom*/p | head -1)
$ PATH="$PKG/bin:$PATH" bash reports/l2-consumer-test.sh
...
L2 consumer test: 36 passed, 0 failed
```

覆盖 15 个程序的真实业务行为：版本自检、`dcsmpte` 生成 256×256 带像素的 Part 10
文件、`dcdump` 解析出 41 个属性、`dcstats` 统计像素值、`dciodvfy` 校验、
`dcdict`/`dckey` 字典解析、四种像素导出（`dctopnm`/`dctoraw`/`dctopgm8`/`dctopgx`）、
三条像素导入回环（`pnmtodc`/`pgxtodc`/`rawtodc`）、`dccp` 属性替换且不改写输入、
坏输入与截断数据集被拒绝。

### 两条断言在首轮写错，已按工具真实设计修正

补测的价值正在于此——两条失败都不是产物缺陷：

1. **`dcstats` 不输出模块属性**。首轮断言查 `Rows|Columns`，实际它输出的是像素值统计
   （`Unsigned mean = 0x86 (134 dec) (52.549%)`、`Bits Stored = 8`）。改为断言统计行。
2. **`dcdump` 对纯文本返回 0**。首轮把「退出码非 0」当作拒绝坏输入的判据，但 `dcdump`
   按设计支持**没有 Part 10 头的旧格式**，会做字节序与 VR 自动识别，把任意字节流当隐式
   VR 数据集打印出来：

   ```
   $ printf 'this is not a dicom file at all\n' > bad.dcm
   $ dcdump bad.dcm ; echo $?
   (0x6874,0x7369)  ? 	 VR=<UN>   VL=<0x20736920>  [...]
   0
   ```

   `0x6874,0x7369` 就是 "th"/"is" 的小端读法。这是上游设计行为而非缺陷，故判据改用
   结构校验器 `dciodvfy`（同一文件 rc=1）。这条与 workflow §7.3「判定失败以退出码为准，
   上游自打印的诊断行不作为失败证据」互为镜像：**退出码为 0 也不等于工具没按设计做事**。

## L5 — 产物基线与可复现性

### 稳定聚合口径

`conanmanifest.txt` 首行是打包时间戳，含它的全包聚合每轮必然漂移，故排除；聚合在包目录
内用**相对路径**（分片目录名每轮重建，带绝对路径的写法必然漂移）：

```sh
cd "$PKG" && find . -type f ! -name conanmanifest.txt ! -name conaninfo.txt \
  | sed 's|^\./||' | sort | xargs sha256sum | sha256sum
cd "$PKG/bin" && find . -type f | sed 's|^\./||' | sort | xargs sha256sum | sha256sum
```

### 可复现性判别（七轮清缓存构建）

每轮都先执行清缓存四步（限 ref、裸 ref、分片目录、DB 两表回查为空），
并核对本轮 `reports/conan-create.log` 含 `RUN: make`（5 处）与 5 条 `Apply patch`，
确认是干净轮而非缓存轮。

| 轮次 | 提交 | 包内容聚合 | bin 聚合 |
| --- | --- | --- | --- |
| 第 1 轮（清缓存） | `586b8af8` | `023d06b3316d020419f9bc8125edd8cd2ead9cb4fd564a6eca67a4da271f93fe` | `424320e0be30b4aad8fe7330d23912440f553ede6674ebd8ebc7f40e5a79d20b` |
| 第 2 轮（清缓存） | `586b8af8` | `023d06b3316d020419f9bc8125edd8cd2ead9cb4fd564a6eca67a4da271f93fe` | `424320e0be30b4aad8fe7330d23912440f553ede6674ebd8ebc7f40e5a79d20b` |
| 第 3 轮（清缓存） | `440b45b5` | `023d06b3316d020419f9bc8125edd8cd2ead9cb4fd564a6eca67a4da271f93fe` | `424320e0be30b4aad8fe7330d23912440f553ede6674ebd8ebc7f40e5a79d20b` |
| 第 4 轮（清缓存） | `5dcb2924` | `023d06b3316d020419f9bc8125edd8cd2ead9cb4fd564a6eca67a4da271f93fe` | `424320e0be30b4aad8fe7330d23912440f553ede6674ebd8ebc7f40e5a79d20b` |
| 第 5 轮（清缓存） | `1453db5e` | `023d06b3316d020419f9bc8125edd8cd2ead9cb4fd564a6eca67a4da271f93fe` | `424320e0be30b4aad8fe7330d23912440f553ede6674ebd8ebc7f40e5a79d20b` |
| 第 6 轮（清缓存） | `5120a24f` | `023d06b3316d020419f9bc8125edd8cd2ead9cb4fd564a6eca67a4da271f93fe` | `424320e0be30b4aad8fe7330d23912440f553ede6674ebd8ebc7f40e5a79d20b` |
| 第 7 轮（清缓存，**末次采信轮**，含 6 补丁） | `4881372e` | `023d06b3316d020419f9bc8125edd8cd2ead9cb4fd564a6eca67a4da271f93fe` | `424320e0be30b4aad8fe7330d23912440f553ede6674ebd8ebc7f40e5a79d20b` |

**七轮逐字节一致，无差异项**——第 7 轮加入了 `0006-portable-userland-command-syntax.patch`
（只改 sort/xargs 的调用语法，不改编译输入），产物聚合仍与历轮完全相同，
这同时证明了该补丁对产物**零影响**。

三次 SHA 变更的性质各自不同，恰好构成三条独立佐证：

- 第 3 轮相对前两轮只改了 `package_info()` 的 `libdirs`/`includedirs` 声明与文档，
  不参与编译 → 产物哈希不变（配方元数据变更未影响二进制）；
- 第 4、5 两轮只改了 `test_package/**`、`manifest.yaml`、`notes.md`、`README.md`
  与 `reports/**` 等文档/测试侧内容，既不改编译输入也不改打包逻辑 → 产物哈希同样不变；
- 七轮的分片目录名互不相同（每轮清缓存后重建），而产物哈希恒定 →
  二进制内**不含构建路径**。

抽样单产物在七轮中同样一致：

```
dcdump    d711eb104f8deaa2f4556f2d0839cdb8847068c240a3de385d1563d17b2c08fc
dciodvfy  1df2f72638fe634a4c1a4d5e237a3a764ec048ff2be6ed376d29e18f2dd72576
dccreate  659f5d341c5e6572b144b4fcf1a4779aa4690cc124ce763f43b4dcc35d1539c1
dcsmpte   9e3318ed74db87d7427220a0f8a9ce34c0f2659a94b20ca78b0bcb659e81e0ee
dctopnm   c98e0baa5fc7cb28ec022a2e3c3c17d9be2721e1914c4c15cc0e61cf49fe1499
```

末次采信轮另外逐项比对了两条聚合与 `reports/l5-artifacts.sha256`：
`bin/` 下 122 个文件的逐产物 sha256 清单与第 2 轮采集的基线 `diff` **无输出**。

七轮的 `linked 102 programs` 与 `test_package: 22 passed, 0 failed` 也相同。

### 上游本可导致不可复现的两个来源，本包均不命中

- 上游 `dcdump` 等程序在 `-version` 输出里内嵌 `__DATE__`/`__TIME__` 与构建机
  平台串（例如 `dicom3tools Platform: Darwin ...`）。**这是运行期输出，不写入二进制**，
  因此不影响产物 sha256；七轮实测一致即为佐证。
- 上游 Makefile 未固定 `-g`，`DW_AT_comp_dir` 不会写入每轮不同的缓存构建目录
  （七轮分片目录名互不相同而产物哈希相同，说明二进制内不含构建路径）。

### 基线

以上两条聚合即本包在末次采信轮 SHA `48813722e1ccb489db358f51e973a6376ced5c03`
下的 L5 基线（与第 2 轮采集的基线完全相同）；
`bin/` 下 122 个文件的逐产物 sha256 清单见 `reports/l5-artifacts.sha256`；
包内另有 `share/man/man1` 130 个手册页与 1 个许可证文件（共 255 个文件），
它们不参与可复现性比对（内容由同一轮 `make install.man` 生成，两轮 `diff -r` 亦无差异）。
