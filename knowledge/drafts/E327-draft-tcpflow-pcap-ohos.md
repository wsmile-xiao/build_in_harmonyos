# E327 — pcap 取证 CLI（tcpflow 类）在 OHOS 上的 submodule 缺源合并、DFXML 报告 getpwuid 空指针 SIGSEGV 修复与离线 pcap 无损消费者测试

> 本条目为 draft（草稿），触发事件：tcpflow 1.6.1 适配 HarmonyOS PC（Issue #2180，路径 B）。
> 结构化数据见同目录 `E327-draft-tcpflow-pcap-ohos.kv`。

## 错误特征（symptom）

在 OHOS PC 环境（CI / test_package / 赛事真机）适配 tcpflow 1.6.1 类
pcap 取证 CLI 时，按官方 release tarball 依次出现三个独立问题：

```
# 1) 构建期：官方 tarball 不含 submodule 内容
make[2]: *** No rule to make target 'http-parser/http_parser.c', needed by 'tcpflow-tcpdemux.o'
# 2) 自举期：GitHub archive tarball 无 configure，bootstrap 需要 automake
tcpflow bootstrap: be sure to run the appropriate CONFIGURE script
# 3) 运行期：默认生成 report.xml 时崩溃（精确截断于 <uid> 之后）
reportfilename: out/report.xml
<uid>20020084</uid>      ← report.xml 最后一个元素
Signal 11 (core dumped)  # exit 139
```

- 修复 submodule 与自举后，默认运行 `tcpflow -r xxx.pcap` 仍稳定 SIGSEGV；
  `-S enable_report=false` 时核心离线工作流完全正常（流文件 md5/size/mtime
  与上游 tests/test1.sh 断言逐字节一致）。

## 触发条件

- 构建系统: autotools（configure.ac + Makefile.am + bootstrap.sh）
- 上游: simsong/tcpflow 1.6.1（C++，GPL-3.0）
- 阶段: compilation / configuration / runtime / testing

## 机制区分（三个独立机制，勿混写）

### 机制 1：源码分发缺失（submodule 缺源）— 源码获取层

`.gitmodules` 声明 `src/http-parser`（simsong/http-parser），官方 GitHub
release tarball 中该目录为空（0 文件）；`src/Makefile.am` 引用
`http-parser/http_parser.c` → make 必失败。与 E150（manual-download）同族，
但此处用 conandata `sources.submodules` 段配方化解决。

### 机制 2：自举缺失（GitHub archive 无 configure）— 构建系统层

GitHub archive tarball 不含预生成 configure（autoreconf 产物不进版本库）；
bootstrap.sh 需要 automake/autoconf/libtool，环境缺 automake 时直接退出
（E116 相关）。`build()` 检测 configure 缺失时 `autotools.autoreconf()` 自举。

### 机制 3：运行期 getpwuid 空指针 SIGSEGV（本条目核心新增）— 运行期平台交互层

**精确根因**：`src/be13_api/dfxml/src/dfxml_writer.cpp:476`：

```cpp
xmlout("username",getpwuid(getuid())->pw_name);
```

`add_DFXML_execution_environment()` 默认生成 report.xml（DFXML）时执行该行。
当进程 uid 在 `/etc/passwd` 无条目（OHOS 容器/CI 常见）时，`getpwuid()` 返回
NULL，`->pw_name` 空指针解引用 → SIGSEGV。

**证据链（三重闭合）**：
1. **截断点**：report.xml 精确截断在 `<uid>20020084</uid>`（第 475 行输出、
   第 476 行执行前），`<username>` 从未写出；
2. **最小复现**：独立 C 程序 `getpwuid(20020084)` 返回 NULL（errno=0，
   `/etc/passwd` 无该 uid）；
3. **Debug 构建**：ASan Debug 构建（-g -O0 -fsanitize=address）在完全相同
   位置崩溃（Signal 11），报告路径一致。

**上游状态**：上游 main 分支（2026-08 核查）476 行与 1.6.1 **完全相同**，
未修复该空指针。上游 commit `c125d859db7d`（2024-06-17，PR #260）
"Disable report.xml when run it with `-c`" 只是在 `-c`（console）模式加
`opt_enable_report = false`，是**纯默认值/行为调整，不是崩溃修复**，且不能
解决默认模式崩溃。因此最小修复为**上游未提供的 getpwuid NULL 保护补丁**
（bugfix 补丁，非 backport 上游已有修复）。

## 修复方案 vs 临时规避方案

### 修复方案（本适配采用，推荐复用）

补丁 `patches/0001-dfxml-writer-getpwuid-null-guard.patch`：

```diff
--- a/src/be13_api/dfxml/src/dfxml_writer.cpp
+++ b/src/be13_api/dfxml/src/dfxml_writer.cpp
@@ -473,7 +473,10 @@
 #ifdef HAVE_GETUID
     xmlprintf("uid","","%d",getuid());
 #ifdef HAVE_GETPWUID
-    xmlout("username",getpwuid(getuid())->pw_name);
+    struct passwd *pw = getpwuid(getuid());
+    if(pw != 0){
+        xmlout("username",pw->pw_name);
+    }
 #endif
 #endif
```

- 最小（1 处）、可重放（`patch --dry-run -p1` 通过）、幂等；
- 修复后**默认 report.xml 正常生成**（完整含 `</dfxml>`），用户无需任何配置；
- 不改动生产网络/抓包语义。

### 临时规避方案（仅当无法打补丁时）

把 report.xml 视为 optional feature（configure.ac 中 cairo/netviz 可
`--enable-cairo=false` 关闭；报告仅附加元数据，核心流重组不受影响），测试
驱动用 `-S enable_report=false` 显式关闭，并说明启用边界：默认开启、无
passwd 条目环境需显式关闭或修复。**此方案不解决根因，不得作为已修复宣称。**

## 解决方案（完整）

1. **submodule 合并**：conandata.yml `sources.submodules` 段声明固定 commit
   源码包（url + sha256），`source()` 中
   `get(url=..., sha256=..., strip_root=True, destination=src/http-parser)` 合并；
2. **autoreconf 自举**：`build_requirements()` 声明
   `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`；
   `build()` 检测 configure 缺失时 `autotools.autoreconf()`；
3. **getpwuid NULL 保护补丁**（见上）；
4. **无损消费者测试**：test_package 用上游 test1.pcap 夹具真实执行
   `tcpflow -o <out> -r test1.pcap`（默认报告，验证修复），对 4 个流文件断言
   md5+size+mtime(2008) 与上游 tests/test1.sh t=1 分支完全一致
   （passed=20 failed=0，case_count=4，assertion_count=20）。夹具 test1.pcap
   由配方 package() 从上游源码复制到包内 test/fixtures/（SHA256
   41cc8c96a2502fd6adb5f4498950264f79f7cbb19afc02e094c5105b32b19668，7047 字节），
   test_package 经 package_folder 定位，不携带二进制进入 PR diff（避免 GitCode
   PR .diff 缺失二进制数据导致 CI checkout-pr 阶段 git apply 失败）。

### 禁止做法

- ❌ 为测试加入运行时 mock 后门 / 隐藏环境变量（getenv 开关）——生产语义必须真实；
- ❌ test_package 使用 `self.run("true")` / 空壳脚本 / 只检查文件存在；
- ❌ 测试驱动实时抓包（pcap_open_live）、修改真实网络配置、捕获用户流量、
  长期占用端口、以 root 运行。

## 验证

```bash
# 1) submodule 合并后源码完整性
test -f src/http-parser/http_parser.c && test -f src/http-parser/http_parser.h
# 2) 补丁可重放
patch --dry-run -p1 < patches/0001-dfxml-writer-getpwuid-null-guard.patch
# 3) 修复前崩溃可复现（历史证据）：
tcpflow -o out -r test1.pcap        # Signal 11 (exit 139)，report.xml 截断于 <uid>
# 4) 修复后默认工作流正常：
tcpflow -o out -r test1.pcap        # exit 0，report.xml 完整含 </dfxml>
# 5) 消费者测试
python3 test_package/test_tcpflow.py <tcpflow-bin> <test1.pcap>
# RESULT: passed=20 failed=0 (case_count=4, assertion_count=20)
# 6) 上游测试入口
make check  # 5 节点审计后分类 total=5, passed=1, failed=1, skipped=3：
            # test1 PASS（真实通过）、test-pdfs FAIL（optional netviz/cairo 关闭）、
            # multifile/iptree/chroot 缺外部夹具 exit 0（实质 skipped，非真实 passed）
```

## 适用范围 / 失败边界

- **applicable_when**：官方 release tarball 不含 submodule 内容、GitHub archive
  无 configure、autotools 构建的 pcap/取证 CLI；运行期默认生成 DFXML/XML 报告
  且报告路径调用 getpwuid() 等 libc 环境查询；进程 uid 可能无 /etc/passwd 条目
  （容器/CI）；上游提供离线 pcap 夹具与确定性断言。
- **not_applicable_when**：官方 tarball 已内嵌 submodule 或有预生成 configure；
  非 autotools（cmake/meson）；运行期不生成报告或不调用 getpwuid；uid 恒有
  passwd 条目；上游无任何可离线复现测试输入。

## 查重差异（与已有 E-entry）

- E150（manual-download）：覆盖"tarball 缺 submodule 手动下载"，仅 cmake 场景，
  未覆盖 conandata `sources.submodules` 段 + autotools `source()` 合并的配方化模式；
- E175（autoreconf-regenerate）：覆盖 configure/config.status 临时目录
  confXXXXXX Permission denied（umask 077→022），仅配置期，与 E327 运行期
  getpwuid SIGSEGV 无重叠；
- E116（compile-automake-from-source）：覆盖 automake perl 模块 @INC 环境修复；
- E287（fuzz-corpus-deterministic-runner）：覆盖 pcap_open_live CAP_NET_RAW
  替代测试，未覆盖 DFXML 报告 getpwuid 空指针。

**本草稿真正新增、可供其他库复用的部分**：
1. **getpwuid() NULL 防御补丁模式**（dfxml_writer.cpp:476 类行）——适用于所有
   DFXML/XML 报告生成中调用 getpwuid 的工具；
2. **精确诊断方法**——"report.xml 截断于 `<uid>` + 最小复现程序"快速定位
   libc 环境查询空指针；
3. **conandata submodules 段 + 上游 test1.sh 断言逐字节复用（md5+size+mtime）**
   的离线消费者测试范式。

## 安全与清理

- 测试驱动仅用 `-r` 离线 pcap 夹具（上游 test1.pcap），不触碰网卡/root/
  CAP_NET_RAW/端口；临时输出目录位于 TMPDIR 下、测试后清理（shutil.rmtree）；
- 生产 tcpflow 保持真实网络/抓包语义，无 mock、无隐藏环境变量、无伪造成功路径。

## 关联条目

- 相关: E150, E175, E287, E116
- 原则: P004, P014, P016
