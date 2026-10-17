# libcroco 0.6.13 测试报告

## 一、构建验证（W3 本地 CI）

- `conan create`（-pr:h/-pr:b=ohos-aarch64，clang-15/armv8/Release，静态库）：**通过**
  - 日志：`reports/conan-create.log`
  - 产物：`libcroco-0.6.a`、头文件 28 个（include/libcroco-0.6/libcroco/）、`libcroco-0.6.pc`、CLI `csslint-0.6`、`croco-0.6-config`
- 消费者用例（test_package/consumer.c）：编译、链接、运行 **exit 0**（公开 API `cr_om_parser_simply_parse_buf` + `cr_stylesheet_nr_rules` + `cr_stylesheet_to_string`）
- W3 模拟（build_and_test.sh）：L0=pass（结构/MANIFEST/CLI 检查全过）、L1/L2/L4/L5 全过
  - 日志：`reports/w3-local-ci.log`

## 二、鸿蒙专项测试

- `tests-ohos/ohos_test.c`：OHOS armv8 clang 编译通过，运行 **exit 0**（2 条规则解析、计数、序列化核验）

## 三、上游测试（R51 双口径台账，详见 test-ledger.md）

- 源码声明总数：11（test0–test6 共 7 个 C 程序 + 4 个 shell 脚本）
- 当前配置可执行总数：11，全部实际运行，无跳过/未实例化
- 输出对比：13/16 通过；3 项（test2.1/test2.2/test4.1）存在**上游参考输出陈旧**导致的格式差异
  （参考文件生成于 2003–2004 年；0.6.13 源码为 Bug 381040 浮点格式、Bug 314831/394294
  转义计算修复后的行为，参考未同步；任何平台均复现，非 OHOS 适配缺陷）

## 四、适配补丁

| 补丁 | 用途 |
|---|---|
| 0001-config.sub-ohos.patch | config.sub 加入 linux-ohos 候选 |
| 0002-configure-umask-ohos.patch | config.status 临时目录 umask 077→022（E011，HMDFS） |

另含配方内 E236 修复（依赖 .la 无元数据私有目录）与 test_package 显式依赖声明。