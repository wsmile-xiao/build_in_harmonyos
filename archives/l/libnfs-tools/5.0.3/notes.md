# libnfs-tools 5.0.3 适配笔记

## 结论（主管裁定）
libnfs-tools 无独立上游 GitHub 仓库（sahlberg 名下不存在；GitHub 全站搜索 0 结果）。
Alpine 生态以 libnfs 子包形式提供同名工具集。按主管裁定立项：
**libnfs-tools/5.0.3 = libnfs 5.0.3 官方 tarball 的 utils/ 工具集**（nfs-ls/nfs-cat/nfs-cp/nfs-stat），
独立配方、独立 commands.json、链接已发布依赖 libnfs/5.0.3。

## 编译环境
- 构建系统: custom（生成 ohos-build/CMakeLists.txt，仅编译 utils/ 四工具，链接 libnfs::nfs）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（Conan Toolchain 注入，R33）
- 状态: published（conan-verify G0-G4+L2/L4/L5 PASS + finish W3 本地 CI 绿）

## 编译步骤
1. 探索编译（验证 utils 源码与 libnfs 依赖的编译/链接可行性）：
   ```
   clang -O2 -fPIC -DHAVE_UNISTD_H -DHAVE_POLL_H -D_U_='__attribute__((unused))' \
     -o nfs-cat utils/nfs-cat.c -I<libnfs include> -I<libnfs include>/nfsc <libnfs>/lib/libnfs.a -lpthread
   ```
   四工具全部 rc=0，无参运行打印 Usage，ELF64 ARM aarch64。
2. conan-init 生成 autotools 模板 → 按 CLI 工具集重写 conanfile.py（CMakeToolchain + CMakeDeps，
   build() 生成 ohos-build/CMakeLists.txt 仅编译 utils 四工具，install RUNTIME DESTINATION bin）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务书给定上游 URL github.com/sahlberg/libnfs-tools 404 | 该仓库在 GitHub 不存在 | 主管裁定改用 libnfs 官方 tarball 的 utils/ 子集 |
| 2 | utils 源码头文件分两种引用形式 | `#include "libnfs.h"`（引号，在 nfsc/）+ `<nfsc/libnfs-raw.h>` 内部角括号引用 | 双 include 路径：`-I<include>` + `-I<include>/nfsc` |
| 3 | close/lseek 隐式声明警告 | HAVE_UNISTD_H/HAVE_POLL_H 未定义则 unistd.h/poll.h 不包含 | 自定义 CMake 中 target_compile_definitions 定义两宏 |
| 4 | conan.tools.files 无 write 符号 | 版本差异 | 改用 Python 原生 open() 写生成 CMakeLists.txt |
| 5 | R53 codesign 断言误失败 | 测试用 readelf -l 查 program headers，.codesign 是 section | 改用 readelf -S |
| 6 | finish E017 镜像注入污染 conandata.yml | 框架缺陷（libnfs 任务已记录） | 手动还原为官方单 URL（R39/PF7） |

## 源码修改
无补丁（零源码修改，四工具源自上游原样编译；R3 无 .patch 生成）。

## 依赖版本
- libnfs/5.0.3（conan ohpcd 已发布，静态库，rev 750dbb2885）

## 验证结果
```bash
./nfs-cat  -> Usage: nfs-cat <file>             rc=0
./nfs-ls   -> No URL specified / Usage: nfs-ls  rc=1
./nfs-cp   -> Usage: nfs-cp <src> <dst>         rc=0
./nfs-stat -> Usage: nfs-stat <file>            rc=0
readelf: ELF64 LSB pie, ARM aarch64, interp /lib/ld-musl-aarch64.so.1
```

## 上游测试（R51 三步法，实测回填，如实申报）
- **清点**：libnfs-tools 无独立上游仓库。libnfs 5.0.3 官方 tarball 全量清点：
  - a) `utils/` 工具集自身：4 源文件（nfs-cat.c/nfs-cp.c/nfs-ls.c/nfs-stat.c）+ Makefile.am + CMakeLists.txt，**无任何测试脚本/目标**（无 test*.sh、无 enable_testing、Makefile.am 无 TESTS）→ utils/ 自身 N=0；
  - b) tarball 根级 `tests/` 目录：**50 个 test_*.sh**（另 3 个 .disabled）+ 30 个 prog_*.c 辅助程序 + functions.sh，属 **libnfs 库本体**功能测试（需 NFS 服务器挂载、测库 API 数据面）→ **tarball 全量 N=50**。
- **实跑**：上游 utils 无测试可跑；tarball tests/ 50 项属库本体、需 NFS server、与本 CLI 包产物无对应，不在本包运行（库测试由依赖包 libnfs/5.0.3 按其申报口径记录）；替代实测 = 本包 test_package 四工具真实执行断言 4/4（无参执行均打印 Usage）。
- **回填**：上游测试 **N=50（tarball tests/ 全量，属 libnfs 库本体）**；本包 utils/ 工具 N′ 不适用（自身无测试，库本体测试需 NFS 环境且与本包无关）；替代执行断言 4/4 = 100%。清点证据见 test_package/MANIFEST.yml。

## 鸿蒙特有测试（R53）
test_package/ohos_specific_test.py 对 4 个二进制各断言 7 项（pure-python ELF64 解析：
ELF64 class / e_machine=AArch64(183) / PT_INTERP=ld-musl-aarch64 / .codesign 段 /
无 RPATH·RUNPATH / libnfs 静态链接 DT_NEEDED 无 libnfs.so / 实际执行打印 usage）= **28/28 PASS**。
CLI smoke：nfs-ls/nfs-cat/nfs-cp/nfs-stat 无参打印 Usage = 4/4 PASS。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | 独立配方（application），requires libnfs/5.0.3 |
| conandata.yml | sources → libnfs 官方 tarball，sha256 实测 d945cb4f… |
| commands.json（软件级） | R38：nfs-ls/nfs-cat/nfs-cp/nfs-stat |
| test_package/ | CLI 实跑 + R53 鸿蒙特有断言（ohos_specific_test.py） |
| reports/test-report.md | R51 三步法 + R53 断言 + W3 结果回填 |

## 注意事项
1. 软件级 commands.json 在 archives/l/libnfs-tools/commands.json（R38，先例对齐 lci/d11amp）。
2. 本包依赖 libnfs/5.0.3 已发布（主管确认✅，R36 满足）。
3. utils 工具链接静态 libnfs.a + pthread，产物自包含（NEEDED 仅 libc）。
4. 框架缺陷记录：finish W3/E017 会把 gh-proxy.com 镜像注入 conandata.yml 主 URL（违反 R39），
   每次 finish 后需人工还原官方单 URL；gen_summary 崩溃（'str' object has no attribute 'append'）
   为非阻塞框架缺陷。
---

**编译结束**: 2026-09-21 16:57
**最终状态**: published

## CI 调度记录（2026-09-23，R25 过程记录）
- 12:04–13:29：#55918 / #55919 构建失败，类别=基础设施（worker CI-035 SSH bridge `connection refused`、源码下载网络超时），非本包代码/配方问题。
- 13:21 / 14:05 / 14:35 / 18:37：四次 /rebuild（note 191307671 / 191311986 / 191320621 / 191404030）；前三次仅回执、平台未派发新构建号；对 CI 构建墙 #55920–#56641（约 720 条）逐条扫描无任何 libnfs 包，证实为调度侧未派发（同窗口其他 PR 构建正常流转）。
- 历史绿：#55314（2026-09-22 03:54，SHA 5291b842fb）L0/L1/test_package 全绿；本地 W3 conan create 28/28 全绿。
- 本次提交仅同步上述调度过程记录；配方、测试包、清单零改动（产物与已绿构建一致）。
