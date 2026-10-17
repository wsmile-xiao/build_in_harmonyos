# ppmd 20050811 适配笔记

## 软件背景

ppmd 是 Dmitry Shkarin 的 PPMd variant I 文件到文件压缩器（public domain）。
本包源码是 Debian 打补丁、FreeBSD ports 重打包的 `ppmd-20050811.tar.gz`
（README-PACKAGE：原始包 `ftp://ftp.elf.stuba.sk/pub/pc/pack/ppmdi1.rar`，
附加补丁来自 Debian unstable 的 ppmd 源码包）。下载镜像
`distfiles.macports.org/ppmd/`，SHA256
`81fc0cd13b1a6277959f52f9215e62ce71824ff652b28b2a754e469b9fa4ba22` 与
FreeBSD ports `archivers/ppmd/distinfo` 逐字一致。

上游 port 标注 `ONLY_FOR_ARCHS=i386`——这是本次适配两大功能缺陷的准确预告。

## 编译环境

- 构建系统: makefile（上游为 FreeBSD pmake 专属语法，补丁 0005 改写为 GNU make）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（profile `tools.build:compiler_executables`）
- 状态: built
- 外部依赖: 无（W0 预检：源码只包含标准 C/C++ 头文件；`conio.h`/`dos.h`/
  `windows.h` 全部在 `_WIN32_ENVIRONMENT_`/`_DOS32_ENVIRONMENT_` 条件块内，
  设备走默认 `_POSIX_ENVIRONMENT_` 分支）

## 编译步骤

1. init-build 下载并核对源码（sha256 逐字匹配）。
2. 原生探索：`clang++ -c -O2 PPMd.cpp Model.cpp` 直接编译，暴露补丁 0001 的
   编译错误；打包进配方后由 `make CXX=<cpp> CXXFLAGS="-O2" -j1` 构建
   （编译器按 R33 从 `tools.build:compiler_executables` 取 dict 再索引）。
3. `conan create` + test_package 消费者测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PPMd.cpp:426 `no matching literal operator for call to 'operator""__DATE__'` | C++11 把紧邻字符串字面量的 `__DATE__` 词法成 UDL 后缀 | 补丁 0001：字面量与宏之间加空格 |
| 2 | 编码即段错误（rc=139），产物 0 字节 | 子分配器粒度 `UNIT_SIZE=12` 假设 i386 的 4+4+4 布局；LP64 下 `PPM_CONTEXT`=20、`MEM_BLK`=24 字节，全部溢出单元边界 | 补丁 0002：LP64 下粒度=24（=3×sizeof(DWORD)），`U2B=UNIT_SIZE×NU`，`UnitsCpy` 按粒度逐字节拷贝；`PPM_CONTEXT`(20)≤24、2×`STATE`(20)≤24 保持"每单元 2 状态"的 `>>1` 寻址不变量 |
| 3 | 编码成功但解码首字节即错（文本 5375B 解出 6786B 乱码；tiny 75B 档案解出 NUL 开头 junk） | carryless 区间编码器状态 `DWORD low, code, range` 在 LP64 是 64 位：`range` 初值变 2^64-1，算法依赖的 32 位回绕失效，首个符号即失步 | 补丁 0003：`low/code/range` 与 `SUBRANGE` 计数钉死 `unsigned int` |
| 4 | 档案头会随宿主字长变成 24 字节（`ARC_INFO` 两个 DWORD 字段） | `fwrite(&ai,sizeof(ai))` 按结构体大小写盘 | 补丁 0004：`signature/attrib` 钉死 `unsigned int`，档案头保持 canonical 16 字节（od 实测 `8f af ac 84` 小端 magic） |
| 5 | `make` 直接报错（`.for` 循环与 `:C/\.o/\.cpp/` 替换是 BSD pmake 语法） | 上游 Makefile 面向 FreeBSD pmake | 补丁 0005：等价改写为普通 GNU make Makefile（pattern rules，`CXX?=/CXXFLAGS?=` 可由配方注入） |
| 6 | 采信轮 L2 smoke FAIL：探针 `--version/--help/-V/-h` 全部 rc=255 | 上游 CLI 没有发现旗标，用法错误按 `return -1`（255）退出；平台探针要求 rc=0（与 libgig「只实现小写 `-v`」同形态，见 notes/defects/ci-and-w3.md 第 5 类） | 补丁 0006：旗标为唯一参数时接受 `--version/-V`（打 banner）、`--help/-h`（打 usage）并退出 0；其余调用路径（含无参 255）保持上游行为不变 |
| 7 | 静默档与非静默档行为不一致的假象：解码提示 `overwrite?` 等待 stdin（测试挂死）、rc=255 | `TestAccessRare` 的交互提示在 EOF 时无 default 分支死循环；`-s` 下则静默删除重建 | 测试统一在干净目录跑（test.sh 每 scenario 独立 CWD）；上游交互行为不改 |

## 源码修改

见 `patches/0001`–`0006`（全部 patch_type: portability），对纯净树
`patch -p1` 逐个 dry-run+apply 验证通过，补丁链构建产物 sha256
`76fcdea0012d087a24521a13159b23032f202175cb0d0557d0498c50c2ef45f0` 与
手工修复构建行为一致。

## 依赖版本

无外部依赖（仅 libc/libc++）。

## 验证结果

- 本地探索矩阵（补丁链二进制）：small.txt(5375B)/big.txt(6.9MB)/bin.dat(55744B)×
  {默认, -o16 -m64, -o2 -m1, -r1 -o8, -r2 -o4 -m32} 全部 e=0 d=0 逐字节一致；
  big.txt 压缩率 6957768→596473（约 0.69 bpb），符合 PPMd 对文本的预期。
- 档案头 od 实测：`8f af ac 84 | b0 81 00 00 | 93 80 | 08 00` =
  canonical ppmdi1 16 字节头（magic/属性/info/FNLen）。
- test_package：23 项消费者断言（用法退出码、文本/二进制通往返、开关矩阵、
  档案头布局、bpb 统计行、-f/-d/通配符、损坏档案优雅拒绝），全部 PASS，
  详见 reports/conan-create.log 的 HMBS_TEST_SUMMARY。

## 上游测试清点（R51）

上游确无测试：tarball 共 11 个条目（2 个 .cpp、2 个 .hpp、2 个 .h、Makefile、
ppmd.1、read_me.txt、README-PACKAGE）；Makefile 无 check 目标；源码无 test/
目录、无 *test* 文件、无断言宏。故 N=0、N′=0（清点证据同
test_package/MANIFEST.yml），消费者断言 23 项单列不混入上游分母。

## 注意事项

- ppmd 是纯可执行包（`package_type="application"`），包内无 lib/，conan-verify
  的 G4/L2/L4/L5 自动门禁本轮已全部实跑（4/4）；应用包口径的人工补测写入
  `reports/conan-verify-supplement.md`（真实运行通往返 + readelf 动态段 +
  两条稳定聚合 sha256）。
- 与 32 位 ppmd/i386 实现生成的档案**字节兼容**（补丁 0004 保持 16 字节头），
  但本包从未与 i386 产物互测，不宣称互通。
- 解码目标文件名取自档案头，解码总是把文件写到 CWD；测试与脚本化使用时注意
  工作目录。
