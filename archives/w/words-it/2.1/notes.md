# words-it 2.1 adaptation notes

`words-it` is the distribution package version. Its immutable input is GNU
Aspell Italian dictionary release `2.2_20050523-0`.

The recipe decodes the upstream `it.cwl` prezip v2 file without an Aspell
installation. Aspell records the source words as ISO-8859-15; the package
converts those records to UTF-8, sorts and deduplicates them, and verifies the
expected 92034 entries before packaging `share/dict/words-it`. Conan build and
run environments expose the installed file through `WORDS_IT_FILE`.

### 上游测试清点（R51）

清点对象是官方源码归档 `aspell6-it-2.2_20050523-0.tar.bz2`，SHA-256 为
`3b19dc709924783c8d87111aa9653dc6c000e845183778abee750215d83aaebd`，与
`conandata.yml` 一致。对该归档执行 `tar -tf` 共列出 22 个成员；源码树
`aspell6-it-2.2_20050523-0/` 中没有 `tests/` 目录，也没有测试源文件。

注册测试清点：`Makefile.pre` 没有 `test` 或 `check` target，归档中也没有
CTest 或 pytest 注册。`Makefile.pre` 的 `distcheck` 是独立的打包构建检查，
其 recipe 仅重新解包分发归档，再运行 `./configure && make`，不执行测试程序
或断言，因此不计为上游功能测试。上游功能测试总数为 0，没有可运行的上游
测试用例；对应清点依据也记录在 `test_package/MANIFEST.yml`。

适配后的 Conan 消费者测试检查词表内容和缺失文件行为。另一个测试只在
HarmonyOS AArch64 上编译，验证 Conan run 环境提供的安装路径并读取 UTF-8
词表。

### 对话 #1

2026-09-30：用户要求将 words-it 2.1 移植到 HarmonyOS PC，基于 upstream/main 的 feat/words-it-2.1 分支，归档至本目录，并完成 AArch64 本地 CI、Conan 测试和至少一项鸿蒙特有测试。用户提供 HarmonyOS 6.0 AArch64 真机用于运行测试。

验证记录：Conan test_package 在 HarmonyOS AArch64 上通过，包含专用 OHOS 测试；仓库 v12.20 门禁套件因测试固定设备 Git 路径未能在 Windows 执行，转到真机后 33/33 通过。数据包的官方发布归档已由仓库 PackageBuilder 生成，并在真机解包验证词条数、UTF-8、排序、唯一性和许可证文件。
---

**编译结束**: 2026-09-30 12:00
**最终状态**: built
