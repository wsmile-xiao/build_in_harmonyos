# debian-pan 0.4 — 本地测试报告（R51 上游测试三步法）

> 任务：debian-pan 0.4 适配（Debian Pan Pure Blend 元数据包 → Conan
> data/metadata 配方）
> 上游测试：**0/0**（确无测试套件，R51 清点证据见本文 §2 与
> test_package/MANIFEST.yml）
> 本地测试：`conan create` + test_package 数据校验 **48/48 = 100%**
> 运行环境：HMDFS（chmod 不生效，X_OK 恒 False）；conan 2.29.1 + ohpcd remote

## 1. 测试对象与执行方式

- 配方：`archives/d/debian-pan/0.4/conanfile.py`（data/metadata package，
  `package_type="unknown"`，零 Conan requires，不产 bin/ 与 ELF）
- 测试：`test_package/test_debian_pan.py`（48 项断言），由
  `test_package/conanfile.py` 的 `test()` 经 `self.run("python3 ...")` 实际执行
  （R34/L0d：非空壳测试）
- 执行命令：

```bash
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

- 执行结果：`conan create` exit 0；test_package 输出
  `checks: 48, failures: 0 ==> ALL PASSED (100.0%)`

## 2. 上游测试清点（R51，N=0 证据）

| 清点项 | 命令 | 结果 |
|---|---|---|
| 测试文件 | `find . -iname '*test*'` | 0（无任何含 test 的文件/目录） |
| tests/ 目录 | `find . -type d` | 无 tests/（仅 config/ debian/ dependency_data/ tasks/） |
| ctest 注册 | `find . -name 'CTestTestfile.cmake'` | 0（无 CMake 构建系统） |
| pytest 注册 | `find . -name 'test_*.py' -o -name 'conftest.py'` | 0 |
| 可编译单元 | `find . -name '*.c' -o -name '*.cpp' -o -name '*.h'` | 0（35 文件全为打包元数据） |
| **合计** | — | **0** |

上游构建系统为 Debian 专有（顶层 `Makefile` 仅
`include /usr/share/blends-dev/Makefile`；`debian/rules` 仅
`include /usr/share/blends-dev/rules`），不存在可运行的测试入口。

## 3. 适配后测试：test_package 48 项断言（全部 PASS）

| 组 | 覆盖内容 | 断言数 |
|---|---|---|
| ① 打包布局 | share/debian-pan/{tasks, tasksel, dependency_data, registry.json} + licenses/ + tasks 计数 | 6 |
| ② 鸿蒙特有测试（OHOS 平台适配预检） | 无 bin/ 目录（L0k/R38 不伪装 CLI）、无 lib/ 目录（R26 不适用）、无 ELF 产物（OHOS 拒 execve 未签名 ELF）、无 .so/.a/.o、交付面仅 share/+licenses/ | 5 |
| ③ tasks/ Deb822 结构 | 18 文件、Format == blends 1.1、Task == 文件名、Description 非空 | 4 |
| ④ tasksel desc 结构 | 17 段落、父任务 debian-pan、16 Key 且均 pan-* | 5 |
| ⑤ registry 交叉复核 | blend/version、计数与打包文件重派生一致、任务标题与 format 重派生一致 | 12 |
| ⑥ debian/control 声明 | 18 包全 Architecture: all、16 元包、映射不对称如实记录 | 8 |
| ⑦ 官方快照 | 主题集合 == tasks/ 集合、5 字段均为数组、446 去重引用 | 5 |
| ⑧ semantics | conan_requires == none、blends 1.1 记录、映射不对称记录 | 3 |
| **合计** | — | **48** |

关键点：⑤ 的计数与标题均为**从打包文件重新派生**后再比对 registry.json，
不是同义反复（test_package 自带独立的 Deb822 解析器）。② 组即"鸿蒙特有测试"，
对应 PR 模板「适配后测试用例统计」的鸿蒙特有测试行（针对 HarmonyOS PC 平台
特性的校验：零二进制交付面、无未签名 ELF、不伪装 CLI 工具）。

## 4. 通过率

```
checks: 48, failures: 0
==> ALL PASSED (100.0%)
pass rate: 100.0% (1/1)     # CI build_and_test.sh Build Summary
```

- 上游测试用例通过率：**0/0**（上游确无测试，附清点证据）
- 适配后本地测试通过率：**48/48（100%）**
- 本地 CI 模拟（W3）：exit_code=0（`.ci-result.json`，log_sha256 佐证）

## 5. 与知识草稿的关系

本次适配把原有两条草稿的结论**从"不可适配"修正为"数据包诚实建模"**：
R47 语言预检给出 `detected=c` 是检测器盲区（顶层 Makefile + 零可统计源文件），
但盲区不等于需要伪造 C 编译，也不等于放弃适配。E560 记录盲区判定与正确
处置，E563 记录无测试上游的本地验证补充模板（本报告即其落地实例）。
