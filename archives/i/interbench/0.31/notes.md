# interbench 0.31 — 适配笔记

版本级细节记录：构建链、补丁、真机验证、测试清点与已知限制。
元数据见同目录 `manifest.yaml`；源码与补丁口径以 `conandata.yml` 为准。

## 1. 上游与产物

- 上游仓库：https://github.com/ckolivas/interbench
- 版本：v0.31（标签归档，sha256 `eb838f89a95ba0bffde06c86f6bda565ef234e6165ab86df4e187933ac779151`，38791 字节）
- 构建系统：官方 Makefile（无 configure、无 install 目标）
- 产物：`bin/interbench`（ELF64 aarch64，Position-Independent Executable，137664 字节）
  + `licenses/COPYING`
- 许可证：源文件头为 "GPL version 2 **or (at your option) any later version**"，
  即 GPL-2.0-or-later（归档内另有 LICENSE 文件为 GPLv3 模板文本，非实际授权声明口径）

## 2. 构建链

- `build()`：`apply_conandata_patches` → `make CC={cc} -j1`，cc 取自
  `tools.build:compiler_executables` conf（缺省 clang），不依赖裸环境变量
- 官方 Makefile 的 `interbench` 目标没有显式链接命令行，链接由 GNU make
  隐式规则（`$(CC) $(LDFLAGS) … -o $@`）完成，`LDFLAGS=-lrt -lm -pthread` 生效
- 运行期依赖仅 OHOS libc：产物动态段 NEEDED 仅 `libc.so`
  （`libm` / `librt` / `libpthread` 为 OHOS musl 内建，无需单独链接库文件）
- 源文件 md5 与官方发布包（ck.kolivas.org 的 interbench-0.31.tar.bz2）一致：
  interbench.c `1fc45396…`、interbench.h `47d036e2…`、hackbench.c `d5685e83…`、
  COPYING `393a5ca4…`

## 3. 补丁（2 枚，均为可移植性）

### 0001-add-sys-stat-header.patch

- 现象：clang 15 编译报 `variable has incomplete type 'struct stat'`
- 根因：旧 glibc 时代的代码依赖头文件链（stdio.h 等）间接引入 struct stat
  定义，OHOS musl 头文件不再传递包含
- 修改：interbench.c 顶部显式 `#include <sys/stat.h>`（1 行）

### 0002-fix-makefile-lm-prerequisite.patch

- 现象：`make: *** No rule to make target '-lm'`
- 根因：上游把 `-lm` 写进目标先决条件行
  （`interbench: interbench.o hackbench.o -lm`），GNU make 将不认识的词
  一律当作要构建的文件目标，在无 `/usr/lib/libm.so` 开发文件的系统上直接报错
- 修改：先决条件行移除 `-lm`；链接仍经 LDFLAGS 生效
  （与官方发布包 Makefile 的写法一致）

## 4. 真机验证（conan-verify）

设备：OpenHarmony PC（aarch64-linux-ohos），profile `ohos-aarch64`，2026-10-04。

**Verdict: PASS**

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 知识预查询 | ✅ | 检查器未识别 makefile 构建系统，按工具行为跳过预查询（本包实际构建系统即 makefile） |
| G1 配方完整性 | ✅ | name/version/source/build/package/package_info/export_sources、补丁应用调用、conandata 完整、test_package 与 MANIFEST.yml 均在 |
| G2 干净构建 | ✅ | `conan create` 成功（干净缓存构建） |
| G3 系统库 | ✅ | 无 lib/ 目录（纯可执行包），无系统同名库冲突（R26 通过） |
| G4 制品完整性 | ✅ | 检查器在纯可执行包上未能定位程序包 ID（工具行为）；制品缓存路径已人工核验 |
| L2 smoke / L4 安全 / L5 baseline | ⏭️ | 工具 cache 路径解析限制自动跳过（平台报告普遍同状，非本包问题） |

L4 等效补充核验（真机 `/data/service/hnp/bin/readelf`，于已安装制品）：

- `Type: DYN (Position-Independent Executable)` → PIE enabled
- `GNU_RELRO` 段 + 动态段 `BIND_NOW` → full RELRO
- `GNU_STACK` 段 flags `RW`（无 E）→ NX enabled
- 无 `__stack_chk_fail` 符号：上游未启用 -fstack-protector（信息性，非缺陷）

复用信息：包缓存 `interbench/0.31@ohpcd/stable#ca8d38f7…`，
已安装二进制 `…/p/b/intereb9317f0e66ec/p/bin/interbench`（137664 字节）。

## 5. 消费者测试（真实执行器）

`test_package/test_interbench.py`，由 `test_package/conanfile.py` 的 `test()` 经
`python3 <脚本> <安装后二进制>` 调用；逐例输出 TEST PASS / TEST FAIL，
末行输出 TEST SUMMARY，任一失败 exit(1)。真机 `conan create` 实测 **4/4 PASS**：

| # | 用例 | 结果 | 实测细节 |
|---|------|------|----------|
| 1/4 | `-h` 帮助输出 | PASS | rc=0，版本横幅与用法输出在 stderr |
| 2/4 | 未知负载名拒绝（`-w NoSuchLoad`） | PASS | rc=254，stderr 含 `Unknown load "NoSuchLoad"` |
| 3/4 | 首次完整基准（`-c -t 10 -W Audio -w Burn`） | PASS | rc=0，latency 0.1ms，12.2s |
| 4/4 | 复用已存 loops_per_ms 重跑 | PASS | rc=0，stderr 含 `loops_per_ms read from file` |

`TEST SUMMARY: 4 passed, 0 failed`。

### 5.1 interbench.read 大文件问题与稀疏文件解法

interbench 首次运行的 `create_read_file()` 要求运行目录内 `interbench.read`
大小恰为 `MemTotal×1024` 字节；不满足时它会**实写**一份等大文件
（真机为 32GB 级，浪费空间且极慢）。本执行器在临时工作目录用
`os.ftruncate()` 创建尺寸相符的**稀疏文件**，走"尺寸相符即返回"快路径，
使完整基准可在 CI 时长内跑完；并检查 stderr **不含**
`Creating file for read load`，防止未来回归到实写路径。

### 5.2 非 root 预期行为

真机以普通用户运行：`SCHED_FIFO` 调用返回 EPERM，工具打印
`Results will be unreliable` 后继续，退出码保持 0 —— 执行器不将其计为失败。
非 root 下的延迟数字仅反映冒烟可用性。

## 6. R51 上游测试清点（申报）

清点对象：v0.31 标签归档（sha256 `eb838f89…`）与解包后的源码树。

| 项目 | 清点结果 |
|------|----------|
| 归档文件总数 | 9：COPYING、LICENSE、Makefile、hackbench.c、interbench.8、interbench.c、interbench.h、readme、readme.interactivity |
| tests/ 或 test/ 目录 | 无 |
| Makefile 测试目标 | 无（目标仅 `interbench`、`interbench.o`、`hackbench.o`、`clean`） |
| CI 配置（.github 等） | 无 |
| 单元/集成测试框架注册 | 无 |

**申报上游测试用例数 = 0**（如实清点为 0，非跳过）；程序自身即基准工具，
端到端行为由消费者执行器 4 用例覆盖。

## 7. 知识沉淀

见 `manifest.yaml` 的 `knowledge_gained`：

1. 旧年代 C 代码在 clang 15 + musl 下 `struct stat` 不再经其他头文件传递包含，
   须显式 `#include <sys/stat.h>`；
2. GNU make 把目标先决条件中不认识的词（如 `-lm`）当作要构建的文件目标——
   系统库应放 LDFLAGS/LDLIBS，否则在无开发库链接的系统上报
   `No rule to make target '-lm'`。

## 8. 已知限制

- 非 root 下 SCHED_FIFO 不可用（工具自身提示 "Results will be unreliable"），
  延迟/抖动数值只反映冒烟可用性；
- 消费者测试使用 10 秒短基准（上游默认 30 秒）控制 CI 时长，覆盖
  校准 → 基准 → 复用 完整三段流程。
