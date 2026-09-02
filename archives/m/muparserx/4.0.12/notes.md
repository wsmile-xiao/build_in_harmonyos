# muparserx 4.0.12 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang/clang++ 15.0.4 (HarmonyOS PC / OHOS aarch64 profile)
- 状态: built（验证通过，制品尚未发布，PR 合入后由 CI upload）

## 编译步骤

```bash
# 1. init-build（GitHub 不可达，经 ghfast.top 镜像下载官方 v4.0.12 tarball）
python3 scripts/ohc-run.py init-build muparserx 4.0.12 --url=https://github.com/beltoforion/muparserx

# 2. 探索性编译（本机 OHOS 环境）
cd $BUILD_SRC_DIR && mkdir build-native && cd build-native
cmake .. -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_SHARED_LIBS=OFF -DBUILD_EXAMPLES=ON -DCMAKE_BUILD_TYPE=Release
make -j2
./example < /dev/null   # 上游自测: 16 项 testing 全部 passed (614 expressions)

# 3. Conan 配方验证（G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify muparserx 4.0.12

# 4. finish（含 W2 结构 + R36 依赖 + W3 conan create）
python3 scripts/ohc-run.py finish muparserx 4.0.12 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 执行机无法直连 github.com | 经 ghfast.top 镜像下载官方 tarball，sha256 校验一致（941c79f9...） |
| 2 | `cmake_minimum_required(2.8.12)` 被 CMake 4.1.2 拒绝 | 上游 CMakeLists 版本过老 | conanfile generate() 与 configure() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | test_package 找不到 `mpParser.h` | 上游 install 到头文件到 `include/muparserx/` | package_info includedirs 改为 `include/muparserx` |
| 4 | test_package `Eval()` 无法转 double | Eval() 返回 `const IValue&` | 使用 `.GetFloat()` 取值 |
| 5 | conan-verify 写 ghfast-bak 报 ENOSPC | /storage/Users tmpfs inode 耗尽 | `conan cache clean -s -b -d` 释放 inode 后恢复 |
| 6 | example 交互 REPL 不自退 | 上游 sample 是交互程序 | 以 `< /dev/null` 运行，自测段完整输出到日志后按超时截断，自测 16 项全部 passed 已有记录 |

## 源码修改

无（无补丁，conandata.yml patches 为空；仅配方层适配）。

## 依赖版本

无外部 Conan 依赖（纯 C++17，仅链接系统 libm）。

## 验证结果

- 上游自测: 16/16 passed（614 expressions），日志 SHA256 2333f4717a5739163000e4426fb41da0a06941d710b65f07bcf58e5ab56ad3dc
- conan-verify: G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS
- test_package: 消费者链接 + 表达式求值 `1+2*3-4 = 3` 通过

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（静态库，CMAKE_POLICY_VERSION_MINIMUM=3.5） |
| conandata.yml | 官方 GitHub 源码 + sha256 |
| test_package/ | 消费者链接与 API 求值测试 |
| reports/conan-verify-report.md | 门禁报告 |

## 注意事项

- GitHub 直连不可用，CI 侧已有 E017 ghfast.top 镜像注入兜底。
- muparserx 命名空间为 `mup`（非 `mu`）。
---

**编译结束**: 2026-09-02 13:54
**最终状态**: built（待 PR 合入后由 CI upload）
