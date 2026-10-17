# E565 — 交付产物与上游测试靶向文件不一致时的验证盲区（单文件/amalgamation 类包）

## 错误特征

没有任何错误行。发布流程全绿，但「全绿」覆盖的不是被安装的那个文件：

```
# conan create 日志
wuffs/0.4.0-alpha.10@ohpcd/stable: package(): Packaged 1 '.c' file: wuffs-v0.4.c
wuffs/0.4.0-alpha.10@ohpcd/stable: upstream C tests: 30 programs, 232 test cases, all PASS

# 但若照抄上游测试的 include，测试实际编译的是另一个文件：
$ grep -h 'release/c/' test/c/std/*.c | sort -u
#include "../../../release/c/wuffs-unsupported-snapshot.c"   # 未版本化快照，本包不安装
```

典型伴随信号：

- 交付物自报的版本/身份宏与包版本不符（wuffs 快照的 `WUFFS_VERSION` 恒为 `0`：
  `#define WUFFS_VERSION 0` + `"¡ Some code generation programs can override
  WUFFS_VERSION."`），而库的 `initialize` 会比对 `WUFFS_VERSION`，测试语义随之错位。
- 交付目录与测试目录分别指向同名但内容不同的两个文件（`wuffs-v0.4.c`
  3 625 906 B / `wuffs-unsupported-snapshot.c` 3 625 807 B，`diff` 只有版本宏几行；
  同目录的 `wuffs-v0.3.c` 才是 1 825 612 B——抄错大小的坑见下方注意事项）。
- `conan create` 的 sha256 校验、G1 配方完整性检查、L0g 全部通过——因为
  **没有任何门禁比对「测试编译的文件」与「package() 安装的文件」**。

## 触发条件

- 构建系统：任意（本条目实测于 Conan + 无构建系统的单文件 C 库；同类形态见
  单文件/amalgamation 产物、生成器产出的 `.c`/`.h`、只交付仓库子集的包）
- 阶段：build / test / package —— 假绿在 test 阶段产生，在 package 阶段落地
- 高发对象：
  - 上游把**生成产物随源码树检入**，同时保留一份「开发期快照」（`*-snapshot.*`、
    `*-unstable.*`、nightly 分支产物）
  - 上游测试套件靶向快照/开发副本，发布产物由 CI 在别处另行生成
  - 交付物是仓库的一个子集（只装一个 amalgamation 文件、只装 `release/` 目录）

## 根因分析

上游的测试套件与交付产物是两条独立演化的线：

1. **测试面向开发**：为了让开发者拿到最新代码，测试 include 的是「随开发滚动的
   那个文件」（快照、未版本化产物、或生成器就地输出）。
2. **交付面向消费者**：`package()` 只搬运一个版本化、受支持的文件。

配方照抄上游测试命令时，就把第 1 条线当成了第 2 条线的证据。此时：

- 编译警告、`-Werror`、sha256、配方结构门禁**都不会报错**——它们检查的是
  「配方是否合法」「源码是否完整」，不是「测试是否覆盖了交付物」。
- `N 个用例全过` 的 N 是真实执行的用例数，但**被执行的代码不是被安装的代码**。
  这比直接漏跑测试更危险：漏跑是显式的 SKIP，而这里是「真诚地报告了一个
  与被测对象无关的数字」。

只有把「交付物的身份」带进测试断言，才可能暴露这个缺口。

## 解决方案

### 推荐方案

两步，缺一不可：

**（一）把包内上游测试的靶向文件改指到实际交付产物。**

只改测试的 include/引用行，不改任何断言、黄金值或数据。wuffs 实测：30 个补丁
每个只有 `+1/-1`：

```diff
--- a/test/c/std/png.c
+++ b/test/c/std/png.c
@@
-#include "../../../release/c/wuffs-unsupported-snapshot.c"
+#include "../../../release/c/wuffs-v0.4.c"
```

补丁应用必须走 **Conan 实际执行的同一条路径**（patch_ng 库调用），不能只看
CLI `patch` 的退出码——两者对同一补丁的成功/失败并不总是一致（同族先例：
整文件替换补丁在 patch_ng 下落 0 字节文件而 CLI 报成功）：

```bash
python3 - <<'EOF'
import glob, patch_ng
for f in sorted(glob.glob("patches/*.patch")):
    assert patch_ng.fromfile(f).apply(strip=1, root="<pristine-tree>"), f
EOF
diff -rq "<patched-tree>" "<exploration-tree>"   # 期望无输出
```

**（二）在 test_package 消费者里断言被安装产物自报的身份/版本。**

让「装错文件」变成硬失败：

```c
#include <wuffs/wuffs-v0.4.c>
check_u32((uint32_t)WUFFS_VERSION, 0x000040000u, "WUFFS_VERSION");
check(strncmp(WUFFS_VERSION_STRING, "0.4.0-alpha.10", 14) == 0,
      "WUFFS_VERSION_STRING starts with 0.4.0-alpha.10");
```

同时用**独立算出的**已知答案（不是从某次本库构建回读）验证真实功能：wuffs
实测内嵌 4×4 PNG、像素图案先验已知，期望 `crc32(解码 RGB)=0x6B64E606`、
`adler32=0x3A8710A1` 由 Python `binascii`/`zlib` 独立算出。这样字节序、对齐、
NEON 代码路径的差异都会暴露为哈希不符，而不是被自证。

### 禁止做法

- ❌ 把「上游 N 个用例全过」直接当作被安装产物的验证证据。
- ❌ 只写一句「上游测试通过」而不声明测试编译的是哪个文件。
- ❌ 为了消除不一致而**两边都装**（把快照也塞进包）——那会把上游明确标注
  `unsupported`/未版本化的文件变成交付契约的一部分。
- ❌ 用 `-D` 宏或包装头把快照「伪装」成版本化产物。

## 验证

```bash
# 1. 交付物清单与测试引用是否一致
grep -rn 'release/c/' test/c/std/*.c | grep -c 'snapshot'   # 期望 0
# 2. 补丁真实走 patch_ng 且结果与探索树逐字节一致
patch_ng.fromfile(f).apply(strip=1, root=tree)  # 全部 True
diff -rq <patched-tree> <exploration-tree>      # 无输出
# 3. 消费者侧身份断言
./test_wuffs   # OK: 15 checks passed, 0 failed（含 WUFFS_VERSION / VERSION_STRING 断言）
# 4. 上游测试真实执行的证据（计数 > 0 且与 MANIFEST 声明一致）
grep 'upstream C tests:' conan-create.log
#   → upstream C tests: 30 programs, 232 test cases, all PASS
```

## 适用范围与安全边界

适用于**交付物 ≠ 上游测试靶向文件**的包：单文件/amalgamation 产物、生成器产出、
只交付仓库子集的包。

不适用于：上游测试本就针对所交付文件；交付物即整棵源码树；交付物是上游测试
从未触及的纯数据/头文件集合（那属于「上游无测试」，走 MANIFEST 声明的
补全测试路径）。

边界要求：

- 改向只允许动引用行；断言、黄金数据、用例集合必须保持上游原样，改动范围与
  原因要写进 PR 的「上游测试用例修改说明」。
- 不得用改向掩盖真实不兼容：若交付产物在 OHOS 上确实编不过或测不过，那是另一
  类问题，不能靠改回快照「解决」。
- 上游默认不编译的用例（`#ifdef` 关闭）既不是 PASS 也不是 skip，须在
  MANIFEST.yml 单列说明（wuffs 实测：用 `clang -E` 真实预处理解析 `g_tests[]`，
  `-DWUFFS_MIMIC` 定义时共 **295** 个元素，其中宏内 **63** 个既不编译也不执行，
  未定义该宏的默认口径为 **232**）。
- **静态计数的取数陷阱（本条目实测踩过并因此被审计判 P0）**：
  1. 用正则直接扫源码、以非贪婪方式删除 `#ifdef ... #endif` 块，会误删大量
     非 mock/mimic 区域，得到偏小的假总数（wuffs 实测误得 242，真值 295）；
  2. `clang -E` 的输出含 `# <line> "<file>"` linemarker，按逗号切分初始器时
     不滤掉以 `#` 开头的行，会在实际触发该合并的 10 个文件上各多计 1
   （`g_tests[]` 内含 `#ifdef` 分支的文件共 28 个，其中 10 个命中）
   （`#endif` 回填的 linemarker 与末尾 `NULL` 哨兵落进同一逗号片段），
   实测误得 242，真值 232；另注意整文件带 `-DWUFFS_MIMIC` 预处理会因缺第三方
   头文件失败，须先取出 `g_tests[]` 块再预处理。
  两条陷阱叠加后「总数」与「默认口径」都错，且错得互相自洽（232+10=242），
  极易蒙过自查——**计数必须与真实执行日志逐文件对账**（本包 30/30 吻合）。

## 关联条目

- 相关: E276 / E392 / E483（Conan `get()` 对 codeload URL 选错解压器——同一任务
  中遇到的另一类「验证通过但产物不对」问题）
- 相关: E543（改变结构体布局的特性宏必须经 `cpp_info.defines` 下发——同属
  「交付物与消费者假设不一致」的家族）
