# inform6-library 6.12.6 适配笔记

## 上游与产物

- 上游发行包 `inform6lib-6.12.6.zip`（IF Archive library/old/ 目录，2022-02
  发布）：Inform 6 标准库，纯文本 Inform 语言头文件 + 文档，无任何编译产物。
  sha256=653b7613...8b124 实测。
- 14 个文件：8 个库头（`english.h` 语言定义、`grammar.h` 语法、`infglk.h`
  Glk 接口自动生成、`infix.h`、`linklpa.h`、`parser.h` 解析器、`verblib.h`
  动词库、`version.h` 版本常量）+ 6 个文档/许可证（ARTISTIC、COPYING、
  README.txt、ChangeLog、caveats.txt、voices_and_tenses.txt）。
- 许可证：Artistic License 2.0（`ARTISTIC` + `COPYING`）。
- Debian/Ubuntu 同源打包：`inform6-library` 为 `all` 架构纯数据包，安装到
  `/usr/share/inform6/library/` —— 本包布局沿用该惯例。

## OHOS 适配

纯数据包，无编译无链接（kicad-demos 范式）：

- `build()` 仅做防漂移清单校验：14 个文件逐个在位 + 总数断言；
- `package()` 整树复制到 `share/inform6/library/`，许可证另存 `licenses/`；
- `package_id` 清空（数据包与 settings 无关）；
- `cpp_info.resdirs` 暴露资源目录，`runenv_info` 定义 `INFORM6_LIBRARY_DIR`。

与编译器包 `inform6/6.44-r7` 的关系：后者内置标准库 **6.12.8**，装在
`share/inform6/std/{lib,include}`；本包 6.12.6 装在 `share/inform6/library/`，
路径独立、互不覆盖。消费者用 inform6 编译器的命令行 `+目录` 参数或源内
`+include_path` 指令指向本目录即可（见 inform6 包测试用例同款用法）。

## 上游数据勘误（实报）

- `grammar.h` 头注释自述 "Release 6.12.5"——上游 6.12.6 发行包内的陈旧
  注释未同步（其余 6 个头文件均为 6.12.6，序列号 220219 一致）。本包不
  修补（保持与官方发行逐字节一致），探针以序列号断言。
- `infglk.h` 为 `parse_dispatch.py` 自动生成文件（Glk API 0.7.5），无版本
  注释行，探针改以生成器标记 + `System_file` 指令断言。

## 测试口径

上游发行 zip 无测试套件（纯数据，R51 清点证据：zip 内无 tests/ 目录、
无测试目标；库的功能验证即"交给 inform6 编译器编译游戏"，属编译器包
测试范围）。适配后消费者探针（test_package/inform6lib_probe.cpp）：

1. 目录清单：14 文件（8 头 + 6 文档）精确计数；
2. 8 个头文件逐个在位、非空、尺寸合理（>100 字节）；
3. 逐文件发行标记：version.h 的 `LibRelease "6.12.6"`/`LIBRARY_VERSION
   612`、english.h 语言定义头与 `parserm`、其余头文件序列号 220219、
   infglk.h 生成器标记；
4. ARTISTIC 为 Artistic License 2.0 文本；
5. 截断注入负向用例（写入→清理，证明探针路径真实读写包目录）。

## 真机验证（鸿蒙侧，2026-09-25）

`python3 scripts/ohc-run.py conan-verify inform6-library 6.12.6`
（华为 PC 真机，Conan 2.29.1 + ohos-aarch64 profile）：
**八道门禁全过**，判定「配方验证通过，可标记 status: published」。

- G0 ✅（构建系统 unknown，跳过预查询）
- G1 ✅ 配方完整性（name/version/source/build/package/package_info/export_sources/补丁应用调用/conandata/test_package 全项）
- G2 ✅ conan create 干净构建（真机实跑，含 test_package 探针）
- G3 ✅ 系统同名库隔离（R26）
- G4 ✅ 产物完整性
- L2/L4/L5 ✅（纯数据包无 cache 路径，跳过）
- 探针真机输出：`inform6lib_probe: all assertions passed`（5 组断言全过，逐项 [OK] 见 reports/conan-create.log）

产物实测：`share/inform6/library/` 精确 14 文件（8 头 + 6 文档）、
`licenses/` 2 文件（ARTISTIC + COPYING），无多余文件混入。

配方层要点（真机实证）：
- conan 2 basic_layout 在 package() 期间 `self.source_folder` 指向**构建目录
  b/**（而非源目录），其中混有 conan 生成的 6 个环境脚本与 conaninfo.txt，
  `copy("*")` 须以 `excludes` 排除；且 `excludes` 必须是 **pattern 列表**，
  单个逗号串会被整体当作一个 fnmatch pattern 而不生效；
- build() 的 14 文件计数同样要排除 `.sh`（构建目录混入的环境脚本），
  排除后计数语义与上游清单一致，防漂移能力不受损。

## 参考

- IF Archive library 索引: https://ifarchive.org/indexes/if-archive/infocom/compilers/inform6/library/
- Debian inform6-library: https://packages.debian.org/source/trixie/inform6-library
