# XaoS 4.3.4 上游测试清点

## 范围

- 上游：<https://github.com/xaos-project/XaoS>
- 发布标签：`release-4.3.4`（官方提交 `9e1d900de70b7478a2dd8f8498a9a7285796d309`）
- 官方源码归档：<https://github.com/xaos-project/XaoS/archive/refs/tags/release-4.3.4.tar.gz>
- SHA-256：`4bb1c6bdc3a136e7bdceaa626ae48944ef289cdc092dc5e46b4f8e9e049c5b07`

## 清点结果

| 项目 | 数量 | 证据/说明 |
|---|---:|---|
| `tests/` 目录 | 0 | 源码归档中不存在该目录 |
| `test/` 目录 | 0 | 源码归档中不存在该目录 |
| CMake/CTest 注册用例 | 0 | `CMakeLists.txt`/`.cmake` 中没有 `enable_testing`、`include(CTest)`、`add_test` 或 `BUILD_TESTING` |
| 上游正式自动化测试 | 0 | 没有可运行的正式测试目标 |
| `.xpf` 示例位置文件 | 169 | `examples/` 下的示例数据，不是测试用例 |
| `tools/nametest.sh` 扫描 | 1 次 | 检查 `.xpf` 文件 basename 是否重复；169 个文件中重复项为 0 |

## 执行记录

1. 对 CMake 文件检索 CTest 注册宏，未发现注册用例；源码中也没有 `tests/` 或 `test/` 目录。因此上游测试用例总数为 0，运行数、通过数、失败数和跳过数均为 0（分母为 0，不计算通过率）。
2. 执行 `cd examples && sh ../tools/nametest.sh`。脚本无输出并返回 1；检查脚本可知它用 `grep -v " 1 "` 输出重复 basename，grep 在无匹配时返回 1。对同一 169 个 `.xpf` 文件独立计数得到 0 个重复项，因此扫描结果符合预期。此脚本是示例文件命名检查，不计作正式测试用例。
3. 上游没有需要修改或跳过的正式测试；未运行数为 0。HarmonyOS 上新增的消费者渲染测试单独列在 `test_package/MANIFEST.yml`，不计入上游测试分母。

## 配置清点命令

```text
rg -n -i 'enable_testing|add_test\(|include\(CTest\)|BUILD_TESTING' <source> --glob 'CMakeLists.txt' --glob '*.cmake'
Get-ChildItem <source> -Recurse -Directory | Where-Object { $_.Name -match 'test' }
(Get-ChildItem <source>/examples -Recurse -Filter '*.xpf').Count
```
