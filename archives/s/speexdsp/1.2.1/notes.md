# speexdsp 1.2.1 — 适配笔记

> 档案创建时间: 2026-07-15
> 最后更新: 2026-07-15

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | speexdsp |
| 版本 | 1.2.1 |
| 状态 | built |
| 构建系统 | autotools |
| 源码路径 | https://downloads.xiph.org/releases/speex/speexdsp-1.2.1.tar.gz |

## 二、编译阶段

### Phase 1: 环境准备
- [x] ohc-run.py init-build 完成 / 源码下载解压
- [x] 补丁应用 (config.guess, config.sub, config.h.in)

### Phase 2: 编译（configure + make + make install）
- [x] configure 完成（需要 replace_in_file 修复 mktemp 问题）
- [x] make 编译完成
- [x] make install 完成

### Phase 2.5: 独立目录安装验证
- [x] 干净源码 + 补丁应用
- [x] 独立 TEST_PREFIX configure + make install
- [x] 功能回归测试结果

### Phase 3: 测试验证
- [x] make check 结果: PASS
- [x] conan-verify G2 (conan create + test_package): PASS

### Phase 5: 归档收尾
- [x] 补丁生成（ohc-run.py refresh-patch --auto）
- [x] manifest.yaml / README.md 更新
- [x] conan-verify 质量门禁: PASS

## 三、关键发现

### config.status tmpdir 问题 (E002)
configure 生成的 config.status 使用 `mktemp -d "./confXXXXXX"` 在 OHOS 上失败。
解决方案: conanfile.py build() 中使用 `replace_in_file` 修复 configure 脚本，
将 mktemp 模式替换为 `${TMPDIR:-/tmp}/conan-cs-$$`。

### 补丁策略
- 0001-config.h.in.patch: 修改 config.h.in 模板
- 0003-config.guess.patch: 添加 HarmonyOS/OHOS 平台检测
- 0004-config.sub.patch: 添加 HarmonyOS/OHOS 平台支持
- 其他补丁（Makefile.manual, test files, config_types.h）为构建产物或 configure 生成的文件，不需要声明

## 四、最终状态
- **最终状态**: built
- **结束时间**: 2026-07-15
