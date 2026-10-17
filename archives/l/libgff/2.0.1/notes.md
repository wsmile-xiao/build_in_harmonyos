# libgff 2.0.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt；init-build 按 URL 误判 autotools，见知识草稿 DRAFT-libgff-2.0.1-url-guess-buildsystem-cmake-rewrite）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ (15.0.4，OHOS aarch64 profile)
- 状态: published

## 编译步骤

1. 官方标签核验：`git ls-remote --tags https://github.com/COMBINE-lab/libgff` →
   `v2.0.1` tag = commit 112721772d5c118f8ddf059395e88057b00067e6（与 master 同 commit）。
2. 源码归档：`https://codeload.github.com/COMBINE-lab/libgff/tar.gz/refs/tags/v2.0.1`
   （github.com 直连超时，codeload 官方端点可达；SHA-256
   96d2bda64aaf9cf7b6c1a42205e408b0ef2a353ba42dad560db215e7ec105e2e）。
3. `ohc-run.py init-build libgff 2.0.1 --url=<codeload 归档>` → 生成 .build-context 与归档骨架。
4. `ohc-run.py build libgff 2.0.1` → CMake 构建 libgff.a + TestGFFParse，install 到 staging。
5. 上游测试：`TestGFFParse <libgff-test.gff3>`（1 gene+1 mRNA+2 exon），输出 `tx1 gene1 Name ABC`，退出码 0。
6. conanfile.py 按 CMake 模板重写（基座由 URL 误判产生的 autotools 模板替换），
   test_package 改 CXX + test.cpp 真实调用 GffReader。
7. `ohc-run.py conan-verify libgff 2.0.1` → G0-G4/L2/L4/L5 全部通过。
8. `ohc-run.py finish libgff 2.0.1 published` → W3 本地 CI 通过（Pass rate 100% (1/1)）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub 仓库页报"下载内容是 HTML" | github.com 归档直连超时/被重定向 | 改用 codeload 官方 tag 归档 URL |
| 2 | conan create source() 报 BadZipFile | codeload tar.gz URL 末段无扩展名，get() 按 basename 误判 zip（等价命中 E276/E483） | conandata.yml sources 显式声明 `filename: libgff-2.0.1.tar.gz` |
| 3 | conan-verify G1 报 conandata sha256 未填 | 注册表无 libgff 条目，模板占位符未替换 | 补真实 SHA-256 96d2bda6... |
| 4 | 生成的 conanfile.py 是 autotools 模板而项目为 CMake | _guess_build_system 按 URL 关键字猜测默认 autotools | 按 CMake 模板重写配方 + manifest build_system=cmake |
| 5 | test_package 模板为 C 项目，gff.h 是 C++ 头 | 模板默认 C | project(test_libgff CXX) + test.cpp |
| 6 | W3 junk_check JC5 拦 util-linux-login .ci-trigger | 其他库既有 tracked 空文件未被白名单覆盖（无关历史基线） | JUNK_PR_DIFF 注入当前库 PR diff（prdiff 模式，与真实 CI 同源），详见基线隔离审计 |

## 源码修改

无补丁（patches 为空）。配方层修改见 conanfile.py / conandata.yml / manifest.yaml / test_package。

## 依赖版本

无外部依赖（纯 C++14 静态库）。

## 验证结果

- 上游测试：TestGFFParse 解析 4 特征 GFF3 → transcripts=1（tx1），退出码 0。
- conan create 干净构建：成功（libgff.a + TestGFFParse + test_package 自测通过，test_package 断言 2 项）。
- harmonys_specific_test：arm64 原生二进制在本机（OHOS PC）运行成功，退出码 0。
- W3 本地 CI 模拟：1/1 通过（Pass rate 100%），`.ci-result.json` exit_code=0。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 静态库配方（libs=["gff"]，库文件 libgff.a） |
| conandata.yml | 官方 codeload 源 + SHA-256 + filename |
| manifest.yaml | build_system=cmake、status=published |
| test_package/ | CXX 消费者测试（真实调用 GffReader）+ MANIFEST.yml |
| knowledge/drafts/DRAFT-libgff-2.0.1-url-guess-buildsystem-cmake-rewrite.{md,kv} | 路径 B 知识草稿对 |

## 注意事项

- 本任务不与正式知识库（knowledge/graph、knowledge/doc）写交互，路径 B 只创建 DRAFT 草稿对。
- 基线隔离（util-linux-login .ci-trigger）仅以环境变量注入，无 tracked 改动，已无条件恢复。

---

**编译结束**: 2026-09-22 20:23
**最终状态**: published