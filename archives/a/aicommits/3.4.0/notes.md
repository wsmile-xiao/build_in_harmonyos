# aicommits 3.4.0 适配笔记

## 编译环境
- 构建系统: npm (Node.js CLI)
- 编译日期: 2026-08-11
- 运行时: node v24.13.0 (hnp)
- 状态: published

## 编译步骤

1. `ohc-run.py init-build aicommits 3.4.0 --url=https://registry.npmjs.org/aicommits/-/aicommits-3.4.0.tgz`
2. 验证零依赖：`node dist/cli.mjs --version` → 3.4.0（npm tarball 已含打包产物，无编译步骤）
3. conan-init 生成配方 → 重写 conanfile.py 为 application 打包配方：
   - dist/* + package.json + LICENSE → libexec/aicommits/
   - 生成 bin/aicommits 启动脚本（exec node <libexec>/dist/cli.mjs "$@"）+ aic 别名
4. test_package：test.sh 真实执行 `aicommits --version` 断言 3.4.0（R34）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | npm/node 崩溃（Signal 5, Check failed: 12 == errno） | 当前 shell 环境变量污染（HOME 未正确解析，uv_os_homedir ENOENT） | 用干净环境 `env -i PATH=... HOME=... TMPDIR=... npm` 运行 |
| 2 | autotools 模板不适用 | aicommits 是零依赖纯 JS CLI，无 configure/make | 重写为 application 打包配方，直接打包 dist/ + 启动脚本 |

## 源码修改
无（npm 发布包即最终产物）

## 测试结果
- 消费者验证：aicommits --version → 3.4.0 ✅，--help 可用 ✅
- 上游 npm 包无内置测试套件（上游仓库测试依赖 Git 环境，不在发布包内）
---

**编译结束**: 2026-08-11 06:18
**最终状态**: published
