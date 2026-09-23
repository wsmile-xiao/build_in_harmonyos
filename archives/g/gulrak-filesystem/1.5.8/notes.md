# gulrak-filesystem 1.5.8 适配笔记

## 编译环境
- 构建系统: cmake（header-only，无 autotools）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 / clang++（OHOS aarch64-linux-ohos triplet）
- 状态: built

## 编译步骤

1. `python3 scripts/ohc-run.py init-build gulrak-filesystem 1.5.8 --url=https://github.com/gulrak/filesystem/archive/refs/tags/v1.5.8.tar.gz`
   - 源码 sha256: 726f8ccb2ec844f4c66cc4b572369497327df31b86c04cefad6b311964107139
   - tag v1.5.8 与头文件内 `GHC_FILESYSTEM_VERSION 10508L` 一致
2. `python3 scripts/ohc-run.py lang-preflight gulrak-filesystem 1.5.8 --src <work>` → detected=cpp，匹配
3. 原生构建（clang 15, C++17）：
   - `cmake -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17 -DGHC_FILESYSTEM_BUILD_EXAMPLES=ON -DGHC_FILESYSTEM_BUILD_TESTING=ON`（exit 0）
   - `make -j2`（exit 0；filesystem_test/cpp17/cpp20/multifile_test/fwd_impl_test/exception 全部链接成功）
   - `ctest --output-on-failure`（175/209 通过，34 项失败均为 OHOS HMDFS 平台能力限制，详见 reports/test-report.md §3）
4. `python3 scripts/ohc-run.py conan-init gulrak-filesystem 1.5.8`
   - conanfile.py 按 header-only 模板重写（package_type=header-library，无编译阶段，package() 复制 include/ghc/*.hpp）
   - conandata.yml 填入官方 URL + 真实 sha256
5. `python3 scripts/ohc-run.py conan-verify gulrak-filesystem 1.5.8` → G1-G4/L2/L4/L5 全部通过，可标记 published
6. `python3 scripts/ohc-run.py finish gulrak-filesystem 1.5.8 built` → W2 结构/原子性、R36 依赖、W3 本地 CI 模拟通过（见下方基线隔离复验记录）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 的 test_package 阶段报 Imported target 引用不存在的 include 路径 | header-only 配方 package() 用 `copy("*.hpp")` 不匹配 `include/ghc/` 子目录，包内 include 为空 | package() 改用 `copy("ghc/*.hpp", src=source_folder/include, dst=package_folder/include)` 保留相对路径 |
| 2 | W3 JC5 误报 `archives/u/util-linux-login/2.42.2/.ci-trigger`（其他库 main 基线文件） | junk_check full 模式基于 `git ls-files` 索引扫描，main 上既有未登记 dotfile | 按任务基线隔离协议：记录 pre_sha256 → `git rm --cached` 临时隔离 → W3 通过 → `git add -f` 原样恢复，pre/post sha256 一致（e3b0c4...b855），git 状态干净 |
| 3 | 上游 34 项测试失败 | OHOS HMDFS 平台禁止硬链接/FIFO/socket/mknod，chmod 权限位归一化 | 实测确认平台能力限制（ln/mkfifo/mknod → Operation not permitted），属上游用例在 OHOS 平台不可运行的真实技术原因，非库缺陷；如实计入全量通过率分母 |
| 4 | gen_summary 报 `'str' object has no attribute 'append'` | 其他库 qpdf/12.3.2 的 manifest.yaml 基线数据格式（knowledge_gained 为字符串而非列表），框架解析脚本崩溃 | 其他库基线数据问题，非当前库引入；finish 步骤表标注 gen_summary 为非致命步骤，SUMMARY.md 以既有内容为准 |

## 源码修改

无补丁（patches/ 为空）。header-only 纯头文件库，未改上游源码。

## 依赖版本

无外部 Conan 依赖（header-only，自包含）。

## 验证结果

```bash
# 上游测试（clang 15, C++17, cwd=/storage/Users/currentUser/tmp/builds/gulrak-filesystem-1.5.8-build）
ctest --output-on-failure   # 175/209 通过；34 项失败均为 HMDFS 平台能力限制

# HarmonyOS 专项测试（16 断言全过）
clang++ -std=c++17 -I<src>/include test_package/src/test_ghc_fs.cpp -o ghc_ohos_test && ./ghc_ohos_test
# → RESULT: checks=16 failures=0（exit 0）

# Conan 验证（ohos-aarch64 profile）
conan create archives/g/gulrak-filesystem/1.5.8 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# → conan-verify G1-G4/L2/L4/L5 全通过
```

## 注意事项

- gulrak-filesystem 是 header-only 库（ghc::filesystem），package 无 bin/lib 产物，G3/L2/L5 按 header-only 预期处理。
- OHOS 平台硬链接/FIFO/socket/mknod 不可用是 HMDFS 既有语义，任何消费该库的项目在 OHOS 上创建这些特殊文件时须预期 error_code 非零（库已如实透传，不崩溃）。
- 官方 GitHub tarball 下载时 CI 的 E017 会自动注入镜像 fallback，本库 conandata.yml 始终保留官方 HTTPS URL（gh-proxy 仅出现在临时注入备份，已清理）。
---

**编译结束**: 2026-09-06 23:20
**最终状态**: built
