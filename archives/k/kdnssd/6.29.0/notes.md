# kdnssd 6.29.0 适配笔记

## 编译环境
- 构建系统: cmake (ECM/KDE Frameworks 6)
- 编译日期: 2026-08-29 (r03: Qt6LinguistTools 消费核验轮)
- 编译器: clang/clang++ 15 (ohos-aarch64 profile, os=OHOS)
- 状态: built

## 编译步骤

r03 本轮（r02 外部首错 Qt6LinguistTools 缺失已由分析端发布 qt6linguisttools/6.11.1 解决）：

1. conan create（-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同 profile）全绿：
   - CMake configure 通过（含 ECMPoQmTools 的 find_package(Qt6 LinguistTools)）
   - libKF6DNSSD.so 构建成功
   - 上游 ctest 零入口证据（kdnssd 上游无 autotests 套件）rc=0
   - test_package：ctest 2/2 通过（test_kdnssd + 新增 test_kdnssd_ohos），直接运行 ./test_kdnssd OK
2. conan-verify 全部门禁 PASS（G1/G0/G2/G3/G4, L2/L4/L5）
3. finish 至 Step 5/10（W3 本地 CI 模拟）：setup.sh 通过；build_and_test.sh 的 L0/KC 全过，仅 JC3
   杂物门禁被 main 上其他库 goaccess/1.10.2/ncurses-headers.tar.gz（已跟踪 tarball）阻塞——
   无关历史基线，超出本任务允许改动范围，按 SKILL 隔离规则记录，不修改 goaccess。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ECMPoQmTools 报 Qt6LinguistTools 缺失 | qtbase/6.11.1 不含 LinguistTools；r02 时 ohpcd 未发布独立包 | 分析端已发布 qt6linguisttools/6.11.1；配方 build_requirements 增加 tool_requires("qt6linguisttools/6.11.1") |
| 2 | find_package(Qt6 COMPONENTS LinguistTools) 仍失败 | Qt6Config 组件解析锚定 Qt6_DIR（qtbase 内）相对路径 | generate() 显式设置 tc.variables["Qt6LinguistTools_DIR"] 指向 qt6linguisttools 包 lib/cmake/Qt6LinguistTools |
| 3 | 上游 ctest "--no-tests=error" 因无测试失败 | kdnssd 上游无 autotests 套件 | 去掉 --no-tests=error，以零入口证据 rc=0 通过并写入 MANIFEST |
| 4 | W3 JC3 杂物门禁失败 | main 上 goaccess/1.10.2/ncurses-headers.tar.gz 已跟踪 tarball（外部历史基线） | 按 SKILL 隔离/恢复规则记录外部首错，不修改 goaccess，回报 external_blocked |

## 源码修改

- patches/0001-lower-ecm-version.patch：ECM 6.29.0 需求降为 6.26.0（registry 已发布版本，attica 6.28.0 先例）
- conanfile.py：接入 qt6linguisttools/6.11.1 tool_require + Qt6LinguistTools_DIR

## 依赖版本（r03 实测消费）

| 依赖 | 版本 | registry 状态 |
|------|------|---------------|
| qtbase | 6.11.1 | ohpcd 已发布 #714d84d0，可消费 |
| ecm (tool) | 6.26.0 | ohpcd 已发布 #0768b8c9，可消费（>= 6.0.0） |
| qt6linguisttools (tool) | 6.11.1 | ohpcd 已发布 #021a6867，提供 Qt6LinguistToolsConfig + lrelease/lupdate/lconvert/lcheck/ltext2id |
| qttools（qt6linguisttools 传递）| 6.11.1.1 | ohpcd 已发布，可消费 |
| qtdeclarative（传递）| 6.11.Z | ohpcd 已发布 6.11.1 #5e71bc8b，可消费 |

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64  # exit 0，test_package 2/2 Passed
ohc-run.py conan-verify kdnssd 6.29.0                  # G1/G0/G2/G3/G4 PASS，可标记 published
ohc-run.py finish kdnssd 6.29.0 built                  # W3 JC3 被 goaccess tarball 外部阻塞
ctest --test-dir test_package/build/...                # 2/2 passed: test_kdnssd, test_kdnssd_ohos
./test_kdnssd                                         # isAvailable()=2(Unsupported), OK
./test_kdnssd_ohos（新）                                # OHOS dummy backend 行为断言 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake/ECM 配方（qtbase + ecm + qt6linguisttools tool_require，Qt6LinguistTools_DIR 显式注入）|
| conandata.yml | 官方 KDE 源 URL + SHA-256（已核验）|
| patches/0001-lower-ecm-version.patch | ECM 版本降低补丁 |
| test_package/ | conanfile.py + CMakeLists.txt + test_kdnssd.cpp + test_kdnssd_ohos.cpp + MANIFEST.yml + test.c |
| manifest.yaml / notes.md | 编译元数据/笔记 |

## 注意事项

- 上游无 autotests/ 目录，无 ctest 目标；逐入口台账结论：不可运行（上游无测试套件），
  零入口证据记录于回报；有效测试保留在 test_package（2 个，均真实调用 KDNSSD API）。
- OHOS dummy backend（无 Avahi/DNSSD）：isAvailable()==Unsupported；新测试 test_kdnssd_ohos
  显式断言该平台适配路径行为（R40 深度适配完整性）。
- remote_authorization=none：未 commit/push/PR/上传制品；状态维持 built。
- W3 JC3 外部阻塞须由分析端处理 goaccess tarball 后方可继续（下一步）。
---
**编译结束**: 2026-08-29（r03）
**最终状态**: built（本地验证通过；W3 仅被外部历史基线 goaccess tarball 阻塞）
---

**编译结束**: 2026-08-29 17:00
**最终状态**: built
