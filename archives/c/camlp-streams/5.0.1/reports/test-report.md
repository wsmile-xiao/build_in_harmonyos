# 测试报告 — camlp-streams 5.0.1

- 日期: 2026-09-24
- 方式: W3 本地 CI（finish step [5/10]，ci/conan/build_and_test.sh）
- 结果: **1/1 包构建+测试通过，.ci-result.json exit_code=0**

## conan create（干净源码构建）
- `conan create` 全流程通过：source 下载 → dune build -p camlp-streams
  → dune runtest -p camlp-streams（exit 0）→ package() → test_package
- 门禁: L0 pass / L1 pass（test_package 执行）/ L2 skip（无 bin/，纯库包）/
  L4 pass（无补丁）/ L5 pass（lib/ 产物存在）

## L1e 破坏性反向验证（R34）
- 移走 lib/ 后 test_package 编译失败 → 证实测试实质依赖被测包（非空壳）

## test_package 覆盖（消费者级）
1. 断言包内产物存在: camlp_streams.cma/.cmxa/.cmxs/.a、stream.cmi、
   genlex.cmi、META
2. 字节码编译: `ocamlc -I <pkg>/lib/ocaml/camlp-streams camlp_streams.cma
   test_camlp_streams.ml`（registry OCaml 4.14.1 无 findlib，
   显式 cma 链接）
3. 原生编译+运行: `ocamlopt ... camlp_streams.cmxa ... && ./exe`
   - Stream: of_list + next 迭代（断言 [1;2;3] 顺序与值）
   - Genlex: make_lexer 分词（Kwd/Ident/Int/Float/String 分类 +
     嵌套注释跳过，7 个 token 断言）
   - 输出 "ALL TESTS PASSED"

## 上游测试（R51）
- 清点: test/ 注册 2 可执行文件（equality.exe、linking.exe）+
  2 diff 断言（equality.expected、issue4.expected）
- 实测: `dune build test/equality.exe test/linking.exe` 通过，两可执行文件
  直接运行正常退出（类型级/链接级测试，无输出）；`dune runtest` exit 0
- 阻塞: 2 条 diff 断言引用的 .expected 文件不在 v5.0.1 tarball（上游
  git tree 核对确认缺失）→ 2/4 无法执行，非 OHOS 适配问题
- 详见 test_package/MANIFEST.yml 申报表
