# describe.h 2.1.2 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile，无 configure）
- 编译日期: 2026-09-19
- 编译器: clang 15 (OHOS aarch64) / clang (本机 x86 验证)
- 状态: built

## 编译步骤

1. 下载官方源码 https://github.com/stephenmathieson/describe.h/archive/refs/tags/2.1.2.tar.gz（SHA-256: 1d2c2dc493fe991a465bbe49716d66729ba9b4c2020196e3405d6af24706f3dd）。
2. 上游 tarball 不内嵌 deps/（Makefile 依赖 deps/assertion-macros + deps/console-colors），按官方源补拉：
   - assertion-macros.h 0.3.1（SHA-256: 3271494d88e11d28d472d09f0283ebccfb7bb2552e01f309b05eb89871fc9257）
   - console-colors.c 1.0.1（SHA-256: 6cfd7bbe82bbed04565e1ece8eb5240634c8be50020bd814a906c92d52e4fabe）
3. conan 配方（makefile 型）：source() 补拉 deps → build() 编译 describe.c + console-colors.c 为静态库 libdescribe.a → package() 安装头文件与库。
4. 本机验证：clang -std=c99 编译 example.c（上游样例）与 describe_ohos_test.c（鸿蒙专项测试）均通过。
5. OHOS 验证：conan create（profile ohos-aarch64）通过，test_package 消费者测试真实运行通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create G2 编译 describe.c 报 assertion-macros.h 找不到 | source() 用 get(destination=) 下载 deps，但 destination 不剥离归档根目录（文件落在 deps/<dep>/<repo>-<ver>/） | 改为 get(strip_root=True) 解到 source 根再 copy 到 deps/<dep>/（见知识草稿 DRAFT-describe.h-2.1.2-conan-get-destination-strip-root） |
| 2 | W3 本地 CI conan create 报 NotADirectoryError（predl_cache 路径畸形） | conandata.yml 注释含裸 URL 被 pre-download 正则误提取并子串改写污染 | 注释禁写裸 https:// URL；清理 .build-cache/predl_cache 坏缓存；恢复官方 URL（既有知识 DRAFT-jwt-cpp 等已覆盖） |
| 3 | W3 JC5 拦截其他库基线文件 .ci-trigger | 新库零提交分支 W3/JC 走 full 模式整仓扫描，命中 origin/main 既有 .ci-trigger | 按基线隔离复验：记录 pre SHA-256 → git rm --cached + mv 隔离 → 复跑 W3 通过 → 原样恢复并核对 post SHA-256 一致（既有知识 DRAFT-dr_mp3 已覆盖） |
| 4 | W4 审计 P1：conandata.yml 残留 gh-proxy 前缀 | build_and_test.sh 镜像改写残留污染 worktree 内 conandata.yml | 恢复官方单值 URL（R39/PF7 合规） |
| 5 | W4 审计 P1：test() 软通过 | test_package test() 吞掉运行失败异常降级 warning | 移除软通过，仅 can_run=False 时跳过，其余真实执行 |

## 源码修改

无源码补丁（patches/ 为空）；库源码按官方原样编译。

## 依赖版本

- assertion-macros.h 0.3.1（官方源码，deps 补拉）
- console-colors.c 1.0.1（官方源码，deps 补拉）
- 无 Conan 外部 requires（零依赖库）

## 验证结果

```bash
# 上游样例（4 个独立用例：3 通过 + 1 个 assert(0==12) 上游故意失败演示）
make && ./example          # 3/4 = 75%（全量口径）
# 鸿蒙专项测试（describe_ohos_test.c → test_package/test.c）
./describe_ohos_test       # 4 用例 + 失败计数验证全部通过
# OHOS 交叉验证
conan create .../archives/d/describe.h/2.1.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64  # PASS
# W3 本地 CI
finish describe.h 2.1.2 built   # W3 PASS（Pass rate 100%）
```