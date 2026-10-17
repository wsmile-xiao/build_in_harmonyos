# PostgreSQL 18.3 — 测试报告（OHOS PC aarch64）

日期：2026-09-04（第 3 轮：评审 R8 补丁重写后全量复验）｜ 分支：fix/pg-7992-review ｜ Profile：ci/conan/profiles/ohos-aarch64（原生构建）

## 1. 上游回归测试（make check，手动构建基线）

- 日期：2026-06-12（commit 149f3b650，手动构建，配置与本配方一致）
- 结果：**229/230 通过**
- 唯一失败：`opr_sanity`——根因是 OHOS ELF 签名机制阻止服务端加载未签名的
  扩展 .so（如 utf8_and_uhc.so），属**已知平台限制**（非源码 bug），详见版本级 notes.md。
- conan build() 内不执行 make check 的理由：需要完整服务端运行时
  （initdb 数据目录、TCP 监听、大量子进程），不适合 conan/CI 干净沙箱；
  test_package 以 libpq 真实 API 验证替代（见 §3）。

## 2. conan-verify（八门禁，本配方）

- G1 配方完整性：PASS
- G0 预构建风险（知识图谱预查询）：PASS
- G2 conan create（干净构建，ohpcd/stable）：PASS
- G3 系统同名库隔离（R26）：PASS
- G4 产物完整性：PASS
- 报告：reports/conan-verify-report.md

## 3. test_package（conan create 自动执行）

- `test_libpq`：编译链接 libpq（-lpq）→ 运行 `PQlibVersion()` = 180003，
  断言 major=18 **PASS**（`PASS: linked and executed against libpq 18.3`）
- `pg_config --version` → `PostgreSQL 18.3` **PASS**
- L1e 破坏性负测试：bin/lib/include 移走后测试真实失败（证明测试有效性）PASS

## 4. W3 本地 CI（ci/conan/build_and_test.sh，第 3 轮，R8 补丁重写后终态）

- L0 质量门禁（含 KC/JC 垃圾文件检查）：PASS
- L1 测试执行证据：PASS
- **L2 平台功能矩阵（35 个命令 smoke）：35/35 全 OK**
  （第 3 轮首跑曾 34/35——pg_upgrade --version 报 user does not exist，
  根因 tc.defines 只读 property 致宏未注入、守卫代码被编译剔除；
  修复 tc.extra_defines 后恢复全绿，记录见 notes.md 第 10 条）
- L4 补丁危险函数扫描：WARN（误报，查证见 notes.md 第 7 条：
  'gets mapped' 为英文注释、psprintf 为 PG 官方安全封装 vsnprintf 定长实现；
  补丁无真实危险函数调用）
- L5 产物基线：PASS（bin/ 有内容）
- Build Summary：**100.0% (1/1)**，日志含 ci-metadata.json 生成记录

## 5. 可重定位性验证（rpath）

- `readelf -d bin/psql` → `RUNPATH=[<prefix>/lib:$ORIGIN/../lib]`
- bin/psql + lib/libpq.so.5 复制到任意目录结构，无 LD_LIBRARY_PATH 直接运行
  成功（`psql (PostgreSQL) 18.3`）

## 结论

- 上游回归：229/230（opr_sanity 失败为已知平台限制，非源码 bug）
- conan-verify：G0-G4 全 PASS
- W3 本地 CI：100%，L2 35/35
- 判定：**通过**，可提交 PR
