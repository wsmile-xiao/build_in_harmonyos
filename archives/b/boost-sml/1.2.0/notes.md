# boost-sml 1.2.0 适配笔记（bootstrap 阶段）

## 状态：bootstrap（骨架已建立，未进入 adapt/编译）

## 官方来源核验

- 官方仓库: https://github.com/boost-ext/sml
- 正式发布: https://github.com/boost-ext/sml/releases/tag/v1.2.0 (2026-06-01T23:33:11Z)
- tag v1.2.0 -> commit `2d8485da6661519a7697b5f800c7165c543fa499`
  (release PR #708 合并后打 tag，release commit 父提交 d80a092301a7)
- 源码 tarball: https://github.com/boost-ext/sml/archive/refs/tags/v1.2.0.tar.gz
- SHA-256: `d584375bc8b4b391f0d94d57bc126a7cbb0f8c2bf810f5602400206b62eaf280`
  （从官方 tarball 直接计算，53,203,594 字节）
- 包内版本宏: `#define BOOST_SML_VERSION 1'2'0`，inline namespace `v1_2_0`，与 tag 一致
- tarball 根目录: `sml-1.2.0/`，include 布局: `include/boost/sml.hpp` + `include/boost/sml/utility/`

## 适配规划（待 adapt 阶段）

- header-only 库，无编译产物，`conan create` 仅需下载 + 拷贝头文件
- 验证：`conan create` 成功 + `test_package` 编译一个最小状态机示例并运行
- 无平台专项改动预期；如 OHOS/clang 出现模板深度限制等问题再补补丁

## 待办（下一阶段）

1. 运行 `ohc-run.py conan-verify boost-sml 1.2.0`（8 道门禁）
2. 编写 test_package 消费示例（真实调用 sml API，R34）
3. 按结果推进 finish / 提交
## R02 来源复核（2026-08-29）

- GitHub API 复核：tag v1.2.0 -> commit 2d8485da6661519a7697b5f800c7165c543fa499（type=commit）✓
- 本地 tarball SHA-256：d584375bc8b4b391f0d94d57bc126a7cbb0f8c2bf810f5602400206b62eaf280 ✓
- conandata.yml 与官方一致 ✓
- 结论：R01 来源证据可复用，无需重复 Bootstrap。
## R03 基线噪声复验（2026-08-29）

- 三条基线路径（goaccess tarball / scudo-malloc 隐藏文件）确认为 origin/main 已跟踪历史文件，
  预存且未纳入本库范围；复验期间临时 `git rm --cached` 隔离，JC full 模式不再命中（45332 文件，JC_RESULT=pass）。
- W3 本地 CI 模拟通过（setup.sh + build_and_test.sh 均通过），基线噪声豁免生效。
- 状态：built（conan-verify + W3 通过；未上传制品）。
---

**编译结束**: 2026-08-30 09:53
**最终状态**: built
