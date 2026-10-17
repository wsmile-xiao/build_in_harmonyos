# most 5.2.0-r2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: pending (CI evidence 门禁待通过)

## 编译步骤

```bash
./configure --prefix=/usr
make -j$(nproc)
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 依赖 S-Lang 库 | most 是 S-Lang 的消费者，需要 slang 库的头文件和链接 | 在 conanfile.py 中声明 slang/2.3.3 依赖 |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| slang | 2.3.3 | S-Lang 库，most 的终端显示基础 |

## 验证结果

```bash
most --version
most --help
```

## 注意事项

1. 首次适配，暂无补丁，无平台适配问题
2. 依赖 slang 必须先发布到制品仓
3. most 是二进制工具，非库，package_type 为 application

## round 14 — evidence 门禁 no_tests 策略调整（同指纹第 3 次）
真机预检 `conan create` + test_package 全过，唯一阻塞是 evidence 门禁报
"no_tests 仅在清单显式设置 upstream_tests_exist: false 并提供 upstream_test_audit 后允许通过"。
前两轮只在 test_package/MANIFEST.yml 和 manifest.yaml 添加 upstream_tests_exist/upstream_test_audit/reason 字段（YAML 解析确认存在且类型正确），门禁仍拒。
本轮不同策略：守则要求"并输出 status:no_tests、discovered:0、executed:0 及具体 reason"——之前 HMBS_UPSTREAM_TEST_RESULT 标记缺 reason 字段。本轮在标记 JSON 中补 reason（151 字符，与 manifest reason 一致），让门禁能交叉核验 stdout 与 manifest。
AI Review P1（--prefix=/usr → /）不采纳：真机日志显示 most resolved: .../usr/bin/most，conan create 通过，当前路径 + cpp_info.bindirs=["usr/bin"] 已验证可用，改 / 会破坏已通过配置。
P2（notes.md status: built 与 CI 矛盾）采纳：改为 pending。manifest.yaml status: built 保留——它表示配方是否可编译（真机 conan create 通过证实），非 CI/PR 状态。