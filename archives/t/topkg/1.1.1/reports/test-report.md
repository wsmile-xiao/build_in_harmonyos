# 测试报告 — topkg 1.1.1

- 日期: 2026-10-06
- 设备: HarmonyOS PC (HAD-W32, aarch64, API 23)
- 方式: `conan-verify`（G0–G4，profile `ohos-aarch64-device`）+ W3 本地 CI（`ci/conan/build_and_test.sh`，`CONAN_PROFILE=ohos-aarch64-device`）
- 结果: **conan-verify G0–G4 全 PASS；本地 CI L0/L1/L1e/L2/L4/L5 全 PASS（1/1 包，pass rate 100%，`.ci-result.json` exit_code=0）**
- 原始日志: `reports/conan-create.log`、`reports/w3-local-ci.log`（工作区留存，按仓库规范不提交）

## conan create（干净源码构建）

`conan create archives/t/topkg/1.1.1 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device --build=missing`

- source(): 官方 erratique.ch tarball（sha256 校验通过）
- build(): 上游源码零修改，按 `ocamldep -sort` 依赖顺序直连编译 20 个模块
  （ocamlc/ocamlopt + conanfile 内 OHOS shim），按依赖顺序归档
  `topkg.cma/.cmxa/.a/.cmxs`（上游 topkg 自举构建需 ocamlbuild，制品仓尚未发布，
  由直连编译等价复现）
- 门禁: G0 pass / G1 pass / G2 pass / G3 pass / G4 pass

## 上游测试（R51）

- `test/test.ml`（pkg/pkg.ml 的 Pkg.test 条目）：编译运行 → `The test is ok, the arguments are: alpha beta`，exit 0
- discovered=1 / passed=1；上游 topkg-care 的测试不在本包范围

## test_package 消费者测试（R34，L1 实测）

1. 产物断言 7 项（topkg.cma/.cmxa/.cmxs/.a/.cmi/META/.mli）
2. native 路径：`ocamlopt -I <pkg> topkg.cmxa test_topkg.ml` → 真机执行 →
   `assertions=14 failures=0` / `ALL TESTS PASSED`
3. bytecode 路径：`ocamlc -I <pkg> topkg.cma test_topkg.ml` + `ocamlrun` →
   `assertions=14 failures=0` / `ALL TESTS PASSED`
4. 断言覆盖：Topkg.String（is_prefix/is_suffix/cut）、Topkg.R（error_msg/reword_error）、
   Topkg.OS 真机交互（Dir.current + 目录列表、/dev/null write/read EOF 语义、
   Cmd.exists/must_exist 解析 sh）

## L1e 破坏性反向验证（R34）

本地 CI 将包内 `lib/` 移走后 test_package 编译失败 → 证实测试实质依赖被测包。

## 统计

| 项 | 数量 |
|---|---|
| 上游测试 discovered / passed | 1 / 1 |
| test_package 程序内断言（native 14 + bytecode 14；另 test.sh 含 7 项产物存在性断言与 6 项构建/运行状态断言） | 14（双路径各执行一次） |
| 鸿蒙特有测试 | 1（真机 OS 交互 e2e 消费者用例） |
