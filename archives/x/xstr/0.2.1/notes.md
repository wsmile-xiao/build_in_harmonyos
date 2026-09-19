# xstr 0.2.1 适配笔记

## 软件信息
- **名称**: xstr
- **版本**: 0.2.1
- **类型**: 纯 OCaml 字符串处理库（search / replace / split / match，线程安全，是 OCaml Str 模块的子集替代）
- **作者**: Gerd Stolpmann
- **上游**: http://www.ocaml-programming.de/packages/ / https://projects.camlcity.org/projects/xstr.html
- **官方源码**: https://download.camlcity.org/download/xstr-0.2.1.tar.gz
- **许可证**: MIT/X11
- **构建系统**: 纯 Makefile（无 autotools/cmake/meson/dune）

## 源码审计
- tarball `xstr-0.2.1.tar.gz`，sha256 `796f77589af651d1bb627444fa48c76d887c97d98a58cb95913d86103fb168be`
  （与 Debian `/debian/pool/main/x/xstr/xstr_0.2.1.orig.tar.gz` 逐字节一致，已 `cmp` 验证为同一上游归档）。
- 3 个模块：`xstr_split`（切分）、`xstr_search`（搜索/替换）、`xstr_match`（模式匹配）。
- 构建：`make all` → 字节码 `xstr.cma`；`make opt` → 本机 `xstr.cmxa` + `libxstr.a`。
- `make install` 依赖 ocamlfind（findlib），未打包；README 明确支持「无 findlib 时手动拷贝 .cmi/.cma/.cmxa/.a」。

## 上游测试审计（no_tests）
- tarball 无 `tests/`/`test/` 目录；无 gtest/pytest/ctest 注册。
- `Makefile` 目标仅 all/opt/install/uninstall/clean/distclean/release/dist，**无 check/test 目标**。
- `speed/` 目录是 xstr 与 Str 的**性能基准示例**（`with_str.ml`/`with_xstr.ml`），其中名为 `test_*` 的是计时函数，只计时不断言，非测试用例。
- 结论：上游确无测试套件 → `test_package/MANIFEST.yml` 写 `upstream_tests_exist: false` + 完整 `upstream_test_audit`，test_package 输出 `HMBS_UPSTREAM_TEST_RESULT`（status=no_tests）。

## 适配要点
1. **依赖**: `requires("ocaml/4.14.1.1.4")` —— OCaml 工具链（ocamlc/ocamlopt/ocamldep/ocamlrun）由该包提供（R33：编译器路径从 Conan 依赖取得，不裸用 shell 变量）。repo 内已有 `archives/o/ocaml/4.14.1.1.4`（最新迭代版），`ocaml-syntax-shims` 为先例。
2. **构建**: `layout()` 用 `build="."; source="."`（同 ocaml-syntax-shims 先例）。source() `get(..., strip_root=True)`。build() 把 ocaml 包 bin 注入 PATH，同时显式设 `OCAMLLIB` 指向 ocaml 包 `lib/ocaml/`（否则 ocamlc 报 `Unbound module Stdlib`——ocaml 包编译期嵌入的 --prefix 在缓存目录会失效），依次 `make all` 与 `make opt`。Makefile `include depend` 首次构建自动 `ocamldep` 生成依赖（需 ocaml bin 在 PATH）。
3. **打包**: package() 手动安装（绕开 ocamlfind/HMDFS）：把 `.mli/.cmi/.cmo/.cmx/.cma/.cmxa/libxstr.a/xstr.a/META/LICENSE/README` 拷入 `lib/xstr/`。
4. **package_info**: `includedirs=["lib/xstr"]`、`libdirs=["lib/xstr"]`、`libs=[]`（OCaml 库按 `xstr.cma`/`xstr.cmxa` 文件名链接，非常规 `-l`）。
5. **test_package**: `test.ml` 用 ocamlc 链接 `xstr.cma`，真实调用 9 条断言（Xstr_search 5 + Xstr_split 2 + Xstr_match 2），末尾打印 `xstr: N/M assertions passed`；test() 捕获输出解析 N/M 生成 `HMBS_TEST_PACKAGE_RESULT`（discovered=M, passedCount=N）。同时复发 `HMBS_UPSTREAM_TEST_RESULT`（no_tests）。编译时同样设 `OCAMLLIB`；运行时设 `OCAMLLIB` + `CAML_LD_LIBRARY_PATH`（指向 ocaml 包 `lib/ocaml/stublibs`，供 ocamlrun 加载 dllunix.so 等 C stub）。
6. **上游缺陷补丁（OCaml>=4.06 不可变 string 类型不匹配，一批 3 处）**，均在 `build()` 内通过 Python 就地编辑 `_apply_source_fixes` 修复，不依赖外部 `patch` 二进制（真机 busybox/toybox patch 报 "patch stream is incomplete!" 无法解析统一 diff）：
   - `xstr_search.ml` 的 `rev_concat`：`String.create`(bytes) 缓冲返回给 .mli 声明的 `string`，把返回 `t` → `Bytes.to_string t`（与 test_package 中 `rev_concat " " ["a";"b"] = "b a"` 的 string 语义一致）。
   - `xstr_match.ml` 的 `set_as_string`：`String.make`(string) 后 `s.[i]<-` 原地写（要求 bytes，报 "expected type bytes"），改 `Bytes.make` + 返回 `Bytes.to_string s`。
   - `xstr_match.ml` 的 `replace_matched_substrings`：`String.create`(bytes) 的 `target` 返回给 .mli 声明的 `(string*int)`，改 `Bytes.to_string target`。
   - conandata.yml 已移除 `patches:` 段，不再使用补丁文件机制。

## 验证
- 本阶段仅完成未提交工作树；真机（ohos@c1.sermc.net，端口 20222）编译 + test_package + 上游测试由 HMBS 预检执行。
- 预期：`make all`/`make opt` 成功，9/9 断言通过，`HMBS_TEST_PACKAGE_RESULT` discovered=9/passedCount=9，`HMBS_UPSTREAM_TEST_RESULT` status=no_tests。

## 备注
- 真机环境与命令属内部基建，不写入 PR 正文（正文统一写「在 HarmonyOS aarch64 环境实测」）。
- 本配方是 OCaml 库，非 C/C++；参考 repo 内 `ocaml-syntax-shims/1.0.0`（application 先例）与本库的 OCaml 库形态完成。

## 2026-09-18 修复：test_package 误报 passed:false（0/9 假阴性）
- 现象：真机 conan create 成功、test_package 执行到 test()，但
  `HMBS_TEST_PACKAGE_RESULT` 为 `passed:false, discovered:9, passedCount:0`。
- 诊断：旧 test() 用 `self.run(..., stdout=True)` 的返回值解析断言数。若断言
  真失败 test.ml 会 exit 1，conan 的 run 将抛异常、JSON 不会打印；但 JSON 确实
  打印了，说明进程 exit 0（9 条全过），却解析到 0 —— 唯一自洽解释是
  `self.run(stdout=True)` 在本真机/ocamlrun 路径返回的空/未含程序输出，regex 匹配
  不到而落入 fallback（discovered=9, passed=0）。
- 修复：test() 改为把 `ocamlrun test_probe` 输出重定向到文件再读回解析
  （`> test_result.txt 2>&1`），并用 `ignore_errors=True` 使真实断言失败也不中断、
  仍如实上报 passed:false；同时把 test_probe 的每行输出回显到 conan 日志便于诊断。
- 结论：无论根因是 stdout 捕获为空还是断言真失败，此写法都通道式给出真实结果且
  带完整断言输出，供下一轮门禁与诊断。

## 2026-09-19 修复：MANIFEST.yml 缺少 upstream_test_total 字段（rule4 门禁失败）
- 现象：真机预检 `HMBS_UPSTREAM_TEST_RESULT` status=no_tests 输出正确，但门禁返回
  `rule4：必须声明合法的 upstream_test_total，缺失不能按 0 处理`。
- 诊断：MANIFEST.yml 中虽有 `upstream_tests_exist: false` 及完整 `upstream_test_audit`，
  但缺少强制字段 `upstream_test_total` 和 `upstream_test_count_method`，导致 rule4 拒绝。
- 修复：在 `upstream_tests_exist: false` 后追加两行：
  - `upstream_test_total: 0`（上游确无测试，口径为手动审计确认）
  - `upstream_test_count_method: manual_audit`
- 经验参考：经验 1（udns/0.6 同类复发 no_tests 标记问题）提示 test() 中复发 HMBS_UPSTREAM_TEST_RESULT 的做法已到位；本轮根因在 MANIFEST.yml 字段缺失而非 conanfile.py。

## 2026-09-19 修复：CI L0c no_test_sources（test_package 无 CI 认可的测试源文件）
- 现象：CI #51243 在 conan-build-test 步骤报 `L0c: No test source files in test_package/`
  （L0 质量闸失败，L0_ERRORS=no_test_sources）。
- 诊断：CI L0c（build_and_test.sh）只认 test_package/ 下扩展名为
  `.c/.cpp/.cc/.cxx/.sh/.py` 的测试源文件；本库的测试程序是 OCaml 的 `test.ml`，
  扩展名 `.ml` 不在识别列表内，故 gate 判定无测试源。仓库内 ocaml-syntax-shims
  （application 先例）正是因此带一个 `.sh` 驱动脚本。
- 修复：新增 `test_package/run_test.sh`（`.sh` 测试驱动，满足 L0c/PF3 识别），
  把原先散在 conanfile.py build()/test() 里的「设 PATH/OCAMLLIB/CAML_LD_LIBRARY_PATH →
  ocamlc 链接 xstr.cma 编译 test.ml → ocamlrun 运行并重定向到结果文件」逻辑
  收敛进该脚本；conanfile.py 通过 `_env()` 统一解析依赖包路径后 `sh run_test.sh ...`
  调用（build() 与 test() 均调用，test() 带 ignore_errors=True 保留真实失败上报）。
  断言计数解析逻辑（HMBS_TEST_PACKAGE_RESULT discovered=9/passedCount=N）与
  HMBS_UPSTREAM_TEST_RESULT（no_tests）保持不变。
- 结论：`run_test.sh` 是 CI 认可的 .sh 测试源且真实参与执行，L0c 应放行。
