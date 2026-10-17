# jsonxx 1.0.1 适配笔记

## 编译环境
- 构建系统: makefile（上游仅 test 程序 Makefile，无 configure/library/install 目标）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4（aarch64-linux-ohos，Conan profile ohos-aarch64）
- 状态: built（conan-verify G1-G4/L2/L4/L5 全通过，未 upload）

## 编译步骤

1. `init-build jsonxx 1.0.1 --url=<官方 v1.0.1 tarball>` 下载源码至
   `/storage/Users/currentUser/builds/jsonxx-1.0.1.work`（sha256
   `7ac3b38b9377481c71104d374d5f383e04a2f4c5baf840128e834afdccda09c0` 与官方一致）。
2. 上游验证：`CXX=clang++ make test` → `All tests ok.`（退出码 0）。
3. `conan-init` 生成配方骨架后，因上游无 Autotools 流程，改写 conanfile.py：
   直接从 Conan conf 取编译器（R33），`clang++ -std=c++11 -O2 -fPIC -c jsonxx.cc`
   编译后 `llvm-ar rcs libjsonxx.a`，package() 安装 jsonxx.h / libjsonxx.a / LICENSE。
4. 改写 test_package：`test_jsonxx.cpp` 真实调用 jsonxx API（解析/读写/构造/序列化），
   使用 CHECK 宏而非 assert()（Release/NDEBUG 下不失效），浮点比较用容差。
5. `conan-verify`：G1/G2(conan create + test_package ctest)/G3/G4/L2/L4/L5 全 PASS。
6. `finish jsonxx 1.0.1 built`：W2 结构检查、W3 本地 CI 模拟（build_and_test.sh）
   全通过，`.ci-result.json` 写入（exit_code=0，log_sha256 见该文件）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 后 test_package 运行时 jsonxx 内部断言
  `has<T>(key)` 崩溃 | test 用 assert() 判定，Release(-DNDEBUG) 下被整体
  编译掉，`obj.parse()` 未执行，后续无条件 `get<>` 在空对象上触发
  jsonxx 自身 JSONXX_ASSERT | 改用显式 CHECK 宏（非零 return + 打印行号），
  所有检查在 Release 下同样执行；对应知识已由 DRAFT-cpplocate-
  2.3.0-test-package-reliability / DRAFT-devio 覆盖（路径 A 等价命中） |
| 2 | `obj.get<Number>("ratio") == 3.14` 判 false | jsonxx 数字解析与
  字面量存在浮点精度差异（实测 `3.14 != 3.14` 为 0） | 浮点断言改
  `fabs(a-b) < 1e-9` 容差比较（通用常识，path_a_no_knowledge） |
| 3 | W3 build_and_test.sh JC 拦截 3 个空文件（cloog/kics 的历史
  基线 .build-closed/.staging-verified） | 其他库历史跟踪文件在
  origin/main 中，非当前库缺陷 | 按执行端规则临时 index 隔离（git rm
  --cached，记录 blob/content 哈希）→ W3 复验通过 → git reset 无条件恢复 |
| 4 | conandata.yml 被 CI 镜像注入残留 gh-proxy 前缀 | E017 预防临时
  注入镜像后备份未还原 | 恢复官方 URL 单值形式；W4 审计确认后重新提交 |

## 源码修改

无源码补丁（patches/ 为空）。上游源码零修改，仅配方层适配。

## 依赖版本

无第三方依赖（仅 C++ 标准库）；工具链 clang 15.0.4 + conan 2.29.1 + cmake 4.1.2。

## 上游测试（R51 三步法申报）

| 项 | 申报 |
|---|---|
| 测试清点 | 上游 1 个测试程序 `jsonxx_test.cc`（`make test` 运行 `./jsonxx_test`），
  138 处断言/测试调用，覆盖解析（严格/宽松）、序列化、Object/Array/Number/
  String/Boolean 读写、XML 转换 |
| 实际运行 | 本地 aarch64 工作区 `CXX=clang++ make test` → `All tests ok.`（退出码 0）；
  conan-verify G2 内 test_package ctest `test_jsonxx` 通过（1/1） |
| 如实回填 | 上游 138 断言全过（100%）；适配后 test_package 21 项 CHECK 全过 |

## 验证结果

```bash
# 上游测试
cd /storage/Users/currentUser/builds/jsonxx-1.0.1.work && CXX=clang++ make test
# → All tests ok. (exit 0)

# Conan 配方验证
python3 scripts/ohc-run.py conan-verify jsonxx 1.0.1
# → G1/G2/G3/G4/L2/L4/L5 全 PASS，报告: reports/conan-verify-report.md

# W3 本地 CI 模拟（finish 内）
# → build_and_test.sh L0 pass, Pass rate 100.0% (1/1)，.ci-result.json exit_code=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 纯 Makefile 库配方：jsonxx.cc 编译为静态库 + 头文件安装 |
| conandata.yml | 官方 v1.0.1 tarball（sha256 已核验） |
| test_package/ | 消费者测试（CMake + CHECK 宏，21 项断言）+ MANIFEST 申报 |
| manifest.yaml | status=built，构建系统 makefile |
| reports/ | conan-verify-report.md / test-report.md / w3-local-ci.log |

## 注意事项

- jsonxx 为 header + 单源库，无 configure/install 目标，配方须直接编译打包。
- test_package 不得用 assert() 判定（NDEBUG 陷阱，详见知识判定审计节）。
- 浮点断言必须容差比较。

---

**编译结束**: 2026-09-22 16:04
**最终状态**: built

## 知识判定审计（本地只读快照查重）

- knowledge_snapshot: /storage/Users/currentUser/runnerljs002/knowledge-snapshots/jsonxx-1.0.1-r01-20260922T072744Z
  - repository: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git
  - ref: main, HEAD: 48d9cee6844d0fca1f25e86c2df1293b904855d8, sparse: knowledge
- 扫描范围: knowledge/graph/E*.kv（540 正式条目）+ knowledge/doc/*.md + knowledge/drafts/* 草稿
- 候选 1（test_package 中 assert 在 Release/NDEBUG 下被编译掉导致测试失效）:
  - 等价命中: DRAFT-cpplocate-2.3.0-test-package-reliability（NDEBUG 静默通过根因一致）、
    DRAFT-devio-1.2-consumer-test-no-tmpfile-popen-capture（明确禁止 assert() 判定）
  - 逐字段验证: error_signature/root_cause（NDEBUG 下 assert 不求值）/rec_approach（CHECK 宏替代）与本轮实测一致
  - 结论: 等价命中 → knowledge_decision=reuse_existing（路径 A），不创建草稿
- 候选 2（浮点解析精度，jsonxx 解析 3.14 与字面量不 ==）: 属通用浮点容差比较常识；
  E306/E388/E401 为其他库具体数值问题，无直接等价；不阻塞，走路径 A（path_a_no_knowledge 子项）
- 最终: knowledge_decision = 路径 A（常规基础适配），无新草稿；标题前缀【积分赛】；issue_action: none
