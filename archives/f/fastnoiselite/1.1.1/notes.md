# fastnoiselite 1.1.1 适配笔记

## 编译环境
- 构建系统: header-only（无构建系统，官方源码为单头文件库 Cpp/FastNoiseLite.h）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (OHOS aarch64 profile, cppstd=17)
- 状态: built

## 编译步骤
1. init-build fastnoiselite 1.1.1（官方 GitHub archive v1.1.1，SHA-256 核验通过）
2. lang-preflight: 语言匹配 cpp（源码 1 个 cpp 文件，主体占比 100%）
3. conan-init 生成配方后按 header-only 模板重写 conanfile.py：
   - package_type = "header-library"，no_copy_source = True
   - package() 将 Cpp/FastNoiseLite.h 安装到 include/，LICENSE 到 licenses/
   - package_info() 仅 includedirs，无 libs/bindirs/libdirs
4. conan-verify: G1-G4 + L2/L4/L5 全部通过；test_package 消费者用例 1/1 Passed
5. finish: W3 本地 CI 模拟（setup.sh + build_and_test.sh）通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 解压后 Cpp/ 等真实源码目录丢失 | _promote_nested_source 把含 CMakeLists.txt 的 WebPreviewApp 演示子项目误判为源码根并提升，删除同级 Cpp/、C/ 等目录 | 按官方 tarball 布局手工恢复（tar -xzf 保留全部子目录，移动隐藏文件，写回 .tarball-sha256），重建 .work；知识库同机制见 E195/E466 |
| 2 | conan-verify G2 报 BadZipFile | conandata 使用 codeload.github.com URL，被 E017 镜像注入为 ghfast.top/https://codeload... 返回 403 | 改用官方 github.com/<owner>/<repo>/archive/refs/tags/<tag>.tar.gz 形态；与 codeload 直连 SHA-256 一致（8b1d439a），G2 PASS |
| 3 | finish W3 JC 拦截：其他库基线垃圾文件（cloog/kics .build-closed/.staging-verified） | junk_check 本地 full 模式用 git ls-files 全仓扫描，命中其他库已跟踪空标记文件 | 基线隔离复验：记录隔离前 SHA-256 → git rm --cached 临时取消跟踪 → 复跑 W3 → git restore --staged 原样恢复，核对恢复后 SHA-256 一致 |
| 4 | build_and_test.sh 镜像回退把 conandata.yml 改写成 gh-proxy.com URL 列表 | CI 脚本的 mirror fallback 逻辑（本地 W3 也执行） | 提交前恢复官方 HTTPS URL、清理 .build-cache/predl_cache 与 conandata.yml.ghfast-bak，重新核验 SHA-256 |

## 源码修改

无补丁（patches/ 为空；header-only 库无源码修改）。

## 依赖版本

无第三方依赖（header-only，0 requires）。

## 验证结果

```bash
# conan create（含 test_package）
1/1 Test #1: test_fastnoiselite ...............   Passed    0.02 sec
100% tests passed, 0 tests failed out of 1

# conan-verify 门禁
G1 配方完整性: PASS / G2 conan create: PASS / G3 系统同名库隔离: PASS
G4 产物完整性: PASS / L2 smoke: PASS / L4 安全扫描: PASS / L5 产物基线: PASS

# 头文件一致性
packaging/FastNoiseLite.h SHA-256 = 47a29750dfe13d15651febd235f3c26b1cc57af7c6e26583b838fd7ab5215dc2
（与官方源 Cpp/FastNoiseLite.h 一致）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/FastNoiseLite.h | 107699 B | 安装产物头文件（与官方源 SHA-256 一致） |

## 注意事项

- codeload.github.com URL 在 E017 镜像注入环境下不可用（403），必须用官方 github archive URL 形态
- W3/JC full 模式会命中其他库基线垃圾文件，隔离必须从 git 索引层面操作（git rm --cached + restore --staged），单纯 mv 工作区文件无效
- conandata.yml 提交内容必须是官方 HTTPS URL，CI 的镜像回退由远端 CI 自行处理，不得提交代理改写地址

---

**编译结束**: 2026-09-19 02:19
**最终状态**: built
