# irstlm 6.00.05 适配笔记

## 编译环境
- 构建系统: autotools（GitHub tag tarball 不含生成文件，需 autoreconf 自举）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ (15.0.4, OHOS SDK)
- 状态: built

## 编译步骤

```bash
# 1. 获取官方源码（GitHub tag v6.00.05）
curl -sSL -o irstlm-6.00.05.tar.gz \
  https://github.com/irstlm-team/irstlm/archive/refs/tags/v6.00.05.tar.gz
sha256sum irstlm-6.00.05.tar.gz   # 0d0ca97a58351710f3bca8a43bdcca880dbc766a1f73389b359b4df6357df9ec

# 2. 配方 build() 内自举 autotools（tarball 无 configure）
#    autoreconf -fi  # 生成 configure/config.guess/config.sub

# 3. 修复生成的 configure（E114: 去掉 umask 077，否则 config.status 临时目录不可写）
#    将 umask 077 改为 umask 022

# 4. configure（显式三元组跳过 config.guess 的 HarmonyOS 识别失败）
./configure --prefix=/ --disable-doc --enable-static --disable-shared \
  --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos

# 5. 编译（-j1 规避 HMDFS jobserver fifo EPERM, E074）
make -j1

# 6. 安装
make install DESTDIR=<package_dir>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub tag tarball 无 configure | autotools 生成文件不入 git | 配方 build() 先 `autoreconf -fi`（tool_requires automake/1.18 + libtool/2.5.4） |
| 2 | config.guess 无法识别 HarmonyOS（uname -s=HarmonyOS） | E007 | 显式 `--build/--host=aarch64-unknown-linux-ohos`（config.sub 支持 *-linux-ohos） |
| 3 | config.status 临时目录 Permission denied（drwx--S---） | E114: HMDFS umask 077 | 生成的 configure 中 umask 077 → 022 |
| 4 | `invalid argument '-std=c++0x' not allowed with 'C'` | 上游 configure.ac 把 -std=c++0x 注入 CPPFLAGS，C 源（cmd.c/thpool.c）被误用 C++ 标志 | 补丁 0002: 移到 CXXFLAGS |
| 5 | `install-exec-hook: ln -s lib lib64 Permission denied` | prefix=/ 时在根目录创建软链无权限 | 补丁 0001: 移除 install-exec-hook |
| 6 | 链接错误 undefined symbol: gzopen/gzclose/gzread | 上游无条件 -lz（mfstream.cpp/gzfilebuf.h） | 配方声明 `self.requires("zlib/1.3.1")` |
| 7 | make/ctest jobserver mkfifo: Operation not permitted | E074: HMDFS fifo | make -j1 / ctest -j1 |
| 8 | test_package 编译失败 iostream not found | 消费者测试误用 C 项目编译 C++ | test_package 改 project CXX + test.cpp |

## 源码修改

| 补丁 | 内容 |
|------|------|
| patches/0001-Makefile.am.patch | 移除 install-exec-hook（lib→lib64 软链，prefix=/ 时 Permission denied） |
| patches/0002-configure.ac.patch | -std=c++0x 从 CPPFLAGS 移到 CXXFLAGS（避免 C 源被加 C++ 标志） |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| zlib | 1.3.1 | ohpcd 制品仓（configure.ac 无条件 -lz） |
| automake (tool) | 1.18 | ohpcd 制品仓（autoreconf 自举） |
| libtool (tool) | 2.5.4 | ohpcd 制品仓（autoreconf 自举） |

## 上游测试枚举台账（双口径）

irstlm 6.00.05 官方 tag 源码（135 个文件）清点结果：

| 类别 | 入口 | 是否独立上游用例 | 是否运行 | 结果/原因 |
|------|------|------------------|----------|-----------|
| tests/ 目录 | 无 | — | — | 官方 tag 不含任何 tests/ 目录 |
| ctest 注册 | 无 | — | — | CMakeLists.txt 无 enable_testing/add_test |
| Makefile.am TESTS | 无 | — | — | 根/src/scripts Makefile.am 均无 TESTS 目标 |
| make check | 空操作 | — | 已运行 | `make check` 全部 "Nothing to be done for 'check'"，exit 0 |
| 用户测试源 | 无 | — | — | 无独立 TEST_CASE 文件 |
| doc/regressionTests.tex | 文档 | 否 | 未运行 | 仅为 LaTeX 文档（描述回归测试思路），非可执行用例 |
| 框架头/源码 | 无 | — | — | 无单测框架（无 gtest/catch） |

- `source_declared_total` = 0（官方 tag 源码中无可复制枚举的独立测试声明）
- `configured_executable_total` = 0
- `executed_passed_total` = 0
- 未运行/未实例化 = 0
- 全量通过率 = 0/0（无分母，按源码声明 0 例如实上报）
- 清点证据：`tar -tzf irstlm-6.00.05.tar.gz`（135 文件）+ 全目录 `find -iname "*test*"` 仅命中 doc/regressionTests.tex + `grep -rn "TESTS\|check" Makefile.am src/Makefile.am` 无测试目标

## 鸿蒙专项测试（真实可执行，非空壳）

基于编译产物（compile-lm/score-lm CLI）的端到端用例：

```bash
# 构建小型 ARPA 语言模型并编译为 IRSTLM 二进制格式
$BIN/compile-lm sample.arpa sample.blm
# → 输出 "Saving in bin format to sample.blm"，exit 0，产出 28 字节 .blm

# 用编译后的模型对句子打分（真实调用公开 API 链路）
printf 'hello world\n' | $BIN/score-lm -lm=sample.blm
# → 输出 "-14"，exit 0
```

- 消费者用例（test_package/test.cpp）：通过公开头文件 dictionary.h 调用 encode/decode/size 公开 API，`conan create` 内实际编译链接运行，ctest 1/1 Passed

## 验证结果

```bash
# conan-verify 8 道门禁
python3 scripts/ohc-run.py conan-verify irstlm 6.00.05
# → G0/G1/G2(conan create+test_package 1/1)/G3/G4/L2/L4/L5 全部 PASS

# finish W3 本地 CI 模拟
python3 scripts/ohc-run.py finish irstlm 6.00.05 built
# → L0(Junk/KC)/L1(test_package)/L2/L4/L5 全部 pass，Pass rate 100%
# → .ci-result.json 已写入（exit_code=0, log_sha256=9bb6abd8...）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方（autoreconf 自举 + OHOS 三元组 + umask 修复 + zlib 依赖） |
| conandata.yml | 官方 GitHub 源 + SHA-256 + 2 个补丁声明 |
| patches/0001-Makefile.am.patch | 移除 install-exec-hook |
| patches/0002-configure.ac.patch | cxx0 标志移入 CXXFLAGS |
| test_package/ | 消费者测试（test.cpp，dictionary 公开 API 往返验证） |
| manifest.yaml | 编译元数据（built） |

## 注意事项

- GitHub tag tarball 无 autotools 生成文件是此类配方的普遍形态，必须 autoreconf 自举
- HMDFS 的 umask 077 + jobserver fifo 两个问题在每次 configure/make 时都会触发，配方内已固化修复
- commands.json：irstlm 产出 13 个 CLI 工具（dict/ngt/compile-lm/score-lm 等），软件级 commands.json 随 PR 一并交付（R38）
- 基线隔离：W3 JC full 模式命中其他库（cloog/kics）的提交前基线空文件（.build-closed/.staging-verified），已隔离复验并原样恢复（pre/post sha256 均 e3b0c442 空文件），未写入本 PR

---

**编译结束**: 2026-09-21 01:31
**最终状态**: built
