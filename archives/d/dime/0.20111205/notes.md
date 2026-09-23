# dime 0.20111205 适配笔记

## 软件概况

- **dime** = "DXF Import, Manipulation and Export"，Coin3D 家族（Kongsberg/SINTEF）的
  C++ DXF 图形文件读写库。FreeCAD 等项目的 DXF 后端。
- 上游仓库：<https://github.com/coin3d/dime>（由 Bitbucket Mercurial 迁移而来）。
- 许可证：BSD-3-Clause（tarball 内 COPYING）。
- 构建系统：autoconf/automake + libtool 1.5.26（2008），tarball 自带预生成 configure，
  无需 autoreconf。
- 产物：`libdime`（`.so.0.0.0`/`.a`）+ `include/dime/` 头文件 + `dime.pc`。
  `dxf2vrml`/`dxfsphere` 是 `noinst_PROGRAMS` 示例程序，`make install` 不安装
  （bin/ 子目录不在顶层 SUBDIRS 中，其 coin-config 残留脚本也不会被安装）→
  纯库包，**无需 commands.json**。

## 版本来源（W0b 核验）

- 0.20111205 = 上游 2011-12-05 快照（hg r187，`hg archive` 生成）。
- GitHub 无对应 tag（仅 `dime-0.9.1` 2002 年与 `CI-builds`），等价 git commit 为
  **edcbe949ae67**（2011-12-04 "fixed issue #5"，快照日期前最后一笔提交）。
- **等价性证据**：GitHub `archive/edcbe949ae67.tar.gz` 与 Debian
  `dime_0.20111205.orig.tar.bz2`（sha256 `a5f1738d…eec5ce`）逐文件 sha256 对比：
  209 个公共文件全部一致，唯一差异为 `.hg_archival.txt`（hg archive 自动附加的
  元数据戳，非构建输入）。
- 选 GitHub URL 而非 Debian 池的原因：R39/PF7 禁止 Debian 域名与明文 http，
  GitHub 为官方上游且 https。

### GitHub codeload 封装不稳定（真机实证 2026-09-12）

`github.com/coin3d/dime/archive/edcbe949ae67.tar.gz`（302 → codeload）动态生成，
gzip 封装**非字节稳定**：同日两次观察得到两种哈希——

- `6d9f7d0c1ba20f5815c585a33589943d6ba969bc53587269b735c64703c9f3a6`（curl 直连，两次一致）
- `065a7d74d4e1f15244d3a467f8b92e37908f33d4824a528d468379ea868a9914`（conan Python 下载器）

两种封装**内容等价**（解包后抽查 configure / src/Input.cpp / include/dime/Base.h
sha256 与本地 GitHub 解包逐一相同；git tree 由 commit 决定，确定性）。对策：
`source()` 用 `download()` 落盘后显式校验 `_SOURCE_SHA256` 集合（两个已证变体），
不匹配即报错——**校验永不跳过**，只是接受同一棵树的两种已知封装。conandata 的
`sha256:` 保留主变体（CI 镜像链路产物）。若未来出现第三种封装，报错信息中已写明
核实与扩展方法。

## W0 依赖检查

**零外部依赖**：`requirements()` 为空。源码 include 只有标准 C/C++ 头
（stdio/stdlib/math/string/ctype）。configure 探测的 isinf/isnan/finite/fpclass
均由 libc 提供（HAVE_* 宏带回退分支）。→ 无需制品仓检查，无依赖阻塞。

## 构建系统分析与 OHOS 策略

沿用 **celt 1.0.0 已真机验证的 Autotools 模式**（同代 autoconf 生成的 configure）：

1. **config.guess/config.sub 是 2009 版**（无 aarch64、无 ohos）：实测
   `sh cfg/config.sub aarch64-unknown-linux-gnu` 通过 → 传
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu` 通用三元组，
   不修改 cfg/ 生成文件（R6）。
2. **链接器**：OHOS 只有 ld.lld，clang 不搜 PATH 找链接器 → configure 参数加
   `-fuse-ld=<ld.lld 绝对路径>`；build-local `bin/` 下补 `ld`/`ld.aarch64` 软链
   （`rm -f && ln -s` 语义，R5）供 make/libtool 探测。
3. **TMPDIR**：OHOS `/tmp` 只读 → patch 0001 让 configure 临时目录走 `$TMPDIR`
   （与 celt 0001 同思路，dime configure 第 21595 行同样的 `mktemp -d "./confXXXXXX"`）。
4. **configure 用 bash 跑**：OHOS `/bin/sh` 是 mksh，config.status 临时文件会炸
   → `self.run('bash <configure> <args>', env="conanbuild")`，参数从 generate()
   落盘的 configure_args.txt 重放。
5. **C++17**：profile 定 cppstd=17（-std=gnu++17），`register` 存储类在 C++17 被
   移除，clang 15 直接报错 → patch 0002 删除 src/Input.cpp 中 6 处 `register `
   （全库仅此 6 处）。
6. **库类型**：非系统同名库，默认静态（`--disable-shared --enable-static`，
   上游 AM_DISABLE_STATIC 默认只建共享，需显式启用静态）。用户可选 shared。
7. **libtool 1.5.26 风险**：静态构建路径只走 ar/ranlib，风险低；若真机验证暴露
   问题，备选方案是给 configure.ac 加 Debian debian-autoreconf 式改造并
   autoreconf（Debian 2.2 即此路线），当前不做。

## R51 上游测试清点（证据）

- `ls tests/` → 不存在 tests 目录。
- `grep -rn "TESTS\|check_PROGRAMS" */Makefile.am src/*/Makefile.am` → 无命中；
  automake 只生成空的 `check` 目标。
- 唯一可执行程序 dxf2vrml/dxfsphere 为 noinst 示例，无断言型测试。
- 结论：上游快照无测试套件，功能性覆盖由 test_package 冒烟测试承担
  （模型构造 → DXF 写出 → 读回 → 实体类型与 6 个坐标断言，17 项断言）。

## 补丁清单

| # | 文件 | 类型 | 说明 |
|---|------|------|------|
| 0001 | configure | portability | 临时目录优先用 $TMPDIR（OHOS /tmp 只读） |
| 0002 | src/Input.cpp | portability | 删除 C++17 移除的 register 存储类（6 处） |

两补丁已在 pristine 解包上 `git apply --check` + 实际 apply 验证通过。

## 本地已验证 / 待真机

已验证（本机 Windows）：
- 源码等价性与 sha256（见上）。
- 两补丁 apply 验证。
- conan export 通过；conanfile.py / test_package 语法检查通过。
- config.sub 三元组实测。

## 真机验证结果（2026-09-12，frp-tip.com 真机全绿）

环境：aarch64 OHOS，`ohos-aarch64-fixed` profile（clang-15 / libc++ / gnu++17，
工具链在 `$HOME/usr/local/bin`），隔离 `CONAN_HOME` + `TMPDIR`，`jobs=1` +
内存看门狗（900MB 阈值），与另一个 `swiftc -j1` 任务并行，MemAvailable 全程
8.6-8.9GB。最终 `conan create` exit 0，test_package PASS。

三轮修复记录（每轮均为一次性定位修复，无调参螺旋）：

1. **codeload 封装不稳定**：conan Python 下载器与 curl 拿到不同 gzip 哈希
   （内容相同）。对策：`source()` 用 `download()` 落盘后显式校验
   `_SOURCE_SHA256` 双变体集合，不匹配即报错（校验永不跳过）。
2. **2009 版 configure 拒绝 `-fuse-ld=` 命令行参数**（`unrecognized option`；
   celt 的 configure 较新不报此错）。对策：改经
   `tc.extra_cflags/extra_cxxflags/extra_ldflags` 注入——configure 的链接
   探测是编译+链接一步走，flag 经 CXXFLAGS 照样到达链接器。
3. **test_package 首跑失败（测试代码 bug，非库问题）**：`dimeOutput` 只在
   析构时 flush/关闭文件，同进程写完立刻读时磁盘上还是 0 字节，而
   `dimeInput::setFilePointer` 以 `filesize > 0` 为成功条件。对策：写阶段
   包进作用域块，析构先于读取发生。

产物核验：`lib/libdime.a`（601758 字节）+ `include/dime/` 全目录 +
`lib/pkgconfig/dime.pc`（内部版本串仍是上游 configure.ac 的 0.9.1，属预期；
Conan 包版本为 0.20111205）。package id
`5afd1f029b3a1a68998b4ec5f666f32767ce1532c`。

## 后续

- shadow CI 单包：`CI_PACKAGES="archives/d/dime/0.20111205" zsh ci/conan/build_and_test.sh`
- issue 与 PR 按流程在建（W2-W4 走 ohc-run.py finish/submit 或手动等价路径）。
