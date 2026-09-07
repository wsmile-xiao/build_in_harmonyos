# boost-te 1.0.0 适配笔记

## 编译环境
- 构建系统: header-only（C++17 单头文件库，无编译阶段；上游 CMakeLists 仅 examples+tests，无 install 规则）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 / clang++（aarch64-unknown-linux-ohos，OHOS SDK）
- 状态: published

## 编译步骤

header-only 库无 configure/make 步骤。适配流程：

```bash
# 1. 初始化（下载官方 v1.0.0 归档 + 双轨解压）
python3 scripts/ohc-run.py init-build boost-te 1.0.0 \
  --url=https://github.com/boost-ext/te/archive/refs/tags/v1.0.0.tar.gz
# 2. 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight boost-te 1.0.0 --src $BUILD_SRC_DIR   # cpp 匹配
# 3. 配方生成 + 验证（header-only 模板，G1-G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py conan-init boost-te 1.0.0
python3 scripts/ohc-run.py conan-verify boost-te 1.0.0    # exit 0
# 4. 上游测试 28/28（独立编译运行）
clang++ -std=c++17 -O2 -Wall -Iinclude -Itest test/te.cpp -o te && ./te   # exit 0
# 5. finish（W2 原子性 + W3 本地 CI 100%）
python3 scripts/ohc-run.py finish boost-te 1.0.0 published   # 状态 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G1 失败：header-only 配方缺 build()/export_sources()/补丁调用 | G1 门禁逐字检查方法名文本 | 补充 export_sources()+build()（apply_conandata_patches，patches 空为无操作） |
| 2 | G2 失败：test_package 配置期 "Imported target includes non-existent path .../p/include" | package() 的 copy() 用相对 dst 被解析到 build 目录，包内缺 include | src/dst 全部改用 os.path.join 绝对路径 |
| 3 | test_package 编译失败：te::as/te::ref 不存在、te::call 返回 void | v1.0.0 的 te::call 模板首参为返回类型（默认 void）；te::as/te::ref 为更新版 API | te::call<int>/te::call<int64_t> 显式返回类型；te::poly<T>{Concrete{}} 隐式构造 |
| 4 | finish W3 JC5 fail：full 模式扫到 origin/main 其他库基线杂项 .ci-trigger | 新库分支零提交，junk_check 三点 diff 为空回退 full 整仓扫描 | 先 commit 本库工作使三点 diff 非空，回退 incremental 只查本库（commit-first） |

## 源码修改

无补丁。header-only 库未修改任何上游源码（patches: {}）。

## 依赖版本

无外部依赖（header-only，C++17 标准库即可）。

## 验证结果

```bash
# conan-verify（G1-G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py conan-verify boost-te 1.0.0   # exit 0
# W3 本地 CI（incremental 9 文件，JC/L0/L1 pass，100%）
python3 scripts/ohc-run.py finish boost-te 1.0.0 published  # 状态 published
# 上游测试 28/28 通过（clang++ -std=c++17 -O2 -Iinclude -Itest test/te.cpp && ./te）
# test_package 消费者测试 + OHOS 专项测试 编译/运行退出码 0
```

## 知识沉淀（路径 B 草稿）

- DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental（.kv/.md 配对，与归档同 PR）
  1. header-only 配方 package() 的 copy() src/dst 必须绝对路径（相对 dst 解析到 build 目录，
     包内缺 include → "Imported target includes non-existent path"）
  2. te v1.0.0 的 te::call 首参为返回类型（默认 void）需显式 `te::call<int>`；v1.0.0 无
     te::as/te::ref，用 te::poly<T>{Concrete{}} 隐式构造
  3. 新库分支零提交时 W3 junk_check 回退 full 模式误伤他库基线杂项；先 commit 本库工作
     使三点 diff 非空即回退 incremental（commit-first 规避，零副作用）
- 查重结论：C1 命中 E257 复用；C2+C4 为组合/边界新增差异 → new_draft（路径 B）

## 注意事项

- 上游 CMakeLists.txt 无 install() 规则（仅 examples+tests），header-only 配方直接打包头文件树
- G1 门禁要求 header-only 配方也声明 build()/export_sources()/apply_conandata_patches
- origin/main 上 util-linux-login/.ci-trigger 为其他库基线杂项（空 blob），与本 PR 无关，
  真实 CI pr.diff 模式不受影响
- conandata.yml 只写官方原始 URL（gh-proxy 等镜像前缀由 CI 自动注入，R13）
---

**编译结束**: 2026-09-05 06:10
**最终状态**: published
