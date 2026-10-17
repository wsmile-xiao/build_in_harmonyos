# farmhash 1.1.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-10
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. `init-build farmhash 1.1.0 --url=https://github.com/google/farmhash/archive/34c13ddfab0e35422f4c3979f360635a8c050260.tar.gz`（官方 v1.1 提交，sha256 核验通过）
2. `./configure --prefix=$DEFAULT_PREFIX`（需先对 config.guess/config.sub 打 HarmonyOS 补丁，见下）
3. `make -j1`：构建 libfarmhash.so/.a + farmhash_unittest
4. `make -j1 check`：上游自测 1/1 PASS
5. `-std=c++17 -stdlib=libc++` 编译复验（对齐 conan 工具链）+ make check 1/1 PASS
6. `conan init/verify`：G0-G4 + L2/L4/L5 全过
7. `finish farmhash 1.1.0`：W2 结构 + W3 本地 CI 通过，产物状态 built（未 upload）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | 2015 版 config.guess/sub 无 HarmonyOS 分支 | 0001/0002：config.guess 增 `*:HarmonyOS:*:*` 分支 echo 三元组；config.sub 增 linux-ohos 三处识别 |
| 2 | reference to 'data' is ambiguous (20 errors) | C++17 起 std::data 与自测区全局数组 `data`（`using namespace std;`）冲突 | 0003：自测区 9 处 `static char data[]` 及引用改名 `farmhash_data`（100 token，注释保留） |
| 3 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS 对 umask 077 + mktemp 临时目录的 UID 映射限制（E011/E052/E060） | 本地环境 mktemp shim（mkdir 实现）前置 PATH；CI 干净环境无此问题 |

## 源码修改

- `patches/0001-config.guess.patch`：增加 HarmonyOS 系统识别
- `patches/0002-config.sub.patch`：增加 linux-ohos 规范目标
- `patches/0003-src-farmhash.cc.patch`：自测缓冲区 data → farmhash_data（C++17 兼容）

## 依赖版本

无外部依赖（farmhash 为纯 C++ 头文件+库，不需 requires）。

## 验证结果

```bash
./configure --prefix=$DEFAULT_PREFIX   # exit 0
make -j1 && make -j1 check             # exit 0, farmhash_unittest 1/1 PASS
conan-verify farmhash 1.1.0            # G0-G4 + L2/L4/L5 PASS
finish farmhash 1.1.0 published        # W2/W3 通过, exit 0
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | Conan 配方（static 库，R26） |
| test_package/test.cpp | 消费者测试：6 个已知向量断言（C++ 编译） |
| patches/0001-0003 | HarmonyOS 三元组 + C++17 歧义修复 |
| reports/test-report.md | 上游测试 1/1 + test_package 证据 |

## 注意事项

- HMDFS 本地验证时 config.status 临时目录不可写属环境特性（E011），CI 干净环境不受影响。
- Release（NDEBUG）构建下 farmhash DebugTweak 关闭，Hash32/Hash64 与 Fingerprint 一致；test_package 向量按 conan Release 构建实测。
- 上游无 git tag，v1.1.0 对应官方提交 34c13ddfab0e35422f4c3979f360635a8c050260（NEWS v1.1, 2015-03-01）。

**编译结束**: 2026-09-10 21:24
**最终状态**: built
