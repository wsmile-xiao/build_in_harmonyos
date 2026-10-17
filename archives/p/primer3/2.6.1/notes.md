# primer3 2.6.1 适配笔记

## 编译环境
- 构建系统: makefile（上游 tarball 顶层无 configure，非 autotools；Makefile 在 src/ 子目录）
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / clang++ / llvm-ar / llvm-ranlib
- 状态: built（conan-verify 八门禁通过，未 upload；待主任务审计后提交 PR）

## 源码信息
- 上游: https://github.com/primer3-org/primer3 tag v2.6.1
- 官方 tarball: https://github.com/primer3-org/primer3/archive/refs/tags/v2.6.1.tar.gz
- sha256: 805cef7ef39607cd40f0f5bb8b32e35e20007153a0a55131dd430ce644c8fb9e（GitHub 直连实测一致，本地曾用 ghfast 镜像下载同一内容）
- 许可证: GPL-2.0（源码 LICENSE 文件实测；src/Makefile 头部声明 GPL v2；另有 LICENSE_GPL3_for_Amplicon3 单独覆盖 amplicon3 部分）

## 编译步骤

零补丁适配（无任何源码修改），全部通过 Makefile 变量注入完成交叉编译：

```bash
# 完整 tarball 解压后（注意 Makefile 在 src/ 子目录，顶层无 configure）：
cd primer3-2.6.1/src
make clean
make -j2 CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
     AR=llvm-ar RANLIB=llvm-ranlib
# 产物：7 可执行（primer3_core ntdpal ntthal oligotm amplicon3_core
#       long_seq_tm_test primer3_masker）+ 7 静态库（libprimer3 libdpal libthal
#       libthalpara liboligotm libamplicontm libmasker）
```

Conan 配方（Makefile 类型，R33 合规）：
- `source()`: `get(self, **self.conan_data["sources"], strip_root=True)` —— 解压后为完整结构（src/ 在根下）
- `build()`: `make -C <source_folder>/src CC=... CXX=... AR=llvm-ar RANLIB=llvm-ranlib -j2`，编译器路径取自 `self.conf.get("tools.build:compiler_executables")`（dict），不碰 shell 环境变量
- `package()`: 手动 copy —— 7 exe→bin/、7 .a→lib/、11 .h→include/（上游 install 只装 EXES，库与头不装）
- `package_info()`: `cpp_info.libs = [primer3, dpal, thal, thalpara, oligotm, amplicontm, masker]`（静态链接顺序：libprimer3 引用 dpal/thal/thalpara/oligotm 符号，被依赖者靠后）

上游测试（完整结构、perl 5.42.0）：
```bash
cd test && make test   # exit 0，218 个 [OK]，0 FAILED
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `self.conf.get("tools.build:compiler_executables:c", check_type=str)` 抛 `does not exist in configuration list` | OHOS 适配版 conan 2.29.1 对 conf 子键严格校验，`compiler_executables` 是 dict 型 conf，按子键取值不在白名单 | 改为整体读取 dict 再 `.get("c")/`.get("cpp")`；AR/RANLIB 直接用 `llvm-ar`/`llvm-ranlib`（buildenv PATH 含 /data/service/hnp/bin） |
| 2 | `make -C src` 报 `src: No such file or directory` | basic_layout 下 build() 的 cwd 是 `build-release/` 子目录，而源码（含 src/）在 source_folder 根 | `make -C "<self.source_folder>/src"` 用绝对路径（E350 类坑：conan create 从 conandata 官方 tarball 解压是完整结构，Makefile 在 primer3-2.6.1/src/，不能照抄 .work 提升版路径） |
| 3 | `from conan.tools.can_run import can_run` 模块不存在 | 该 conan 版本 can_run 位于 `conan.tools.build` | `from conan.tools.build import can_run` |
| 4 | clang 警告 `-ffloat-store` is not supported | 上游 thal.c/thal_parameters.c 用 x87 浮点精度 flag（x86 专用） | 无需处理：clang 忽略该 flag 仅告警；上游测试浮点输出与参考一致（218 项全过），零补丁 |
| 5 | primer3_core 最简输入报 `PRIMER_ERROR=SEQUENCE_INCLUDED_REGION length < min PRIMER_PRODUCT_SIZE_RANGE` | 70bp 模板短于默认产物尺寸范围 | test_package 的 Boulder 输入改用上游 example 同款记录（120bp 模板 + PRODUCT_SIZE_RANGE=75-150），稳定产出 PRIMER_PAIR_0_PRODUCT_SIZE=104 |
| 6 | 上游 `install` 目标只装 7 个 EXES，不装库/头文件 | 上游定位工具发行，库非官方分发形态 | conanfile package() 手动 copy 7 exe + 7 .a + 11 .h |
| 7 | conan-verify 报 `归档目录不存在: <SKILL_ROOT>/archives/...` | ohc-run.py 项目根定位落到 SKILL 安装目录（E351） | `export OHC_PROJECT_DIR=<repo 根>` 后重跑 |

## 源码修改

无（零补丁适配）。conandata.yml `patches: {}`。

## 依赖版本

- 无第三方运行时/编译依赖（requirements() 为空；Makefile LDLIBS 仅 -lm，musl libc 自带）
- conan 2.29.1（OHOS 适配版）、cmake（test_package 用）、perl 5.42.0（上游测试用）

## 验证结果

```bash
# conan create（OHOS arm64 profile）：
$ conan create archives/p/primer3/2.6.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...
primer3/2.6.1: package(): Packaged 7 files        # bin/ 7 个可执行
primer3/2.6.1: package(): Packaged 7 '.a' files    # lib/ 7 个静态库
primer3/2.6.1: package(): Packaged 11 '.h' files   # include/ 11 个公共头
libprimer3 API OK: default opt_size=20, after set_gs_primer_opt_size(22): 22
oligotm API OK: Tm=69.605221 ...
ALL primer3 LIBRARY TESTS PASSED
primer3_core boulder IO OK: PRIMER_PAIR_0_PRODUCT_SIZE=104

# conan-verify 八门禁：G0/G1/G2/G3/G4/L2/L4/L5 全 PASS（reports/conan-verify-report.md）

# L1e 破坏性反证（临时改断言 needle 为不存在字符串）：
Exception: FAIL: primer3_core output missing expected key 'XPRIMER_LEFT_X_L1E_NEGATIVE_TEST'
→ conan create 退出码 1，测试真实有效；恢复后 PASS

# L2 smoke / L4 安全：
$ primer3_core --about → libprimer3 release 2.6.1
$ llvm-readelf: Type=DYN(PIE), FLAGS BIND_NOW, FLAGS_1 NOW PIE

# 上游测试：
$ cd test && make test → exit 0，218 [OK]，0 FAILED（八段全跑，p3test.pl 450s）
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/p/primer3/2.6.1/conanfile.py | Conan 配方（Makefile 类型，零补丁） |
| archives/p/primer3/2.6.1/conandata.yml | 官方源 URL + sha256 |
| archives/p/primer3/2.6.1/test_package/ | 消费者测试（真实 API + Boulder IO + L1e 反证通过） |
| archives/p/primer3/2.6.1/reports/test-report.md | 上游测试报告（218/218） |
| archives/p/primer3/README.md、manifest.yaml、commands.json | 软件级三件套（7 个 CLI 全声明） |

## 注意事项

1. **E350 类坑**：本地探索目录 `~/tmp/builds/primer3-2.6.1.work/` 是 src/ 提升后的结构，但 conan create 从 conandata 官方 tarball 解压是完整结构（Makefile 在 primer3-2.6.1/src/）——build() 必须按完整结构写（`make -C <source>/src`），勿照抄 .work 路径。
2. libprimer3.cc 是唯一 C++ 源（-std=c++11）；消费方链接 libprimer3.a 必须用 C++ 链接器（test_package 的 CMake 设 `LINKER_LANGUAGE CXX`）。
3. `p3_create_global_settings()` 存在但无对应公开 free 函数（上游 API 如此）；测试程序以进程退出回收，不影响验证。
4. kmer_lists/ 与 src/primer3_config/ 热力学参数文件默认不打包——最简 Boulder IO 不需要；如下游需要 thermodynamic alignment 或物种掩蔽，须另行 `--path` 指定（保持包体积最小）。
5. 分支 feat/primer3-2.6.1 本地提交，未 push、未建 PR（等主任务统一审计）。
---

**编译结束**: 2026-09-04 14:38
**最终状态**: built
