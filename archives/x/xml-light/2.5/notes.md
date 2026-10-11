# xml-light 2.5 适配笔记

## 编译环境
- 构建系统: custom（dune 3.17.0，registry 提供）
- 编译日期: 2026-10-06
- 编译器: ocamlc/ocamlopt 4.14.1（registry ocaml/4.14.1.1.4）
- 状态: built

## 软件说明
Xml-Light 是 OCaml 的极简 XML 解析/打印库（作者 Nicolas Cannasse），
支持 DTD 解析、校验（check）与证明（prove），纯 OCaml 实现无 C 依赖。
2.5 版切换为 dune 构建（`dune build -p xml-light`），库以 `wrapped false`
发布，公开模块 Xml / Dtd / XmlParser，内部模块由 ocamllex
（xml_lexer.mll）与 ocamlyacc（xml_parser.mly）生成。

## 语言预检说明（R47）
lang-preflight 判 `detected_language=other`（`lang_detect.py` 的
`_EXT_LANG` 不含 `.ml/.mli/.mll/.mly`，§4.6 枚举无 `ocaml` 值）→ 自动写了
env_unsupported 终态。经核验为**工具盲区误报**：
- 源码为纯 OCaml（9 个 .ml/.mli + .mll/.mly）+ dune 构建（`dune-project`
  存在，`(lang dune 2.7)`）
- W0b CI 能力矩阵明确：OCaml → registry 工具链可 CI（PR6097 正例）
- 本仓库已有多个 OCaml 包走通同一流程（csexp/camlp-streams 5.0.1 已合入，
  xmlm/menhir 同模式 PR 在审），均为 requires ocaml + dune 形态
- 按 camlp-streams 5.0.1 已合入先例继续适配；终态 result.json 以真实结果
  为准重写（--force）

## 编译步骤
1. `dune build -p xml-light @install`
   - 环境：OCAMLLIB=<ocaml pkg>/lib/ocaml，
     CAML_LD_LIBRARY_PATH=<ocaml pkg>/lib/ocaml/stublibs，
     PATH 前置 ocaml bin + dune bin
   - 无需 `--root`（dune 3.17 拒绝 `dune --root=. <cmd>` 语法）；
     HMDFS 的 "Unable to read /storage/Users" 警告为良性（camlp-streams
     先例验证过，构建不受影响）
   - 产物：xml_light.cma/.cmxa/.cmxs/.a + 各模块 cmi/cmt/cmx
     （Xml/Dtd/XmlParser + 生成的 xml_lexer/xml_parser 等），
     dune @install 树含 META（dune-project 带 `(version 2.5)`，META 有
     version 字段）
2. `dune runtest -p xml-light`（见下方上游测试三步法）
3. `package()`：从 `_build/install/default/lib/xml-light` 以
   `copytree(symlinks=False)` 拷贝实文件到 `lib/ocaml/xml-light`
   （findlib 布局）；强制校验 8 个必需产物存在且全部为非空实文件
   （HMDFS 软链症状守卫）

## 上游测试三步法（R51）
1. **清点**（官方 2.5 release tarball 核对）：
   - tests/ 共 6 个文件：dune、test.ml、check_dtd.ml、simple.xml、
     topic-like.dtd、topic.xml
   - tests/dune 注册 2 个可执行文件（test.exe、check_dtd.exe，链接
     xml-light 库）+ 2 条 runtest alias 动作：
     a. `(pipe-stdout (cat simple.xml) (run ./test.exe))` — 上游 CI 的
        标准喂入方式
     b. `(run ./check_dtd.exe topic-like.dtd topic.xml topic)` — DTD
        parse/check/prove 全链路
   - 申报表：discovered=2，passed=2，见 test_package/MANIFEST.yml
2. **实际运行**（registry OCaml 4.14.1 + dune 3.17，非"没环境"）：
   `dune runtest -p xml-light` 在 build() 内执行，两个动作均编译并运行
   通过（详见 reports/test-report.md 与 conan create 日志）
3. **PR 回填**：MANIFEST.yml 如实写 discovered=2 / passed=2，无修改、
   无跳过；test_package 另含消费者测试与鸿蒙 e2e 用例（rule12）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 other/env_unsupported | lang_detect.py 扩展名表/§4.6 枚举缺 OCaml | 工具盲区误报；按 camlp-streams 5.0.1 已合入先例继续；终态 result 以真实结果重写 |
| 2 | `init-build` 下载 .tbz 后解压失败 "not a gzip file" | 仓库工具固定按 `.tar.gz` 保存并假定 gzip，不支持 bzip2 | 脚手架阶段临时改用 GitHub codeload tag tar.gz（gzip）；**提交的 conandata.yml 用官方 release .tbz 资产**（opam 锁定，sha256 交叉核对一致），conanfile `source()` 以 `filename=*.tar.bz2` 显式解包（xmlm 1.4.0 先例） |
| 3 | codeload tag 归档里 dune-project 是 `(version 2.4)`，release .tbz 里才是 `(version 2.5)` | 上游打 2.5 tag 时 dune-project 版本未入库（tag 树与 release 资产不同步） | 选用官方 release .tbz 作为 conandata 源（版本元数据正确，无需任何补丁）；本地 .orig/.work 已对齐 release 资产内容 |
| 4 | dune @install 树全为指向 _build/ 的相对软链 | dune 机制 + HMDFS 对软链支持不可靠 | package() 以 `copytree(symlinks=False)` 从 install 树拷实文件（menhir 20260209 先例），并校验无非空实文件 |
| 5 | ocaml 包 launcher 绝对 shebang 在 cache 重定位后悬空 | ocaml 包构建时烘焙的绝对路径 | build() 中泛化 shebang 修复（camlp-streams 先例） |
| 6 | 设备侧 OCaml 原生编译缺 GNU as / 烘焙 cc 路径失效 | 设备镜像无 binutils；registry ocaml 包烘焙的是 CI worker 路径 | 设备本地工装（profile [buildenv] OCAMLPARAM=_,cc=ccwrap + PATH 前置 local/bin，内含 as/ccwrap shim，menhir 任务就位）；**归档配方零依赖这些工装**，平台 CI worker 具备完整工具链 |

## 源码修改
无补丁（patches_applied 为空）。上游 2.5 release 资产在 OHOS 上未改一行
源码即构建、测试通过。

## 依赖版本
- ocaml/4.14.1.1.4（制品仓，revision 1537a565…）
- dune/3.17.0（制品仓，revision 58cd83c8…）

## 依赖发布检查（W0）
`conan download <dep> -r=ohpcd --only-recipe`（R35 口径）双确认：
ocaml/4.14.1.1.4 与 dune/3.17.0 recipe 均在 ohpcd 制品仓；两者 armv8/OHOS
Release binary 亦已发布（camlp-streams 5.0.1 notes 的
`conan install --build=never` 实测 + 本包 conan create 解析成功为证）。
无新增缺失依赖（无 dependency_missing 需上报项）。

## 发现与知识
- OCaml/dune 包适配完全复用 camlp-streams 5.0.1（已合入）确立的模式：
  requires ocaml + dune、env 注入、@install 实文件打包、findlib 布局。
  本包无新错误模式产生（conan-verify 无知识草稿新增）。

**编译结束**: 2026-10-06
---

**编译结束**: 2026-10-06 14:44
**最终状态**: built
