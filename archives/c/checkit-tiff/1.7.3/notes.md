# checkit-tiff 1.7.3 适配笔记

## 编译环境
- 构建系统: cmake (Ninja generator)
- 编译日期: 2026-09-07
- 编译器: clang/clang++ (OHOS SDK 15.0.4)
- 状态: built (本地交叉编译验证通过，aarch64-ohos)

## 编译步骤

源码通过 git 获取（上游仓库 git.fsfe.org 位于 Anubis 反爬保护之后，Web UI 不可直达，
但 git 协议可用），在 conan recipe 的 source() 中：

```bash
git clone https://git.fsfe.org/art1pirat/checkit_tiff.git _clone
git -C _clone checkout 6e8084b5ae6225162ae9947368e3db8d995ae7b5   # tag v1.7.3
```

顶层 CMakeLists.txt 位于 `src/` 子目录，其 install 规则引用 repo 根的
`../example_configs`、`../tiffs_should_*`，因此整库 clone 进 source_folder，
configure 用 `-S src/`：

```bash
cmake -G Ninja -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
  -DPCRE2_INCLUDE_DIR=$OHOS_PCRE2/include \
  -DPCRE2_LIBRARY=$OHOS_PCRE2/lib/libpcre2-8.a \
  -DPCRE2_POSIX_LIBRARY=$OHOS_PCRE2/lib/libpcre2-posix.a \
  -DCMAKE_BUILD_TYPE=Release <src>
cmake --build build/Release
cmake --install build/Release --prefix $PACKAGE
```

依赖 pcre2/10.47（aarch64 预编译包）。RefIccMAX 未安装时自动禁用
完整 ICC 校验（可选依赖，安全跳过）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ld.lld: unable to find library -llibpcre2-8` / `-lC:/.../libpcre2-posix.a` | 上游 src/CMakeLists.txt 用 `get_filename_component(... NAME_WE)` 拼 `-l${...}`，NAME_WE 保留 `lib` 前缀导致 `-l` 变成 `-llibpcre2-8`；POSIX 全路径又被当作 `-l` 库名 | 补丁 0001：把 PCRE2_LDFLAGS/PCRE2_STATIC_LDFLAGS 改为 `-L;${PCRE2_LIBDIR}`，库引用走全路径的 PCRE2_LIBRARIES |
| 2 | source() 第二次 build 报 "destination path '.' already exists" | conan 复用 cache source 目录，`git clone target="."` 遇非空目录失败；克隆到 "." 也覆盖了 export_sources 拷入的 patches/ | 不强求 clone 到空目录，先清空子项后再 clone；随后发现会连带清掉 patches/，改为 clone 到临时子目录 `_clone` 再合并回 source_folder，保留 patches/ |
| 3 | `apply_conandata_patches` 报 patches 文件不存在 | patches 在 export_sources（source_folder 顶层），被 git clone "." 覆盖 | 同 2：clone 用临时目录合并 |
| 4 | test_package 中 `find_program(checkit_tiff REQUIRED)` 失败 | host 机器 PATH 上没有 OHOS 目标可执行，且 can_run=False 本就不该跑 | test_package 改为纯 conan 模式：can_run() 时才 `checkit_tiff -h`（上游 print help 后 exit 0），cross 环境跳过 |
| 5 | Windows 无 sh 时 CMake "MinGW Makefiles" 生成器不可用 | CMakeConfigure 检测到 `CMAKE_SH-NOTFOUND` | recipe 强制 `tc.generator = "Ninja"`（本机 WinLibs 自带 ninja） |
| 6 | Windows 上 source() 直接 `shutil.rmtree(source_folder)` 抛 PermissionError | source() 以 source_folder 为 cwd，目录自身被进程占用 | 只删除子项，保留 source_folder 本体；后续改成整体避免删除 source_folder |
| 7 | L1c 质量门禁 + rule4 要求上游 5 个用例真实执行，但实测 0/5 | ① 误判 OHOS armv8 为交叉编译，用 `shutil.which("qemu-aarch64")` 探测；而 CI worker 的 host profile 与 build profile 完全一致（os=OHOS os.version=6.0 arch=armv8），是**原生**构建，根本不需要 qemu，于是走 warning 分支静默跳过；② 即使跑了 ctest，t/Testcall.pm 把可执行文件硬编码为 `../build/<exe>`（相对 `t/`，即 `<source>/build`），而 conan 编在 `<b>/build/Release`，Perl 用例 exec 不到二进制 | ① 改用 `can_run(self)` 判定（原生即执行，跨架构才跳过并显式 warning，不再静默）；② 把刚编出的 3 个可执行文件暂存到 `<source>/build/` 以匹配上游硬编码路径；③ `self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanbuild")`，非零退出直接中断 conan create |
| 8 | 上游 4 个 Perl 用例起不来（`open3: exec of ../build/checkit_tiff ... failed` 之外的第二层依赖） | 上游 t/*.t 依赖两个非 perl core 的 CPAN 模块：`File::Slurp`、`Data::Printer`。CI worker perl 5.42、Ubuntu perl 5.34 实测均缺失 | recipe 写出最小纯 perl 实现并经 `PERL5LIB` 注入（`File::Slurp` 仅用 read_file/write_file；`Data::Printer` 仅用 `p()`，且只在断言已失败后打印 stderr，不影响判定）。**不修改任何上游测试文件**，断言全部保持上游原样 |
| 9 | `package()` 抛 `AttributeError: 'CheckitTiffConan' object has no attribute 'copy'`，CI 红灯 | Conan 2 的 `ConanFile` 没有 `self.copy`（那是 Conan 1 API），必须 `from conan.tools.files import copy` 后用模块函数 | 改用 `copy(self, ...)`；同时删掉原先 if/else 两分支完全相同的死代码 |
| 10 | 修完 9 后 `bin/` 仍只有 `checkit_tiff`，另两个可执行文件丢失 | `conan.tools.files.copy()` 的 `dst` 是**字面路径**，不像 Conan 1 的 `self.copy()` 会相对 `package_folder` 解析；`dst="bin"` 被写到进程 cwd 下的 `./bin` | 传入绝对路径 `dst=os.path.join(self.package_folder, "bin")`，并打印实际拷贝文件数便于核对 |
| 11 | `checkit_check_config` 的 2 个 E2E 断言是空壳（恒真/恒假） | 该程序**只从 stdin 读配置，完全忽略 argv**（上游 t/Testcall.pm 也是用管道喂）；且解析器需要行尾换行才能判定 regex 非法。原 `checkit_check_config '270; mandatory; regex("^test.*")'` 形式下 stdin 为空，连垃圾输入都返回 0 | 改为 `printf '%s\n' '<grammar>' \| checkit_check_config`（与上游 Testcall.pm 一致），并补一条"合法语法必须被接受"的反向对照，防止工具不可用时假通过 |
| 12 | `patches/0001-*.patch` 缺文件末尾换行 | 上游 blob 为 LF、补丁为 LF，但补丁最后一行 `else()` 后无 `\n`，GNU patch 报 "unexpectedly ends in middle of line" 并拒绝 hunk | 补齐末尾换行。conan 走 `git apply`（更宽容）所以 CI 未暴露，但这是 POSIX 文本文件硬性要求，且会让任何用 GNU patch 的复现失败 |

## 源码修改

- `patches/0001-fix-pcre2-static-link.patch`
  - src/CMakeLists.txt：PCRE2_LDFLAGS、PCRE2_STATIC_LDFLAGS 不再用 NAME_WE 拼
    `-l${name}`（产生 `-llibpcre2-8`），改为 `-L;${PCRE2_LIBDIR}`，静态库以全路径
    PCRE2_LIBRARIES 上链接线。

## 依赖版本

- pcre2/10.47 (aarch64-ohos 预编译包，含 libpcre2-8.a / libpcre2-posix.a)
- 本机构建侧：cmake 4.4.3、ninja (WinLibs)、OHOS SDK clang 15.0.4

## 验证结果

```bash
# 门禁脚本（同源，CI 实际执行的那一份）
CI_PACKAGES="archives/c/checkit-tiff/1.7.3" zsh ci/conan/build_and_test.sh
# -> GATE_RC=0
#    L0_RESULT=pass  L1_RESULT=pass(upstream tests + test_package executed)
#    L2_RESULT=pass  L4_RESULT=pass  L5_RESULT=pass
#    L1c: Upstream official tests (ctest) executed in build phase
#    L1e: Negative test (R34) confirmed - test genuinely depends on checkit-tiff
#    Build Summary: Total 1 / Success 1 / Pass rate 100.0% (1/1)

# 单独 conan create（原生 profile，can_run()=True，与 worker 同为原生）
conan create archives/c/checkit-tiff/1.7.3 -pr default --build=missing   # exit 0
```

上游 5 个用例实测（ctest 原文）：

```
1/5 Test #1: 01_test_stack ....................   Passed
2/5 Test #2: 01_grammar .......................   Passed    (181 断言)
3/5 Test #3: 02_config ........................   Passed    (8 断言)
4/5 Test #4: 03_validfiles ....................   Passed    (13 断言)
5/5 Test #5: 03_invalidfiles ..................   Passed    (36 断言)
100% tests passed, 0 tests failed out of 5
```

test_package 消费者侧 E2E：6 条断言全 PASS（合法 baseline / PCRE2 正匹配拒绝 /
regex 语法接受 / 白名单拒绝 / PCRE2 负匹配拒绝 / 无效 regex 拒绝 / 合法语法对照接受）。

打包交付物：`bin/{checkit_tiff, checkit_check_config, checkit_tiff_risk}` +
`share/checkit_tiff/{example_configs, tiffs_should_pass, tiffs_should_fail}`。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | - | conan recipe (application, git source, pcre2 deps, Ninja, ctest in build) |
| conandata.yml | - | sources url+commit，patches 0.1 注册 |
| patches/0001-fix-pcre2-static-link.patch | - | 修复上游 PCRE2 静态链接标志 |
| test_package/conanfile.py | - | can_run 时运行 test.sh (6 条 E2E 断言) |
| test_package/test.sh | - | E2E 消费者用例：baseline/正匹配/regex 语法接受/白名单拒绝/负匹配/无效 regex 拒绝 |
| test_package/MANIFEST.yml | - | 上游 5 测试 (239 断言) + test_package E2E 声明 |
| manifest.yaml | - | 版本元数据 + 知识沉淀 |

## 注意事项

- 上游 CMakeLists 里 `src/CMakeLists.txt` 的 PCRE2 显式变量分支（
  PCRE2_INCLUDE_DIR/PCRE2_LIBRARY/PCRE2_POSIX_LIBRARY）是作者预留的无 pkg-config
  配置路径，recipe 直接利用，免于引入 pkgconf。
- `execute_process(git ...)` 取版本号要求源码目录带 .git，git source 模式天然满足。
- 顶层 CMakeLists 用 `file(GLOB ...)` 收集 src/lib/ 下的子目录源码，patch 不改动它。
- 该仓库在 git.fsfe.org，git 协议可用但 Web 不可直达；CI 不依赖 Anubis。
- CI worker 的 host profile 与 build profile 一致（os=OHOS os.version=6.0 arch=armv8），
  是原生构建，`can_run(self)` 为 True，上游 5 个用例直接本机执行，**不需要 qemu**。
  `find_package(Perl)` 在 worker 上命中 `/data/service/hnp/bin/perl` 5.42，ctest 才会注册全部 5 个用例。

---

**编译结束**: 2026-09-26
**最终状态**: built (with upstream tests + E2E test_package)