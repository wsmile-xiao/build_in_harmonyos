# enchantum 0.4.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库，C++17）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18 附带）+ OHOS aarch64 交叉工具链
- 状态: published

## 编译步骤

1. `ohc-run.py init-build enchantum 0.4.0 --url=.../archive/refs/tags/0.4.0.tar.gz` — 下载官方 tag 源码（经 gh-proxy.com，SHA-256 964a9789 双重一致）
2. 上游测试构建（C++17 规范配置）：cmake + FetchContent(Catch2 本地 overlay) → `ctest` 362/362 通过
3. `ohc-run.py conan-init` → 手工调整 conanfile.py 为 header-only 配方（package_type=header-library、cpp_info.libs=[]、package_id clear）
4. `ohc-run.py conan-verify` — G0-G4 全 PASS（G2 干净 conan create 通过）
5. `ohc-run.py finish published` — W2 原子性 + W3 本地 CI 模拟通过（JC prdiff 0 拦截、conan create passed、test_package 实际执行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载返回 HTML | URL 传仓库主页而非 tag 压缩包 | 改用 `archive/refs/tags/0.4.0.tar.gz`（tag 无 v 前缀） |
| 2 | github.com 直连超时 | 大陆网络访问 GitHub 不稳定 | 经 gh-proxy.com 通道下载（E017 知识） |
| 3 | FetchContent 拉取 Catch2 失败 | github.com 不可达 | FETCHCONTENT_SOURCE_DIR_CATCH2 指向本地已解压 Catch2 源码 overlay（E292 知识） |
| 4 | W3 junk_check 误拦其他库历史基线文件 | 本地分支未提交时 diff 为空 → 回退 full 模式 | pr.diff 走 prdiff 模式只扫 PR 文件（草稿 DRAFT-jc-full-scan-baseline-noise-exemption） |
| 5 | OHOS SDK `<format>` 头存在但 std::format 不可用 | libcxx-ohos 占位头 | C++17 规范配置运行上游测试；新增草稿 DRAFT-enchantum-0.4.0-libcxx-ohos-format-stub（路径 B） |
| 6 | libXext/libxext 大小写碰撞显示为修改 | 大小写不敏感文件系统 + 历史目录碰撞 | 哈希记录基线，恢复原状，不入 PR（基线噪声隔离） |

## 源码修改

无源码补丁（header-only 库，配方层完成适配；patches/ 为空）。

## 依赖版本

- Catch2 devel（本地 overlay，仅测试依赖，未入配方 requires）
- 无第三方运行时依赖（header-only）

## 验证结果

```bash
# 上游测试（C++17 规范配置）
cd $HOME/tmp/enchantum-build-cxx17 && ctest   # 362/362 Passed (100%)

# OHOS aarch64 专项测试（任务要求 5）
aarch64-unknown-linux-ohos-clang++ -std=c++17 test_ohos.cpp -o test_ohos && ./test_ohos
# OHOS test: PASS (platform=OHOS, enchantum=All), exit 0
# 产物 SHA-256: 4f95147d930d10e2f240026d4978ce6f55725812c603ec323a1983f8a74cb01b

# 消费者验证（conan create test_package）
# L1a: test_package was executed by conan create [ok]
```

## 注意事项

- 本库为 header-only，版本号 0.4.0 保持上游版本（首次适配，无修复后缀）
- W5 知识完整性检查的 E219/E253/E305 字段缺失为共享框架历史基线，非本库引入
- CI 镜像 fallback 会在 conan create 期间临时改写 conandata.yml，脚本自动恢复官方 URL
---

**编译结束**: 2026-09-03 03:58
**最终状态**: published
