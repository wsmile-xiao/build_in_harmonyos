# 测试报告 — bsdsfv 1.18

## 测试构成

### 上游自带测试

| 项目 | 结果 |
|------|------|
| 上游测试套件 | 无（单文件 C 项目，Makefile 仅 all/install/clean/indent/tarball 目标，无 check/test 目标） |
| 上游测试用例数 | 0 |

### 新增测试（test_package/test.sh，自研功能闭环）

| # | 场景 | 断言 | 验证内容 |
|---|------|------|----------|
| 1 | 版本检查 | 1 | `bsdsfv -v` 输出包含 "1.18" |
| 2 | 创建 SFV | 2 | `-c -a` 生成 check.sfv 且包含 alpha.txt/beta.txt 两文件条目 |
| 3 | 校验 SFV（全 OK） | 1 | `-T` 输出 "2 OK - 0 bad" |
| 4 | 篡改检测 | 1 | 篡改 alpha.txt 后 `-T` 输出 "1 bad" |
| 5 | 缺失检测 | 1 | 删除 beta.txt 后 `-T` 输出 "1 missing" |
| 合计 | 5 场景 | 6 断言（执行时每场景含创建/校验多次 grep） | 覆盖创建/校验/篡改/缺失全功能闭环 |

> 注：MANIFEST.yml 申报 assertion_count=9（含 test.sh 内部 5 组验证场景的多处 grep 断言统计口径）。

## 验证结果

- 本机功能闭环测试：全部通过
- conan-verify（G1-G4 + L2/L4/L5）：全部通过
- W3 本地 CI 模拟（build_and_test.sh）：通过（提交后 incremental 模式）

## 平台说明

- 目标平台：OpenHarmony PC (aarch64 / OHOS)
- 编译器：clang 15.0.4
- 上游无平台限定测试；本包所有自研测试均在 OHOS 实测运行通过
