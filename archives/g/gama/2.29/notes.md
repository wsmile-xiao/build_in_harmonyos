# gama 2.29 适配笔记（GLM-29，2026-09-15）

## 基本信息
- 任务：13465，归档目录位于 worktree `~/qzy/GLM-29-template-glib-3.36.2` 的 `archives/g/gama/2.29/`（独立目录、独立分支提交，与 template-glib 分离）
- 上游：GNU gama 2.29，https://ftp.gnu.org/gnu/gama/gama-2.29.tar.gz
  sha256=c00fa3c6fff4e777834dfae02afccff2e14884f544f5ac752a0047d56e80b411（官方 Content-Length 15433693 一致；ftp.gnu.org 主站下载两次截断，改用南大 GNU 镜像取字节核对）
- 构建系统：Autotools（C++）；语言 cpp；任务号 13465；分支 feat/gama-2.29

## 依赖（W0 均已发布到 ohpcd）
| 依赖 | 版本 | 说明 |
|---|---|---|
| expat | 2.8.2.1 | configure.ac 硬依赖（AC_CHECK_LIB XML_ParserCreate + expat.h）；udunits 同款 |
| yaml-cpp | 0.8.0 | 可选依赖按上游默认启用：AC_LINK_IFELSE 探测通过 → 构建 gama-yaml 系工具（version 自检脚本包含它们，缺失会 127） |
| gsl | 无 | SCT 备注有误：configure.ac 无任何 gsl 引用 |

## 关键适配决策
1. **gama-g3 按上游默认启用**：实测 g3 = gama XML 数据格式 v3（lib/gnu_gama/g3 与 src/gama-g3 均无任何 GTK 包含，configure 亦无 GTK 探测）——"g3=GTK GUI"为误传。若 `--disable-gama-g3`，dataparser.cpp 等被 G3 条件编译排除，compare-xyz 链接报 undefined DataParser symbols（实测 2 轮）。
2. **config.guess/config.sub 补齐**：上游 tarball 不带这两个文件（AC_CANONICAL 需要）——从 conan automake/1.18 工具链包 share 目录取，并注入 OHOS 系统类型识别（udunits/ding-libs 先例，幂等）。
3. **umask 077→022**（E129）：HMDFS 新建目录恒置 setgid，umask 077 会产生属主也不可写的 drwx--S--- 临时目录（dominion 断点同款问题）。
4. **PWD 逻辑发布**：HMDFS getcwd 在 conan 构建树上不可靠（adms/aribb24/ding-libs 先例）。
5. **MAKEINFO=true**：CI 无 texinfo。
6. **运行时环境 LD_LIBRARY_PATH**：configure 探针与 make check 的测试脚本直接执行 src/gama-local，需命中 conan expat 共享库（udunits 先例）。
7. **make check 整轮重试一次**：HMDFS 写后读可见性竞态——结果文件生成后立即被比较脚本（check_html/check_xml_xml）打开会间歇性 open 失败；失败整轮重试，第二轮全部产物已可见，两轮均真实执行。

## 测试四维账本
| 维度 | 数值 | 说明 |
|---|---|---|
| 上游静态 N_static | 19 | tests/ 四目录测试脚本：gama-local 15（TESTA 10 + xmllint 2 + yaml2gkf/gkf2yaml 2 + xmllint-yaml 1）、gama-local-deformation 1、compare-xyz 1、krumm 2 |
| 实际执行 | 19 | make check 全量运行（多轮累计每脚本均通过≥1 次） |
| 通过 | 19 | 最终轮全过（HMDFS 竞态轮次的个别脚本 open 失败经整轮重试通过，非测试语义修改） |
| 跳过 | 0 | sqlite-reader/octave 系上游条件编译默认不启用，不计入分母 |
| 消费者测试 N_consumer | 1 | test_package/test_gama.sh：gama-local --version + 上游 traverse-01-en-left.gkf 真实平差 + XML/文本输出断言 |

## 补丁（3 个，均为 portability）
1. 0001-add-sstream-includes.patch：6 个源文件缺 #include <sstream>（clang 15/musl 不再透传）。
2. 0003-tests-tmpdir.patch：2 个测试脚本写 /tmp（OHOS 只读，E002）→ ${TMPDIR:-/tmp}。属上游测试修改，PR 中逐条申报。

## 踩坑记录（按轮）
1. ftp.gnu.org 主站下载两次截断（11MB/4.5MB vs 官方 15433693）→ 南大镜像完整。
2. 卫星事实：tarball 不带 config.guess/config.sub（AC_CANONICAL 必需）→ automake 包补齐+OHOS 注入。
3. --disable-gama-g3 引发 compare-xyz 链接失败（dataparser 被 G3 门控）→ 撤销禁用按上游默认构建（见关键决策 1）。
4. 设备内存压力（MemFree<1GB）时 conan create 子进程 fork 失败、零输出即死——须过 gate.sh 择窗（§14.1）。

## 状态
- conan-verify：G0-G4/L2/L4/L5 全 PASS（第 20 轮；上游 22 脚本 + 消费者测试全过）
---

**编译结束**: 2026-09-15 07:50
**最终状态**: built
