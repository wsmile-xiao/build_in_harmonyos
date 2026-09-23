# covtobed 1.3.5 测试报告

## 测试基线

上游发布归档包含一个官方集成测试脚本 `test/test.sh`。按可机械复核的
独立条件检查计数，该脚本有 14 项检查：版本输出、排序输入、非排序拒绝、
最小覆盖度、物理覆盖度、链特异输出、counts 头与数据行、相邻区间、两组
精确输出比较、两种无效比对过滤行为，以及人工覆盖度校验。

消费者测试另外提供 3 项检查：

1. `covtobed --version` 输出 1.3.5；
2. `covtobed --help` 输出程序说明；
3. 对上游 `test/mock.bam` 的等字节内嵌副本运行 `-m 1`，结果与三行预期 BED 完全一致。

## 本机配方预验证

环境：macOS arm64、Apple clang 17、Conan 2.29.1。依赖按同版本配方从源码
构建；为修正 zlib 依赖配方的 OHOS 默认解释器路径，本机命令显式设置
`CONFIG_SHELL=/bin/bash`。

| 测试集 | 发现 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|---:|
| 上游 `test/test.sh` | 14 | 14 | 0 | 0 |
| Conan `test_package` | 3 | 3 | 0 | 0 |
| 合计 | 17 | 17 | 0 | 0 |

关键结果：

```text
ALL TESTS: PASSED
HMBS_TEST_SUMMARY discovered=3 passed=3 failed=0 skipped=0
```

## OHOS 依赖图验证

使用仓库 `ci/conan/profiles/ohos-aarch64`（OHOS 6.0、armv8、clang 15、
libc++、C++17）执行 `conan graph info` 成功。以下二进制包均命中 ohpcd
制品仓缓存，没有触发下游源码重建：

- `bamtools/2.5.3`
- `zlib/1.3.1.1`
- `perl/5.42.2`（build requirement）

## 结论与边界

配方结构、依赖闭包、源码编译、上游测试和消费者测试已完成本机预验证，
17/17 全部通过。本机不存在 OHOS SDK 和 OHOS 可执行环境，因此本报告不把
macOS 运行结果标记为 OHOS 真机构建；目标平台结果以 W3/远端 CI 为准。
