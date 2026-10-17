# calendar 3.0.0 适配笔记

## 编译环境
- 构建系统: custom（OCaml/dune）
- 编译日期: 2026-08-02
- 平台: OHOS（OpenHarmony PC, aarch64）
- 状态: failed（未适配）

## 编译步骤

```bash
# 下载源码
wget https://github.com/ocaml-community/calendar/archive/refs/tags/v3.0.0.tar.gz

# 解压并进入
tar xzf v3.0.0.tar.gz && cd calendar-3.0.0

# dune 构建（OHOS 无 OCaml 工具链，无法执行）
dune build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `dune build` 不可行 | OHOS 无 OCaml/dune 工具链 | 采用 prefixsuffix 失败记录模式，如实标记 status: failed |
| 2 | test_package 无可编译产物 | 无 OCaml 工具链无法编译 | 校验失败归档内容（manifest + notes）真实性 |

## 验证结果

```bash
# OHOS 上无编译产物，验证失败归档内容
$ python3 test_failed_archive.py <package_folder>
PASS: calendar failed adaptation record is complete
```

## 注意事项
- calendar 是 OCaml 库（dune 构建），OHOS 无 OCaml 工具链，无法编译
- 失败归档包含 status: failed、failure_reason（OCaml/dune 工具链缺失）与 OHOS 说明
- 待 OHOS 支持 OCaml 工具链后可启用真实 dune 构建

---

**编译结束**: 2026-08-02
**最终状态**: failed
