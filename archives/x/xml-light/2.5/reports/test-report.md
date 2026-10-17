# 测试报告 — xml-light 2.5

- 日期: 2026-10-06
- 设备: HarmonyOS PC (HAD-W32, aarch64, API 23)
- 方式: `conan-verify`（G0–G4，profile `ohos-aarch64-device`）+ W3 本地 CI（`ci/conan/build_and_test.sh`，`CONAN_PROFILE=ohos-aarch64-device`）
- 结果: **conan-verify G0–G4 全 PASS；本地 CI L0/L1/L1e/L4/L5 全 PASS、L2 skip（库包无 bin/，按设计跳过）——1/1 包，pass rate 100%（`All packages built and tested successfully`）**
- 原始日志: `.ci_logs/conan_build_xml-light_2.5.log`（本地 CI 强制源码重建全量日志）、`reports/conan-create.log`、conan 缓存构建目录 `_build/log`（dune action 日志；均按仓库规范留存工作区、不提交）

## conan create（干净源码构建）

`conan create archives/x/xml-light/2.5 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device --build=missing`

- source(): 官方 release 资产 URL（github.com，sha256 与 opam 仓库锁定值一致）+ 显式
  `filename="xml-light-2.5.tar.bz2"`（Conan unzip 不识别 `.tbz`，xmlm 1.4.0 先例）
- build(): `dune build -p xml-light @install` + `dune runtest -p xml-light`
  （registry ocaml/4.14.1.1.4 + dune/3.17.0，OCAMLLIB/PATH 注入，
  设备侧 as/ccwrap 工装经 profile [buildenv] 提供，不入归档配方）
- package(): dune @install 树以 `copytree(symlinks=False)` 拷实文件到
  `lib/ocaml/xml-light`；打包清单：META/opam/dune-package + xml_light.cma/.cmxa/.cmxs/.a
  + 8 .ml + 7 .mli + 9 .cmi + 8 .cmt + 7 .cmti + 8 .cmx
- 门禁: G0 pass / G1 pass / G2 pass / G3 pass / G4 pass（L2 smoke / L4 checksec / L5 基线）
  — `reports/conan-verify-report.md`

## 上游测试（R51）

- 清点: 上游 `tests/dune` 注册 2 个 runtest 动作 —
  ① `(pipe-stdout (cat simple.xml) (run ./test.exe))`（test.ml 逐行读取 stdin 后解析打印）
  ② `(run ./check_dtd.exe topic-like.dtd topic.xml topic)`（DTD parse/check/prove 全链路）
- 实测: `dune runtest -p xml-light` 在 build() 内执行（真实 OCaml 4.14.1 工具链 +
  真实 aarch64 执行）。dune `_build/log` 记录两动作均真实运行：
  - `./check_dtd.exe topic-like.dtd topic.xml topic` →
    输出 `<topic ID="topic-1"><title>Topic title</title><body><p>This is un exemple of
    DITA <term>topic</term>.</p>...</body></topic>`（DTD 证明后的文档，exit 0）
  - `./test.exe < simple.xml` → `Parsing...` + 完整 breakfast_menu 格式化输出 + `Exit.`（exit 0）
- 统计: discovered=2，passed=2，无源码修改（上游测试零改动原样执行）

## test_package 消费者测试（R34，L1 实测）

`conan-create.log` test_package 段完整输出（4 段断言）：

1. 产物断言: `xml_light.cma/.cmxa/.cmxs/.a` + `xml.cmi/dtd.cmi/xmlParser.cmi` + `META` → `artifacts: OK (8/8)`
2. 字节码路径: `ocamlc -I <pkg> xml_light.cma test_xml_light.ml`（compile-only）→ `bytecode compile: OK`
3. 原生路径: `ocamlopt -I <pkg> xml_light.cmxa test_xml_light.ml` 编译执行 →
   `parse_string ok` / `pcdata ok` / `to_string round-trip ok (91 chars)` /
   `negative control ok: Xml_light_errors.Xml_error raised` /
   `dtd parse/check/prove ok: root=config` /
   `dtd negative control ok: root-not-declared rejected` → `ALL TESTS PASSED`
4. e2e（见下）→ `ALL OHOS E2E PASSED`

## 鸿蒙特有测试（rule12，≥1）

`test_package/test_ohos_e2e.ml`（设备文件系统真实 I/O 的端到端消费者用例）：

- 写 HarmonyOS 风格 module 配置 XML（bundle/deviceTypes 字段）+ DTD 到设备 `$TMPDIR`
- `Dtd.parse_file + check`（文件 I/O 路径）→ `Xml.parse_file` 解析整档 →
  `Dtd.prove` 完成 DTD 证明（与上游 check_dtd.ml 相同用法），断言
  bundle/target/子元素结构/PCDATA
- `XmlParser` 对象 API 双数据源（SString + SFile）再解析断言
- 负向控制: 缺必填 bundle 的配置被 `Dtd.prove` 拒绝（`RequiredAttribute` → Prove_error）
- 清理临时文件；输出 `ALL OHOS E2E PASSED`

实测输出: `ohos module config parsed + dtd-proved ok: bundle=com.example.xml-light` /
`xmlparser object api ok: SString + SFile` / `negative control ok: DTD proved rejection raised` /
`ALL OHOS E2E PASSED`

## L1e 破坏性反向验证（R34）

本地 CI 将包内 `lib/` 移走后 test_package 编译失败 → 证实测试实质依赖被测包（非空壳）：
`[sabotage] lib/ moved away` → `[ok] L1e: Negative test confirmed — test genuinely depends on xml-light`。

## 本地 CI 门禁（W3，与平台 CI 同脚本）

`zsh ci/conan/build_and_test.sh archives/x/xml-light/2.5`（`CONAN_PROFILE=ohos-aarch64-device`）：

- L0: pass（L0i 依赖 dune/3.17.0、ocaml/4.14.1.1.4 均在 registry；L0j 版本首发无冲突；
  L0k 库包无需 commands.json；L0m 目录结构合规）
- KC: pass（知识库 542 条一致性）；JC: pass（增量模式 10 文件，无杂项；单包原子 JC6 合规）
- conan create: **pass（--build='xml-light/*' 强制源码重建**；上游 runtest 两动作 +
  test_package 4 段全部真实执行，输出见上；源码经 gh-proxy 镜像预下载，
  sha256 一致，跑毕 conandata 自动还原官方 URL）
- L1: pass（test_package 由 conan create 执行 + 日志有执行证据）
- L1e: pass（破坏性反向验证，见上节）
- L2: skip（库包无 bin/ 目录，按设计跳过）
- L4: pass（无补丁，扫描干净）；L5: pass（lib/ 有内容）
- 汇总: `Total 1 / Success 1 / Failed 0 / Pass rate 100.0%`

## 统计

| 项 | 数量 |
|---|---|
| 上游测试 discovered / passed | 2 / 2 |
| test_package 断言段 | 4（产物 8 项 / 字节码 / 原生 6 断言组 / e2e） |
| 鸿蒙特有测试 | 2 个用例文件（test_xml_light.ml + test_ohos_e2e.ml，其中 e2e 为 rule12 完整消费者用例） |
