# automake 1.19 编译笔记（HarmonyOS PC · Conan autotools · 工具包）

## 定位与版本选择（R37）

`package_type = "application"`，构建期工具，供下游配方 `tool_requires` 使用。

任务 contrib-6603 要求 1.18，但 1.18 已于 2026-07-30 适配完成并发布制品仓
（软件级 manifest `1.18.status=published`）——按 R37/L0j，同版本修订会被
cnb.cool 制品仓 409 拒绝。第 0 步即递增：上游 2026-09-10 发布 **1.19**
（1.18.1 之后首个新版，新特性 `AM_OPTIONAL_AUTOMAKE` + 58 commits 修复，
GNU Savannah 公告 2026-09-22），直接适配 1.19。

1.18 的完整适配过程（PERL5LIB/@INC、aclocal 宏目录、hnp pkg.m4 遮蔽三件套
的踩坑记录）见 `../1.18/notes.md`，本笔记只记 1.19 增量。

## 上游 1.19 与 1.18 的适配点比对（逐条核对源码）

| 适配点 | 1.19 现状 | 结论 |
|--------|-----------|------|
| bin/aclocal.in 的 @datadir@ 烘焙 + --automake-acdir/--system-acdir 选项 | 保留（bin/aclocal.in:26,66-67,1032-1035） | 包装方案原样适用 |
| bin/automake.in 的 @datadir@ 烘焙 + --libdir 选项 | 保留（bin/automake.in:29） | 包装方案原样适用 |
| configure 内 "umask 077" | 仍存在（2 处） | 022 修补继续适用 |
| perl 最低版本 | use 5.006 不变 | 无影响 |
| bin/ 工具集 | 仍仅 aclocal + automake | 包装覆盖不变 |
| 新特性 AM_OPTIONAL_AUTOMAKE | 新增（dist-xz 等按压缩工具可选打包） | 不影响构建流程 |

## 关键适配（沿用 1.18 三件套）

1. **PERL5LIB 补 @INC**：conan `--prefix=/` + DESTDIR 安装把 `//share/automake-1.19`
   烤进 perl 脚本，`package_info` 用 PERL5LIB 指回真实位置（不改脚本，可重定位）。
2. **aclocal 包装**：`--automake-acdir`/`--system-acdir` 从 `$0` 推算前缀。
3. **hnp 宏目录自发现**：glob `/data/service/hnp/*/*/share/aclocal` 追加
   ACLOCAL_PATH，防 `--system-acdir` 替换语义遮蔽 pkg.m4。

另：`MAKEINFO=true`（设备无 makeinfo，否则 install Error 127）；
显式 `--build/--host=aarch64-unknown-linux-musl` 跳过 config.guess
（OHOS 不在 config.sub 里）。

## 状态

**published**（2026-09-26）—— 真机 conan-verify 八门禁全绿（result.json
draft:false 上报）；test_package 四断言真机实跑通过。四断言因 CI L0c 门禁
（test_package/ 须有非 conanfile.py 的测试源文件，首轮 CI #62069 即挂此门禁）
迁入独立 test.sh，纪律不变（详见下节）。

## 真机验证记录（2026-09-26）

### 设备环境发现：OHOS 内核策略禁 execve 脚本

第一次真机 `conan-verify` G2 在 `./configure` 报 **Error 126 / Permission denied**。
逐层诊断（全部在设备上实测）：

| 探针 | 结果 | 结论 |
|------|------|------|
| `sh configure --version` | ✅ 正常 | 脚本内容/解释器完好 |
| `./configure`（0770，owner 有 x） | ❌ EACCES | 与 DAC 位无关 |
| `chmod 777` 后的新脚本 | ❌ 仍 EACCES | 与 DAC 位彻底无关 |
| 拷贝 /bin/sh 成 ELF 再 exec | ❌ EACCES | 连 ELF 也拒 |
| 通道1 上下文 16:14 构建的 ifconfig ELF | ✅ 可 exec | 标签来源决定一切 |

结论：OHOS `/storage` 挂载带 `hmmac=use_task,seclabel`，**文件按创建任务的
MAC 标签定生死**。本会话通道2（uid 20020084 应用沙箱域）创建的任何文件
（ELF 或脚本）都不可 exec；通道1（20001006 shell 域）创建的文件 ELF 可 exec。
另外，**shebang 脚本执行在全设备被禁**（tcl 8.6.16.1 在通道1 下同样
126 于 configure，40 处）——任何上下文 execve 脚本都 EACCES。

### 配方对策：解释器前缀全线绕行

1. `build()`：configure 改 `sh <源树绝对路径>/configure`，`cwd=self.build_folder`
   （conan 的 Autotools 出源构建布局：configure 用源树绝对路径、产物落
   build-release，否则 Makefile 生成在源树、autotools.make 找不到）。参数与
   Autotools 默认一致：`--prefix=/` + 各目录 `${prefix}` 字面量 +
   `--build/--host` 三元组。
2. make 规则内裸 exec 的脚本全部前缀化：
   - `update_mans`（help2man 链反引号裸跑 bin/aclocal）→ make/install 都传
     `man1_MANS=` 跳过再生，package() 原样拷贝 tarball 预生成手册页到
     share/man/man1；
   - `LOG_COMPILER`/`PL_LOG_COMPILER` → sed 生成后的 Makefile 加 `sh ` 前缀。
3. `_make_relocatable()` 包装脚本内部 `exec perl "$here/.X-real"`：包装经解释器
   前缀跑，perl 本体经 perl ELF 前缀执行，不触发 shebang execve；可重定位语义不变。
4. `test_package`：
   - generate() 显式 `VirtualBuildEnv`——conan 2 不会为 test_package 自动生成
     conanbuild（1.18 时代靠环境 PATH 里恰有系统 aclocal 蒙混过关，不可依赖）；
   - 工具调用全部 `sh <绝对路径>`：sh 的命令名查找会逐个 execve 探测 PATH 候选，
     conan 任务创建的脚本带 noexec 标签、探测即被内核吞掉（报 No such file or
     directory）；显式路径时 sh 直接打开文件读入，不触发 execve；
   - 依赖集按 `tested_reference_str` 全串索引 KeyError（conan 2 实测），
     直取失败按包名兜底；
   - `--add-missing` 加 `--copy`（真机内核拒绝 link() 硬链接）；
   - 最小 configure.ac 补 `AC_CONFIG_FILES([Makefile])`（automake 会正确报错）；
   - 四断言独立成 `test.sh`（CI L0c 要求 test_package/ 有非 conanfile.py 的
     测试源文件，首轮 CI #62069 即挂此门禁）；test() 经 `self.source_folder`
     绝对路径 `sh test.sh <bindir>` 驱动，工具调用纪律不变。

### 验证结果（2026-09-26）

**conan-verify 八门禁：全绿** ✅（G1 export_sources / G2 conan create 含
test_package / G3 平台矩阵、L4 checksec、L5 产物基线等全部通过，
result.json draft:false 上报，可标记 published）。

**test_package 消费者断言（真机实跑）**：4/4 —— aclocal/automake `--version`
输出正常；aclocal 在最小 configure.ac 上产出 aclocal.m4（宏目录接对）；
automake `--add-missing --copy` 在真实 Makefile.am 上产出 Makefile.in
（--libdir 可重定位接对）。断言已迁入 test.sh，test() 以 sh 绝对路径驱动，
CI 侧由 L1 test_package 复验。

**上游测试子集（29 例）**：1 PASS / 1 SKIP / 27 FAIL。
- PASS：`t/aclocal-no-install-no-mkdir.sh`
- SKIP：`t/libobj13.sh`（真机无 libtoolize）
- 27 例失败签名统一：`<工具脚本>: /data/service/hnp/bin/perl: bad interpreter:
  Permission denied`（exit 126），全部死在**第一次裸 exec 工具脚本**处
  （尚未执行到 ./configure，日志里的 configure 字样只是 set -x 追踪输出）。
  根因同第一节：内核在 shebang 解析层拒绝脚本 execve。即便工具调用修掉，
  后续 ./configure、config.status 同为脚本，且测试编译产物 ELF 由通道2 任务
  创建（noexec 标签）同样会被拒——上游 1304 例测试套件（list-of-tests.mk
  唯一文件名清点：1259 个 .sh + 13 个 .pl + 32 个 .tap）在本真机上
  **结构上无法原样跑通**，属平台限制而非包缺陷。本包真机功能证明以
  八门禁 + test_package 四断言 + 消费者端到端用例（见下）为准。

**消费者端到端用例（鸿蒙特有测试）**：`test_package/test_e2e.sh` +
`test_package/e2e-probe/` fixture（下游微型 autotools 工程：configure.ac /
Makefile.am / probe / configure）。真机无 autoconf（注册表与设备均不可用），
故 configure 按发行 tarball 惯例**随档提供**——手写最小发布式脚本，对
automake 生成的 Makefile.in 做 @VAR@ 替换；关键适配替换：INSTALL 系列带
`sh ./install-sh` 前缀（真机禁脚本 execve）、ACLOCAL/AUTOMAKE 从环境继承
sh 前缀绝对路径。全链路：aclocal → automake `--add-missing --copy --foreign`
→ `sh ./configure --prefix` → make → make check（并行 harness，LOG_COMPILER=sh
经 sh 执行 probe——不能用 TESTS_ENVIRONMENT=sh：它在 parallel harness 里被拼
到 LOG_DRIVER 前（am__check_pre 尾部），展开成 `sh /bin/sh ./test-driver`
即拿 sh 把二进制 /bin/sh 当脚本执行，真机实测踩过；LOG_DRIVER 由 automake
生成为 `$(SHELL) ./test-driver` 天然 sh 驱动）→ make install（bin_SCRIPTS
经 INSTALL 替换装进 prefix/bin）→ 运行已安装产物 probe 并核对输出
`probe-ok 1.0`。该用例已接入 test()（test.sh 之后执行），conan-verify
G2 与 CI L1 均复验。另：发行 tarball 时间戳惯例——configure 必须比
configure.ac/aclocal.m4 新（test_e2e.sh 在 automake 后 touch configure），
否则 make 的 `configure: configure.ac aclocal.m4` 重生成规则会用真机
/data/service/hnp 的 autoconf 2.72 覆盖发布式 configure。

**CI #62576 辅助文件污染坑（2026-09-27 实录）**：test.sh 原版直跑在
$PWD（=test_package 目录）且不清理，--add-missing 装的 install-sh/
missing 残留在 test_package 根目录；test_e2e.sh 的构建目录 e2e-work.$$
是其子目录，automake 的缺失文件搜索**向上查父目录**，找到残留后
"引用而不安装"（日志特征：不再打印 installing ./install-sh，且
test-driver 打印为 `installing '../test-driver'`）→ 构建目录缺
install-sh → make install 的 `INSTALL='sh ./install-sh'` 报
No such file or directory（Error 127）。真机单跑 E2E 无残留所以全绿，
CI 顺序跑必炸。修法（双保险）：
1. test.sh 断言迁入独立临时目录 test-sh-work.$$ + trap 清理（根治污染）；
2. test_e2e.sh 在 automake 后对 install-sh/missing/test-driver 做兜底——
   构建目录缺哪个就从 srcdir 拷入（srcdir 必须 `cd $(dirname $0) && pwd`
   绝对化：相对调用时脚本 cd 进构建目录后相对路径失效，真机复现过）。
真机三场景复验全绿（2026-09-27）：S1=test.sh+E2E 同目录顺序跑（run 目录
零残留）；S2=人工污染 install-sh/missing 后跑 E2E（复现 ../test-driver
父目录模式，兜底拷贝后 make install 命中）；S3=全新目录单跑 E2E。
