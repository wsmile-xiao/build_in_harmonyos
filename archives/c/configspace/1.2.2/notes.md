# configspace 1.2.2 适配笔记

## 编译环境
- 构建系统: custom (纯 Python)
- 编译日期: {2026-09-02}
- 编译器: 不适用
- 状态: built (本地 Conan 通过，W3 未运行)

## 编译步骤

使用官方 GitHub v1.2.2 源码闭包，在任务专用 Conan home 中以 OHOS 6.0 profile 创建包；纯 Python 包无需编译。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PyPI sdist 缺少测试 fixture | 发布包未包含 test_searchspaces | 改用同版本官方 GitHub tag 源码闭包并绑定 SHA-256 |
| 2 | Windows ohc conan-verify 失败 | `/bin/sh -c` 与 Windows/Conan POSIX 激活脚本不兼容 | 保留 direct conan create 证据，禁止伪造 ci-result |
| 3 | 目标机无 Python/Conan | 设备环境未预置运行时 | W3 置为 NOT_RUN，等待任务自有冻结 runtime closure |

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
上游 pytest: 330/330 passed；任务隔离 Conan create: package + ConfigSpace.ConfigurationSpace API smoke passed。
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-09-02 23:47
**最终状态**: built
