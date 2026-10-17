# utf8proc 2.11.3.1 — 编译进度

> 档案创建时间: 2026-08-28
> 最后更新: 2026-08-28
> 构建系统: CMake

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | utf8proc |
| 版本 | 2.11.3.1（上游 2.11.3 + 适配迭代后缀 .1） |
| 状态 | ✅ built |
| 构建系统 | CMake |
| 源码路径 | https://github.com/JuliaStrings/utf8proc/releases/download/v2.11.3/utf8proc-2.11.3.tar.gz |
| 依赖 | 无（纯 C 单文件库） |

## 二、编译阶段

### Phase 1: 环境准备
- [x] init-build 完成 / 源码下载解压

### Phase 2: 编译（cmake configure + build）
- [x] cmake configure 完成（clang 15.0.4，OHOS aarch64）
- [x] make 编译完成（无错误）
- [x] make install 完成（staging 到 TEST_PREFIX）

### Phase 2.5: 上游测试
- [x] ctest 上游 10 个测试全部通过（case/custom/iterate/misc/printproperty/valid/maxdecomposition/charwidth/graphemetest/normtest）
- [x] 测试数据由 CMake configure 从 unicode.org 下载（NormalizationTest.txt / GraphemeBreakTest.txt）
- [x] build() 中已集成 `ctest --output-on-failure`（LD_LIBRARY_PATH 指向构建目录）

### Phase 3: Conan 配方
- [x] conan-init 生成配方（CMake 模板）
- [x] conan-verify 通过（G0-G4 + L2/L4/L5）
- [x] test_package/test.c 实质调用 API（version/NFC/iterate/grapheme_break/property，10 断言）
- [x] W3 本地 CI 模拟通过（setup.sh + build_and_test.sh）

## 三、版本说明（2.11.3.1 vs 2.11.3）

制品仓已存在 utf8proc/2.11.3（2026-08-26 发布），本 PR 为同一上游版本的适配迭代：
- 版本号递增为 2.11.3.1（R37）
- 配方改进：build() 集成上游 ctest 测试（原 2.11.3 未集成）
- 保留 OHOS lld 链接器 LD_LIBRARY_PATH 适配（libxml2.so.16）
- 源码与 sha256 不变（官方 GitHub release tarball）

## 关闭

状态：built（2026-08-28），W3 本地 CI 模拟通过，W4 审计通过，已提交 PR。

