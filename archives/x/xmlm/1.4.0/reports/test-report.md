# 测试报告 — xmlm 1.4.0

- 日期: 2026-10-04
- 设备: HarmonyOS PC (HAD-W32, aarch64, API 23)
- 方式: `conan-verify`（G0–G4，profile `ohos-aarch64-device`）+ W3 本地 CI（`ci/conan/build_and_test.sh`，`CONAN_PROFILE=ohos-aarch64-device`）
- 结果: **conan-verify G0–G4 全 PASS；本地 CI L0/L1/L1e/L2/L4/L5 全 PASS（1/1 包，pass rate 100%，`.ci-result.json` exit_code=0）**
- 原始日志: `reports/conan-create.log`、`reports/w3-local-ci.log`（工作区留存，按仓库规范不提交）

## conan create（干净源码构建）

`conan create archives/x/xmlm/1.4.0 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device --build=missing`

- source(): 官方 URL（erratique.ch，sha256 校验通过）+ 显式 `filename="xmlm-1.4.0.tar.bz2"`（Conan unzip 不识别 `.tbz`）
- build(): ocamlc/ocamlopt 直接编译未修改的上游源码 → `xmlm.cma/.cmxa/.cmxs/.a/.cmi`；`-cc` OHOS clang + `as` shim；cmxs 补 `-ccopt -shared`
- 门禁: G0 pass / G1 pass / G2 pass / G3 pass / G4 pass
- 本地 CI: L0 pass / L1 pass（test_package 实际执行）/ L1e pass（破坏性反向验证）/ L2 pass（`xmltrip --help`）/ L4 pass（无补丁）/ L5 pass（bin/ 有内容）

## 上游测试（R51）

- 清点: 上游 `pkg/pkg.ml` 注册 4 个 `Pkg.test` 程序 — `test/test.ml`、`test/test_tree.ml`、`test/xhtml.ml`、`test/examples.ml`（另有 `Pkg.bin test/xmltrip`）
- 实测: 4 个测试程序全部编译并执行（真实 OCaml 4.14.1 工具链 + 真实 aarch64 执行）
  - `test.ml` → 打印 `Decoder attribute stripping.` / `All tests succeeded.`（exit 0）
  - `test_tree.ml` → 输出 `<ol><li>bli</li>...</ol>`（exit 0）
  - `xhtml.ml` / `examples.ml` → 编译+初始化 exit 0
- 统计: discovered=4，passed=4，无源码修改（topkg/ocamlbuild 不在 registry，build() 用 ocamlc/ocamlopt 复现同一流水线）

## test_package 消费者测试（R34，L1 实测）

1. 产物断言: `xmlm.cma/.cmxa/.cmxs/.a/.cmi/.ml/.mli/META` 8/8 + `bin/xmltrip` 可执行
2. 字节码路径: `ocamlc -I <pkg> xmlm.cma test_xmlm.ml` + `ocamlrun` 实测 → `assertions=12 failures=0`，`ALL TESTS PASSED`
3. 原生路径: `ocamlopt -I <pkg> xmlm.cmxa test_xmlm.ml` 实测 → `assertions=12 failures=0`，`ALL TESTS PASSED`
   （解码断言、编码转义断言、encode→decode 往返；编译告警 58 为测试侧无 cmx 优化信息，良性）
4. `xmltrip` 二进制冒烟: `<a b="c">t</a>` parse-only → exit 0

## 鸿蒙特有测试（rule12，≥1）

`test_package/test_ohos_e2e.ml`（设备文件系统真实 I/O 的端到端消费者用例）：

- 写 param 风格 XML 配置到设备文件（product name/version/api、sdk path、`&amp;` 实体）
- `Xmlm.make_input (`Channel ic)` 流式解析并断言 9 项
- 用 `Xmlm.output` 重编码到第二个文件，重新解析校验元素数（4）
- 清理临时文件；输出 `assertions=9 failures=0` → `ALL OHOS E2E PASSED`

## L1e 破坏性反向验证（R34）

本地 CI 将包内 `lib/`、`bin/` 移走后 test_package 编译失败 → 证实测试实质依赖被测包（非空壳）。

## 统计

| 项 | 数量 |
|---|---|
| 上游测试 discovered / passed | 4 / 4 |
| test_package 断言（test_xmlm.ml 12 + test_ohos_e2e.ml 9 + xmltrip 冒烟 1） | 22 |
| 鸿蒙特有测试 | 1（e2e 消费者用例） |
