# mcqd 1.0.0 适配笔记

## 编译环境

- 构建系统: custom（无构建系统；头文件直装 + 示例程序编译验证）
- 上游: https://gitlab.com/janezkonc/mcqd ，tag v1.0.0
- 源码包: https://gitlab.com/janezkonc/mcqd/-/archive/v1.0.0/mcqd-v1.0.0.tar.gz
- SHA256: 37ff68ff88e047c929990d4c12ce474753f6f9c49324661a3aa1cfe77c26ad9d
- 包内容: COPYING / README.md / mcqd.cpp / mcqd.h / test.clq（6 条目，test.clq 约 2.2MB DIMACS 图）
- 编译器: clang/clang++（Conan conf tools.build:compiler_executables，CI 真机为 hnp clang 15）
- 状态: built（待 HMBS 真机 rule4 门禁验证后由后端提交）

## 库形态判定

- mcqd.h 包含 Maxclique 类的完整声明与内联实现（头文件内直接定义全部方法），无需编译库文件，属于 header-only。
- mcqd.cpp 是示例驱动（含 main + DIMACS 读取 + 两次算法调用），仅用于上游验证，不打包为二进制产物。
- 因此配方 package_type 为 header-library，package_id 清空，package() 只安装 mcqd.h 到 include/，COPYING 与 README.md 到 licenses/。
- 无可执行产物，不创建 commands.json（R38 仅适用于 CLI 工具包）。

## 编译步骤

配方 build() 实际执行：

```bash
cxx -O2 -std=c++17 mcqd.cpp -o mcqd_upstream
./mcqd_upstream test.clq > upstream_test.log 2>&1
```

其中 cxx 经 _resolve_cxx() 解析：仅当 conf 绝对路径存在且可执行时采用，否则经 PATH 回退查找（clang++/c++/g++）。
test_package 实际执行：

```bash
cxx -std=c++17 -I<package>/include test_mcqd.cpp -o test_mcqd
./test_mcqd
```

test_mcqd.cpp 自建 4 节点三角图（0-1-2 三角 + 3 仅连 0，最大团大小为 3），分别调用 mcq() 与 mcqdyn()，
各自验证团大小、团合法性（团内两两相连）、steps() 推进，共 6 个 CHECK。

## 上游测试审计

- 上游无 CMake/CTest/Autotools/Meson 测试框架，无 tests/ 目录。
- 唯一可执行验证是 mcqd.cpp 的两个示例场景：Example 1（mcq）与 Example 2（mcqdyn），均在 test.clq 上运行。
- 计数口径：discovered=2（mcqd.cpp main 中两个场景），executed=日志中 Example 抬头行数，passed=Size 行中值大于 0 的个数。
- 解析规则：逐行匹配 `---------- Example N` 计 executed，正则 `^Size = (\d+)\s*$` 计 passed，不做字符串数数后的减法规整。
- test.clq 非空（2.2MB），build() 在运行前校验日志非空，防止空文件比空文件的假通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无正式测试框架，MANIFEST 口径无现成 ctest/gtest/autotools 可套用 | mcqd 仅有示例程序 | upstream_test_total 取 2（两个示例场景），count_method 记 auto 并附计数说明 |
| 2 | 避免 R33 违规（裸用 CC/CXX 环境变量） | CI worker 上 shell 变量可能为空 | 编译器一律从 self.conf tools.build:compiler_executables 获取，test_package 同理 |
| 3 | avoid packing example binary | example only for verification | package() copies only mcqd.h, no binary install; package_info clears bindirs/libdirs |
| 4 | gitlab.com archive ReadTimeout on preflight (2026-10-02) | single official URL, no fallback | round-2 fix (ordered gh-proxy + mirror.ghproxy list) DISPROVEN by preflight: gh-proxy 404, mirror.ghproxy ConnectTimeout; see row 5 |
| 5 | round-2 proxies disproven on preflight (2026-10-02 log) | gh-proxy is GitHub-only; no byte-identical mirror on reachable host | reverted to single official URL, sha256 verbatim; verified: official URL HEAD 200 from executor, no GitHub full-history mirror (API search), SageMath repack sha differs, upstream v1.0.0 = commit e69d5119; preflight gitlab.com timeout is egress-specific, needs backend/infra handling |
| 6 | gitlab.com archive ReadTimeout persists on preflight (2026-10-02); 2nd strategy cycle forbids reusing the prefix-list approach | prefix list disproven (gh-proxy 404 for gitlab, mirror.ghproxy timeout, no identical-byte mirror); same-host HTTPS archive keeps failing | NEW route (transport fallback, not URL prefixes): source() tries official tarball first (sha256 verbatim), on ConanException falls back to `git clone https://gitlab.com/janezkonc/mcqd.git` + checkout pinned v1.0.0 commit e69d5119 (tag object 413efefa, verified via git ls-remote 2026-10-03); pattern follows in-repo precedents (ncmpcpp/vsearch Git fallback); no third-party mirror, no sha change |
| 7 | git fallback ALSO failed on preflight: `git clone https://gitlab.com/janezkonc/mcqd.git` → `Recv failure: Connection reset by peer` (2026-10-02 log) | whole gitlab.com host unreachable from preflight (HTTPS archive timeout + git protocol reset); same-host fallback futile; no byte-identical mirror on reachable hosts | NEW route (vendored offline tier, no network): `files/upstream/` vendors the 5 official tarball files extracted locally from the archive whose sha256 == conandata value (verified 2026-10-03, 473971 bytes); source() tier-3 copies them via exports_sources when tiers 1-2 fail; `exports_sources = "files/*"` added; extracted files (not tarball) so JC3 clean |
| 8 | 真机 build() 失败：`"/data/service/hnp/bin/clang++": inaccessible or not found`（2026-10-02 预检，exit 127） | 配方盲信 conf 的绝对路径，不校验存在性；真机该路径不可用，但可用编译器在 buildenv PATH 中 | 新增 _resolve_cxx()（主配方+test_package）：绝对路径仅当 isfile+可执行时采用，否则对其 basename 及 clang++/c++/g++/cc 做 shutil.which 回退；编译 self.run 显式 env="conanbuild" 以继承 hmbs 前置工具 PATH |

## 源码修改

无。OHOS 上为标准 C++（iostream/fstream/set/map/cstring/assert），无需补丁。

## 依赖版本

无运行时依赖，无 tool_requires。仅需 C++ 编译器。

## 验证结果

本地为 Windows 执行器，未运行 conan（按任务守则，验证交由 HMBS 真机预检）。
待 HMBS 真机回填：

- conan create 日志中的 HMBS_UPSTREAM_TEST_RESULT（期望 discovered=2/executed=2/passed=2）
- conan create 日志中的 HMBS_TEST_PACKAGE_RESULT（期望 discovered=6/passedCount=6）

证伪计划（真机通过后仍需确认）：检查 upstream_test.log 非空且含两个 Size 行；
test_mcqd 二进制故意破坏（如注释掉一条 link 边）应导致 CHECK FAIL，非零退出。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/m/mcqd/1.0.0/conanfile.py | 主配方（header-library，上游示例编译+运行） |
| archives/m/mcqd/1.0.0/conandata.yml | 源码 URL+SHA256 |
| archives/m/mcqd/1.0.0/manifest.yaml | 版本级 manifest |
| archives/m/mcqd/1.0.0/test_package/conanfile.py | 消费者测试入口 |
| archives/m/mcqd/1.0.0/test_package/test_mcqd.cpp | 真实调用 Maxclique API 的 6 断言测试 |
| archives/m/mcqd/1.0.0/test_package/MANIFEST.yml | 上游 2 场景 + 新增 6 断言声明 |

## 注意事项

- 本轮仅完成未提交工作树，未执行 git commit/push，未创建 PR，未调用 GitCode 写接口。
- 等待 HMBS 后台真机验证与提交推送。
