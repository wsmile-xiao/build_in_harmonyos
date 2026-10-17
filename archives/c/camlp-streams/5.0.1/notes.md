# camlp-streams 5.0.1 适配笔记

## 编译环境
- 构建系统: custom（dune 3.17.0，registry 提供）
- 编译日期: 2026-09-24
- 编译器: ocamlc/ocamlopt 4.14.1（registry ocaml/4.14.1.1.4）
- 状态: built

## 软件说明
camlp-streams 提供 OCaml 的 Stream 与 Genlex 库（从 OCaml 标准库拆分出来，
未来版本将从 stdlib 移除并在此独立维护）。纯 OCaml + dune 构建，
无 C 代码，无外部依赖。

## 语言预检说明（R47）
lang-preflight 判 `detected_language=other`（`lang_detect.py` 的 `_EXT_LANG`
不含 `.ml/.mli`，§4.6 枚举无 `ocaml` 值）→ 自动写了 env_unsupported 终态。
经核验为**工具盲区误报**：
- 源码为纯 OCaml（8 个 .ml/.mli）+ dune 构建（`dune-project` 存在）
- W0b CI 能力矩阵明确：OCaml → registry 工具链可 CI（PR6097 正例）
- 本仓库已有 10+ OCaml 包走通同一流程（csexp/cppo/zarith/alcotest/
  calendar/dune 等，均为 requires ocaml + dune 形态）
- 用户（协作模式指派方）已裁决：继续适配（2026-09-24），
  终态 result.json 以真实结果为准重写

## 编译步骤
1. `dune build -p camlp-streams`
   - 环境：OCAMLLIB=<ocaml pkg>/lib/ocaml，
     CAML_LD_LIBRARY_PATH=<ocaml pkg>/lib/ocaml/stublibs，
     PATH 前置 ocaml bin + dune bin
   - 无需 `--root`（dune 3.17 拒绝 `dune --root=. <cmd>` 语法）；
     HMDFS 的 "Unable to read /storage/Users" 警告为良性，构建不受影响
   - 产物：camlp_streams.cma/.cmxa/.cmxs/.a + stream/genlex 的 cmi/cmt
2. `dune runtest -p camlp-streams`（见下方上游测试三步法）

OCaml 4.14.1（< 5.0）下根 dune 文件生成
`stream.ml = "include Stream"` / `genlex.ml = "include Genlex"` 转发模块，
库模块 Stream/Genlex 以 unwrapped 方式发布（与 stdlib 兼容）。

## 上游测试三步法（R51）
1. **清点**（v5.0.1 tarball + 上游 git tree 双重核对）：
   - test/ 仅 5 个文件：dune、equality.ml、linking.ml、
     stream_stdlib.ml、stream_camlp_streams.ml
   - test/dune 注册 2 个可执行文件（equality.exe、linking.exe）+
     2 条 diff 断言（`diff equality.expected equality.output`、
     `diff issue4.expected issue4.output`）
   - **equality.expected / issue4.expected 不在 v5.0.1 tarball 中**
     （GitHub API git/trees 核对：上游 test/ 目录同样没有这两个文件）
   - 申报表：discovered=4，passed=2，见 test_package/MANIFEST.yml
2. **实际运行**（registry OCaml 4.14.1 + dune 3.17，非"没环境"）：
   - `dune build test/equality.exe test/linking.exe` → 通过
   - 直接执行两可执行文件 → 均正常退出（无输出，类型级/链接级测试）
   - `dune runtest -p camlp-streams` → exit 0；_build/log 证实仅执行了
     两条 `./xxx.exe > output` action，diff 断言因 .expected 缺失
     未被执行（dune 未生成对应 action）
3. **PR 回填**：MANIFEST.yml 如实写 discovered=4 / passed=2，
   并注明 2 条 diff 断言被上游打包缺失（非 OHOS 适配问题）阻塞；
   未为凑数添加任何 R36/PF4 依赖。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 other/env_unsupported | lang_detect.py 扩展名表/§4.6 枚举缺 OCaml | 工具盲区误报，用户裁决继续；终态 result 以真实结果重写 |
| 2 | 上游 `camlp5/camlp-streams` 404 | 真实仓库是 `ocaml/camlp-streams`（GitHub search 定位） | conandata URL 用官方 ocaml/camlp-streams v5.0.1 |
| 3 | dune @install 树全为指向 _build/ 的相对软链 | dune 机制 + HMDFS 对软链支持不可靠 | package() 从 _build/default 拷贝实文件（cma/cmxa/cmxs/a/cmi/ml/mli + dune-package），手写完整 META（dune 生成的 META 无 version 字段） |
| 4 | ocaml 包 `ocaml` launcher 绝对 shebang 在 cache 重定位后悬空 | ocaml 包构建时烘焙的绝对路径 | build() 中泛化 shebang 修复：仅当 shebang 目标不存在且 ocaml bin 内存在同名解释器时才重写 |
| 5 | 上游 test/dune 的 diff 断言引用的 .expected 文件缺失 | 上游 v5.0.1 打包遗漏（非适配问题） | 如实上报 2/4；两可执行文件实测通过；不补造测试 |

## 源码修改
无补丁（patches_applied 为空）。

## 依赖版本
- ocaml/4.14.1.1.4（制品仓，revision 1537a565…）
- dune/3.17.0（制品仓，revision 58cd83c8…）

## 依赖发布检查（W0）
`conan list ocaml/*:*/ dune/*:*/ -r=ohpcd` + `conan install --build=never`
双确认：ocaml/4.14.1.1.4 与 dune/3.17.0 均有 armv8/OHOS Release binary，
本地 install 成功（--build=never），无缺失依赖。

## 发现与知识
- ✅ OCaml 库适配走 registry 工具链：requires ocaml/4.14.1.1.4 + dune/3.17.0
  （W0b CI 能力矩阵，csexp 先例）
- ✅ dune @install 树全为指向 _build/ 的相对软链（HMDFS 下 copy 后悬空），
  package() 须从 _build/default 拷贝实文件并手写 META（csexp 先例）
- ✅ OCAMLLIB/CAML_LD_LIBRARY_PATH/PATH 必须从依赖包 folder 注入
  （conan cache 重定位后 ocamlc -where 返回陈旧路径）
- ✅ ocaml 包 launcher 脚本（ocaml）带绝对 shebang，cache 重定位后悬空——
  shebang 修复须泛化：目标存在才重写，否则保持原样
- ✅ registry OCaml 4.14.1 无 findlib：test_package 用显式 cma/cmxa 链接
  而非 -package；字节码产物 shebang 指向 cache 不可执行，测原生运行
- ✅ W3 预下载会把 conandata 单条 url 改写为含 gh-proxy 的镜像列表并留在
  工作区（CI L0j 按文件名+sha256 归一化对比）——提交前必须还原为官方
  单条 URL（PF7 黑名单域）
---

**编译结束**: 2026-09-24 17:17
**最终状态**: built
