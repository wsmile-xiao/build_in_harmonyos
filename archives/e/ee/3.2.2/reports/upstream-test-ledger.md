# 上游测试完整枚举台账 — ee 3.2.2

## 枚举依据（可复制）

官方 tag 源码：`https://github.com/nimaltd/ee` tag `V3.2.2`
tarball SHA-256：`52416cab022f33a66e3ca3b6effa6e699c93376f5ebbe08eb271b4c599e77e63`
枚举命令：

```bash
tar tzf ee-3.2.2.tar.gz                      # 官方包完整文件清单
find <src> -iname '*test*' -o -iname '*spec*' -o -iname '*bench*' -o -iname '*fixture*'  # 测试相关路径
grep -rilE 'gtest|catch2|unity|cmocka|doctest|assert\s*\(' <src>                          # 测试框架/宏
find <src> -maxdepth 2 \( -name 'CMakeLists.txt' -o -name 'Makefile*' -o -name 'meson.build' -o -name 'configure*' -o -name '*.pro' -o -name 'Kconfig*' \)  # 构建系统
```

## 官方 tag 源码完整文件清单（6 个文件，全部为库本体/文档/许可证）

| 文件 | 分类 | 是否独立上游测试用例 |
|---|---|---|
| `ee.c` | 库实现源码（STM32 HAL 依赖） | 否 |
| `ee.h` | 库公开头文件 | 否 |
| `NimaLTD.I-CUBE-EE_conf.h` | 库配置头文件 | 否 |
| `README.md` | 文档 | 否 |
| `LICENSE.TXT` | 许可证 | 否 |
| `.github/FUNDING.yml` | CI/赞助元数据 | 否 |

## 分类清点（覆盖用户测试源/框架头/样例/基准/fixture/测试脚本/构建目标）

| 类别 | 发现 | 说明 |
|---|---|---|
| 用户测试源（tests/ 等） | 0 | 官方包无任何测试目录 |
| 框架头/源码（gtest/catch2/unity/cmocka/doctest） | 0 | grep 无命中（FUNDING.yml 含 "assert" 一词为误命中，非测试） |
| 样例（example/） | 0 | 无 |
| 基准（bench/） | 0 | 无 |
| fixture | 0 | 无 |
| 测试脚本（*.sh/py 测试） | 0 | 无 |
| 构建目标（CMake/Make/Meson/Autotools） | 0 | 官方包无任何构建系统文件（单文件嵌入式库） |
| 独立上游 TEST_CASE/注册用例 | **0** | 无测试框架、无注册清单 |

## 双口径统计

| 口径 | 数值 |
|---|---|
| `source_declared_total`（官方 tag 源码可复制枚举发现的测试声明总数） | **0** |
| `configured_executable_total`（当前 OHOS 配置实例化/注册的独立可执行用例） | **0** |
| `executed_passed_total` | **0** |
| 失败数 | 0 |
| 未运行/未实例化数 | 0 |
| 全量通过率 | 0/0（无测试声明，N/A） |

## 结论

ee 3.2.2 是 STM32 EEPROM 模拟单文件嵌入式库（上游无测试、无构建系统、无测试框架），
上游测试清点为 **0 个独立用例**（附上述枚举证据，符合 R51 "上游确无测试须附清点证据"）。
因此本库以鸿蒙专项测试（`test_package`/鸿蒙测试用例）与消费者用例承担测试门禁，
见 `reports/` 中对应报告。

> 说明：适配新增的 `main.h`（模拟 STM32 HAL）、`ee_sim_flash.c`（模拟 Flash 存储）为
> 平台适配层，非上游测试；`smoke_test.c` 为本库鸿蒙专项功能自测，计入鸿蒙专项测试口径。
