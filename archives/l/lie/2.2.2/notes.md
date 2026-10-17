# lie 2.2.2 适配笔记

## 编译环境
- 构建系统: 裸 Makefile（无 configure；顶层 Makefile + box/ static/ util/ 子目录）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，aarch64-unknown-linux-ohos）
- bison: 3.8.2（构建期从 parser.y 生成 parser.c/parser.h——**发行 tarball 不带这两个生成物**，sage 源 `tar -tzf | grep -c parser\.(c|h)` = 0；属构建期生成物面，**不入补丁面**）
- 状态: built

## 编译步骤

```bash
# conanfile.build() 实际执行顺序
apply_conandata_patches                 # 0001 printexpr NULL 补丁（strip 1）
make -j1 noreadline \
     CC=<conf tools.build:compiler_executables:c，回退 PATH clang> \
     CFLAGS='-O3 -pipe -DNDEBUG'        # -j1=R9；CFLAGS 钉桩=R33；noreadline=README 明文路径
#   noreadline 目标内含：box/ static/ 子目录 + 全部 .o + getl.c（不带 -Dpreprocessor，
#   即不链 readline）+ Lie.exe + script(make_lie) + LEARN.ind + INFO.ind + INFO.a
# 上游三入口（build() 内逐条计数，不符即失败）：
./Lie.exe initfile . < progs/test       # 23 Okay / 0 false
./Lie.exe initfile . < progs/testsuite  # error=0（18 条件断言）+ 3 分节标题在场
./Lie.exe initfile . < progs/maxsub0    # 零输出（纯定义装载）+ A5 冒烟 7 子群正向证明
# package()：copy 收 Lie.exe + INFO.0-4/INFO.a/INFO.ind/LEARN/LEARN.ind/title → bin/，
#            并重写自定位包装脚本 bin/lie（上游 make_lie 烧构建目录绝对路径，随包断链）
```

产物：`bin/lie`（包装脚本）、`bin/Lie.exe`（371136B 未 strip，hnp clang `.codesign` 有效）、
`bin/INFO.0-4`（文档体）、`bin/INFO.a`（定义库）、`bin/INFO.ind`、`bin/LEARN{,.ind}`、`bin/title`。
链接面：`clang -o Lie.exe … static/*.o box/*.o` **不带 -lreadline** —— `readelf -d` NEEDED **仅 `libc.so`**。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | W0 关①版本实核：官方渠道唯一性与「同源」判定 | 上游官方主页 `young.sp2mi.univ-poitiers.fr` 已下线（根路径 Apache 默认页、`~marc/LiE/` 502，留档 `w0/upstream-home.html`、`w0/upstream-lie.html`），Debian 池存在 `lie_2.2.2+dfsg.orig.tar.gz`（+dfsg 重打包） | **三源 sha256 全等 + sha1 双算法互证**：MIT sage 镜像与 RIKEN sage 镜像两处实下载（361073B）sha256=`c4d6f67f…b1e`、sha1=`bf8d2303…22a5d` 全等，再与第三方发布方校验值记录 `sagemath/sage` 仓库 `checksums.ini`（sha1+sha256 双字段）互证；内证 `init.c:153` 自报 `LiE version 2.2.2`。双算法互证防单一算法碰撞，第三方记录独立于两个镜像主机 |
| 2 | PF7 源 URL 闸（A 类硬拦）：Debian `+dfsg` 源两档命中 | `_pf7_classify` 对 Debian 下游重打包源判「Debian 下游重打包源」、对明文 http 判「R39 要求 https」——两处都 A 类 | **改道 sage 上游镜像**（meschach 改道先例同型）：conandata 用有序 URL 列表 MIT 首选/RIKEN 回退（sha256 同值），直接调 `preflight.py` 的 `_pf7_classify`/`check_source_urls` 函数级模拟：两条 sage URL classify=None、`check_source_urls(拟用 conandata)` 零 findings，Debian 对照组两条命中确证不采用；**沿用已定 URL 不再换** |
| 3 | W0 关②硬依赖判定：是否需要 GMP/MPFR | 通常李群计算库链 GMP；误判会白加 requires 或漏加导致链接挂 | **三层证真（缺依赖=零缺口）**：①静态 grep `gmp\|mpfr\|mpir` 三处独立扫描全 0 命中且 include 全为 C 标准库；②`readelf -d Lie.exe` NEEDED 仅 `libc.so`；③自带 `bigint.c`（478 行 K&R 自实现大整数）在 Makefile `common_objects` 实际参与链接。三层互证后 `requires()` 留空 |
| 4 | W0 关④工具缺口两条：readline 缺失、gcc/cc 缺失 | 上游默认目标 `Lie.exe: … -lreadline` 链接 GNU readline；Makefile 写死 `CC = gcc`，设备两者皆无 | readline→**`make noreadline`**（README 明文路径：不带 `-Dpreprocessor` 编 getl.c、链接行不带 `-lreadline`，产物功能等价无行编辑）；gcc→**显式 `CC=<conf c 或 PATH clang>`**（先例#7 presage/mdocml/yapet 同型，Makefile 内 `CC = gcc` 被命令行变量覆盖）；CFLAGS 同理由命令行钉 `-O3 -pipe -DNDEBUG`（R33，防 CI worker 环境泄漏分叉 NDEBUG 面） |
| 5 | 运行期 SIGSEGV(rc=139)：`?help`/`?dim` 等 printexpr 查询入口必崩 | `print.c:601` `tmpnam(tmpfile); cur_out=fopen(tmpfile,"w")` **不检查 fopen 返回值**：OHOS `/tmp` 只读(EROFS) 下 fopen 恒返 NULL，随后 `printdocument` 经 `cur_out` 写入即解引用 NULL → SIGSEGV。同文件 `learn.c:135` 与 `print.c` 另三处（:982/:1007/:1028 邻近）均有 `cur_out==stdout→stdout` 回退先例可对齐 | 裁决=**portability 补丁**（三入口上游测试 0 命中 `?`，不影响上游断言面；无 `__OHOS__` 平台宏，PF5 免拦）：`0001-printexpr-null-check.patch` 补 NULL 检查——fopen 失败回退 `cur_out=stdout` 且 `invoke_pager=false`。**修前 rc=139（`w0/pre.out` 0B）→ 修后 rc=0（`w0/post2.out` 364B 帮助正文）双证**；test_package 用 `?help`/`?dim` 断言把该面固化为消费者回归 |
| 6 | rc=139 探针双支定性（防误判上游/误判设备） | 同一 SIGSEGV 有两个独立成因支：①自家探针 `.c` 缺 `#include <stdlib.h>`，`getenv` 隐式声明（int 返回截断指针）自身即崩——探针缺陷假信号；②上游 printexpr 真缺陷（#5） | **先修探针再定上游**：补 include 后修正版三连探针 rc=0（`w0/p1..p3`），排除探针支后再对上游复跑得 rc=139→补丁→rc=0，两支互不混淆。设备事实（入 feedback 不冒充设备事实）：`tmpnam` 产名正常但 `fopen`/`tmpfile` 恒 NULL(EROFS)，**不判空的调用方必 SIGSEGV**——同类旧 C 程序通用判据 |

## 源码修改

- `patches/0001-printexpr-null-check.patch`（strip 1，portability）：`print.c` `printexpr()` 对
  `fopen` 返回值补 NULL 检查，失败回退 `cur_out=stdout; invoke_pager=false`，对齐同文件
  `learn.c:135` 与 `print.c` 另三处既有形态；无平台宏（PF5 免拦）。
  三关验证：NUL 字节=0、`@@` hunk 头=1、conan `patch(strip=1)` 真 apply 后与
  `w0/ptree/LiE/print.c.patched` 逐字节 `cmp` rc=0。
- `parser.c`/`parser.h`：**不在补丁面**——tarball 不带，bison 构建期生成（见编译环境节）。

## 依赖版本

- 运行期/构建期外部依赖：**无（空集）**——`requires()` 为空；`readelf -d` NEEDED 仅 `libc.so`；
  大整数为自带 `bigint.c`（W0 关②三层证真，问题表 #3）。
- 构建工具链：clang 15.0.4（conf 注入）、make 4.4.1、bison 3.8.2（PATH，`/data/service/hnp/bin`）。
- 可选依赖 readline：缺省经 `noreadline` 禁用（问题表 #4），未启用任何对应开关。

## 验证结果

```bash
# 上游测试（沙箱 HOME，断言口径 assertion 单栏；证据 $TASK_DIR/w0/prog-*.out + conan create 日志）
$ ./Lie.exe initfile . < progs/test        # rc=0  Okay=23 False=0
$ ./Lie.exe initfile . < progs/testsuite   # rc=0  error=0（18 条件断言 + 3 分节标题）
$ ./Lie.exe initfile . < progs/maxsub0     # rc=0  0 字节；A5 冒烟 7 子群（不计上游）
上游合计: TOTAL=41 PASS=41 FAIL=0 SKIP=0 NOT_RUN=0（23+18+0）

# 消费者测试（test_package/test.sh，7 条断言）
$ sh test.sh
test_package: 7/7 assertions, fail=0

# printexpr 补丁面双证（修前/修后）
$ printf '?help\n' | ./lie   # 修前 rc=139（w0/pre.out 0B）→ 修后 rc=0（w0/post2.out 364B）

# 产物与链接面
$ readelf -d bin/Lie.exe | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

## 注意事项

- `?version` 输出「Version 2.1」是 INFO.0 内自带文案（上游数据陈旧，非本包版本判定依据）；
  版本以 tarball 内证 `init.c:153` 的 `LiE version 2.2.2` 为准，勿用 `?version` 做指纹断言。
- 上游**无 make check**：等价入口即三文件直跑（MANIFEST.yml 已声明）；test_package 不得并入上游计数。
- 交互式 banner（`LiE version 2.2.2 created on …`）仅非重定向 stdin 才打印（`redirected_input` 门控），
  管道喂输入时不出现——冒烟断言勿依赖 banner。
