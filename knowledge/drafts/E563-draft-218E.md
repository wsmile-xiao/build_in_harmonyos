# E563-draft-218E — R51 无测试上游（元数据/数据型包）的验证补充模板

## 错误面（现象）

- **触发**：R51 上游测试三步法的"清点 → 运行 → 回填"，遇到**上游确无测试**的
  元数据/数据型包（Debian 源码包、blend 元包、纯配置包等）
- **阶段**：testing（适配验证 / PR 申报）
- **签名**：`find . -iname '*test*'` 输出为空 / 无 tests/ 目录 / ctest、pytest 注册数 = 0 /
  `upstream_tests: []`

## 识别

- severity: 1（🟢minor —— 非编译错误；是 R51 申报场景的合规处理模板）
- category: testing, detection, packaging, ohos

## 诊断

R51 要求适配前清点上游测试并**实测回填 N/N/通过率（禁占位符）**；
"上游确无测试"必须附清点证据（否则防 pixman 式谎报）。

debian-pan 0.4 实测清点（R51 证据）：

```console
$ find . -iname '*test*'          # → 输出为空
$ find . -type d                  # → 无 tests/ 目录
$ find . -name 'CTestTestfile.cmake' | wc -l   # → 0
$ find . -name 'test_*.py' | wc -l             # → 0
$ find . -name '*.c' -o -name '*.cpp' -o -name '*.h' | wc -l   # → 0
```

35 文件构成：Makefile（仅 include blends-dev）、debian/、config/、tasks/(18)、
dependency_data/(4 JSON)、debian-pan-tasks.desc、COPYING。
**零 C/C++ 源码、零可执行程序、零测试框架** —— "没有测试"不是技术故障，
而是资产形态使然。唯一可验证资产 = 打包产物的结构与语义自洽性。

## 方案：把校验做进交付物（test_package 消费者校验套件）

关键区别：**不要外挂一个独立脚本**，而是把校验写进 `test_package/`，
由 `test()` 内 `self.run(...)` 实际执行（满足 R34/L0d 非空壳要求），
`conan create` 时自动触发，CI 的 L1 门禁直接消费这一结果。

参考实现 `archives/d/debian-pan/0.4/test_package/test_debian_pan.py`，
八大类共 48 项断言：

| 类 | 校验内容 | 断言数 |
|---|---|---|
| ① 打包布局 | share/debian-pan/{tasks, tasksel, dependency_data, registry.json} + licenses/ | 5 |
| ② 诚实性 | 无 bin/ 目录、无 ELF 产物（数据包不得伪造成 CLI 工具） | 2 |
| ③ 上游产物 Deb822 结构 | 18 文件、Format == blends 1.1、Task == 文件名、Description 非空 | 4 |
| ④ tasksel desc 结构 | 17 段落、父任务、16 Key 且均 pan-* | 5 |
| ⑤ registry 交叉复核 | 计数与标题**从打包文件重新派生**后比对（非同义反复） | 10 |
| ⑥ debian/control 声明 | 18 包全 arch:all、16 元包、映射不对称如实记录 | 7 |
| ⑦ 官方依赖快照 | 主题集合 == 任务文件集合、5 字段均为数组、446 去重引用 | 6 |
| ⑧ 语义记录 | conan_requires == none、blends 1.1、映射不对称 | 3 |

运行与上报：

```bash
conan create archives/d/debian-pan/0.4 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
# test_package: checks: 48, failures: 0 ==> ALL PASSED (100.0%)
# build_and_test.sh Build Summary: Pass rate: 100.0% (1/1)
```

**三方一致**（审计交叉核验点）：

1. `test_package/MANIFEST.yml` → `assertion_count: 48` + `upstream_test_evidence`
   清点证据 + `upstream_tests: []`
2. `reports/test-report.md` → 逐组断言表 + 通过率 48/48（100%）
3. `conan create` 实际输出 → `checks: 48, failures: 0`

PR 模板「适配后测试用例统计」按此填：单元/集成测试 0（无 API/二进制可测），
"结构/元数据有效性校验 + 鸿蒙特有测试"列真实数字，与上游 N=0 形成对比。

## 禁止

- ❌ PR 模板测试对比表填"待验证 / N/A / 待 CI 验证"等占位符（R51 硬性拒绝）
- ❌ 谎报上游测试数（pixman 42 个测试文件谎报 0 被评审反查揭穿）
- ❌ `assertion_count` 与真实断言数不符（审计会交叉核验三方数字）
- ❌ 空壳测试：`print("ok")` / 裸 `pass` / `assert True`（L0d、PF3、R34 会拦）

## 关联

- 该不该适配、如何建模：E560（R47 检测器盲区 → metadata/registry 包）
- 大型同族实例的分流：E564（debian-science 1.15）
