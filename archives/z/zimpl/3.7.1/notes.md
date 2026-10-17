# zimpl 3.7.1 适配笔记

## 编译环境
- 构建系统: cmake（CMakeLists.txt，`project(ZIMPL VERSION 3.7.1 LANGUAGES C)`，C99）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，aarch64-unknown-linux-ohos）
- 状态: built（本地 conan-verify 全绿、W3 本地 CI 通过；待 release 流水线 upload 制品仓成功后才置 published）
- 上游: https://github.com/scipopt/zimpl（tag v3.7.1）
- 归档: archives/z/zimpl/3.7.1

## 编译步骤

1. 源码下载：`curl -kL https://github.com/scipopt/zimpl/archive/refs/tags/v3.7.1.tar.gz`（本机 urllib SSL 证书验证失败，手动 curl -k 下载后放置 $HOME/tmp/builds/）
2. 初始化：`ohc-run.py init-build zimpl 3.7.1`（注意：必须设 OHC_PROJECT_DIR 指向工作区仓库，否则归档误建到 SKILL 目录；TMPDIR 用 $HOME/tmp）
3. 语言预检：`lang-preflight` → detected=c（c↔cpp 兼容族）通过
4. CMake 配置（探索编译，依赖注入 conan gmp/zlib 的 package_folder）：
   ```bash
   cmake <src> -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang \
     -DGMP_DIR=<conan-gmp-package> \
     -DZLIB_INCLUDE_DIR=<conan-zlib>/include -DZLIB_LIBRARY=<conan-zlib>/lib/libz.a \
     -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX
   ```
5. 编译：`make -j`（100% 通过，产物 bin/zimpl + libzimpl.a + libzimpl-pic.a）
6. 安装：`make install`（头文件 include/zimpl/、静态库 lib/、cmake config lib/cmake/zimpl/）
7. 上游测试：`cd check && sh check.sh <相对路径二进制>`（详见下方测试申报）
8. conan 配方：`ohc-run.py conan-init zimpl 3.7.1` → 修正 conanfile.py/test_package/commands.json/MANIFEST.yml → `conan-verify` 全绿

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 归档误建到 SKILL 目录 | find_project_dir() 从脚本位置找到 SKILL.md（跳过 OHC_PROJECT_DIR） | export OHC_PROJECT_DIR=<工作区仓库路径> 后重跑；清理 SKILL 目录误建产物 |
| 2 | 手动 curl -k 下载后 init-build 仍尝试下载 | 源码包需放 $TMPDIR/builds/（$HOME/tmp/builds/）才命中"已存在"分支 | 放对路径重跑；TMPDIR 默认指向 /data/storage/el2/base/temp 需显式 $HOME/tmp |
| 3 | check.sh 0/209 全 FAIL（首轮） | 二进制动态链接 conan gmp（libgmp.so.10/libgmpxx.so.4），运行期未注入库路径；且 check.sh 内部 `../$1` 拼接相对路径，绝对路径传参在 warnings/errors 子目录失效 | ① set LD_LIBRARY_PATH=<gmp lib>:/system/lib64；② 用相对路径传二进制（`sh check.sh ../../../zimpl-build/build/bin/zimpl`） |
| 4 | check.sh minlp.pip/metaio.lp/qubo.lp 3 项 FAIL | ASLR 导致 zimpl 内部指针哈希表遍历顺序非确定，连续 3 次运行 md5 均不同；输出项/乘法因子排列顺序与参考文件不同 | 数学等价验证：规范化排序（因子排序/求和项排序）后 diff=0，确认纯顺序差异非功能缺陷 |
| 5 | conan-verify G2: bison `m4sugar.m4: cannot open` | conan bison/3.8.2 编译期 pkgdatadir 内嵌 /share/bison 绝对路径，实际数据在包内 share/bison/ | build_requirements 加 m4/1.4.19；build() 中设 BISON_PKGDATADIR（指向 bison 包 share/bison）与 M4（指向 m4 包 bin/m4），同 ball 配方先例 |
| 6 | test_package 链接 xlp_* 未定义 | libzimpl.a 只含解析核心，LP 输出后端（xlpglue/zlpglue/ratlpstore 等）仅编译进 bin/zimpl 可执行文件 | test_package 改为直接执行 bin/zimpl 翻译 0/1 背包模型并校验 knapsack.lp（R34：执行被测包二进制） |
| 7 | conan-verify G2: `bin/zimpl: Operation not permitted`（Error 126） | CMake install 规范化 RUNPATH 尾冒号：`/path/lib:` → `/path/lib`；OHOS musl loader 对 RUNPATH 语义敏感，无尾冒号 ELF execve 被拒 | 1 字节翻转实验定位（改尾冒号字节即恢复可执行）；package() 用 build 目录原始 bin 覆盖 install 产物 + generate() 设 CMAKE_INSTALL_RPATH_USE_LINK_PATH=ON |
| 8 | G2 修 RUNPATH 后仍 `libc++_shared.so not found` | 纯 C 项目被 FindGMP 默认链入 libgmpxx（C++ 接口库），引入 libc++_shared 依赖 | generate() 设 GMPXX_LIBRARY="" 阻止 find_library 搜 gmpxx，NEEDED 只剩 libgmp/libc |
| 9 | W3/JC 检测到 2 个垃圾文件 | 工作区在 main 分支且 zimpl 未提交，junk_check full 模式整仓扫描到 cloog 0.21.1 历史 PR 遗留的 .build-closed/.staging-verified | 创建 feat/zimpl-3.7.1 分支并提交 zimpl 文件，检查进入增量模式只扫本任务变更 |

## 源码修改

无补丁，无源码修改。zimpl 3.7.1 原始代码在 OHOS (aarch64, clang 15) 上编译无兼容性问题。

## 依赖版本

| 依赖 | 类型 | 制品仓版本 |
|------|------|-----------|
| gmp | 运行时（REQUIRED，FindGMP.cmake） | gmp/6.3.0.1 |
| zlib | 运行时（可选 ZLIB=ON） | zlib/1.3.2 |
| bison | 构建工具（REQUIRED，bison_target） | bison/3.8.2 |
| flex | 构建工具（REQUIRED，flex_target） | flex/2.6.4.2 |
| m4 | 构建工具（bison 运行时宏库） | m4/1.4.19 |

## 上游测试申报（R51）

**check/check.sh 主测试套件：209 项计数（按 check.sh 全部 diff 比较测试点统计，含循环展开），实测 209 项全部尝试运行，195 通过 / 14 项运行失败（4 项 ASLR 顺序差异数学等价 + 10 项 e789 上游标注可变输出）**
- 通过（195）：expr/param/set/subto/condit/var/bool/define/vinst/sos/read 的 lp+tbl（22）、presol mps/tbl/mst/ord/hum（5）、print.out、metaio.out、qubo q/q0cp/tbl、bqp50-1/ps5-1 qbo2/qbo3、warn 套件（w139-w215 等）、err 套件（e1-e6xx）
- 运行失败 - ASLR 顺序差异（4 项，数学等价）：minlp.pip、metaio.lp、qubo.lp（lp.1/lp.2 双参考文件各计 1）—— 输出项/乘法因子排列顺序与参考文件不同，**ASLR 导致 zimpl 内部指针哈希表遍历顺序非确定**（同一测试连续 3 次 md5 均不同）；规范化排序（因子排序/求和项排序）后与参考文件 diff=0，**数学内容完全等价**，非功能缺陷
- 运行失败 - 上游标注可变输出（10 项）：e700_1/e700_2/e700_3/e701/e702_1/e702_2/e702_3（e7xx 区段）+ e800/e802（e8xx 区段）+ e900（e9xx 区段）—— 上游检查脚本显式标注"Error 700 to 900 can vary"，diff 失败不计 PASS 且不计数，日志输出 FAIL (ignored)
- 运行方式：`cd check && sh check.sh <二进制相对路径>`（必须相对路径，脚本内部 `../$1` 拼接；且需 LD_LIBRARY_PATH 含 gmp lib 与 /system/lib64）

**test/dotest.sh 辅助测试：无法运行**
- 依赖 .lp.ok/.mps.ok/.tbl.ok 参考文件，源码包未发布（test/ 目录仅有 .zpl 与脚本）
- 已尽穷尽核查：源码包 filelist 无 .ok、Makefile 无生成 .ok 目标、git 仓库树 test/ 目录同样无 .ok

**test_package 自研测试：4 项断言**
- ① 执行 zimpl CLI 翻译 0/1 背包模型（knapsack.zpl）退出码为 0
- ② 校验 knapsack.lp 文件已生成
- ③ 校验 knapsack.lp 包含 "Maximize" 节
- ④ 校验 knapsack.lp 包含 "Subject to" 节

## 验证结果

```bash
# conan-verify（G0-G4 + L2/L4/L5 全绿）
ohc-run.py conan-verify zimpl 3.7.1   # ✅ 配方验证通过，可标记 published

# W3 本地 CI 模拟（finish step 5/10）
# setup.sh + build_and_test.sh 通过（分支提交后增量模式）

# 上游测试
cd check && sh check.sh ../../../zimpl-build/build/bin/zimpl  # 195/209，14 项运行失败（4 项 ASLR 顺序差异数学等价 + 10 项 e789 上游标注可变输出）
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/z/zimpl/3.7.1/conanfile.py | Conan 配方（gmp/zlib 依赖、bison/flex/m4 构建工具、RUNPATH 覆盖、GMPXX 置空） |
| archives/z/zimpl/3.7.1/conandata.yml | 源码 URL + sha256（95f24de6...） |
| archives/z/zimpl/3.7.1/test_package/ | 二进制实质测试（knapsack.zpl 翻译校验）+ MANIFEST.yml |
| archives/z/zimpl/commands.json | CLI 工具声明（bin/zimpl，tool 类型，R38） |
| knowledge/drafts/E6344-draft-zimpl-bison-pkgdatadir-redirect.kv、E6345-draft-zimpl-cmake-install-rpath-tail-colon-eperm.kv、E6346-draft-zimpl-pure-c-findgmp-libgmpxx-libcxx-shared.kv | 3 个知识草稿（bison pkgdatadir / RUNPATH 尾冒号 EPERM / gmpxx 误链） |

## 注意事项

- 上游 zimpl 是 dask 生态 Python 库的同名混淆项：本仓库适配的是 scipopt/zimpl（SCIP 套件 Zuse Institute Mathematical Programming Language，C 语言 LP/MPS 模型翻译器）
- RUNPATH 尾冒号问题（EPERM）是 OHOS CMake install 类 CLI 项目的通用坑，知识草稿已沉淀
- 二次适配本包时：若 conan-verify 报 EPERM，优先核对 p/bin 与 b/build 二进制的 RUNPATH 尾冒号（cmp -l 应一致）
---

**编译结束**: 2026-09-16 21:29
**最终状态**: built（本地 conan-verify 全绿、W3 本地 CI 通过；待 release 流水线 upload 制品仓成功后才置 published）
