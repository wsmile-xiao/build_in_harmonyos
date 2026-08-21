# xz 5.8.3 — 编译进度

> 档案创建时间: 2026-07-27 11:10:00
> 最后更新: 2026-07-27 (当前状态)
> 构建系统: autotools (configure + make)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | xz |
| 版本 | 5.8.3 |
| 状态 | ✅ success |
| 构建系统 | autotools |
| 源码 URL | https://github.com/tukaani-project/xz/releases/download/v5.8.3/xz-5.8.3.tar.gz |
| SHA256 | 3d3a1b973af218114f4f889bbaa2f4c037deaae0c8e815eec381c3d546b974a0 |
| 许可证 | 0BSD |
| 安全 | 包含 CVE-2026-34743 修复 |

## 二、编译阶段

### Phase 1: 环境准备
- [x] init-build 完成（通过 gh-proxy.com 镜像下载源码，GitHub 直连超时）
- [x] SHA256 校验通过

### Phase 2: 编译（configure + make + make install）
- [x] configure 完成（--prefix=$DEFAULT_PREFIX --disable-scripts）
  - 应用 config.guess 补丁添加 HarmonyOS 检测
  - config.sub 5.8.3 已内置 OHOS 支持，无需补丁
  - mktemp wrapper 解决 OHOS 权限问题
- [x] make 编译完成（-j1，无错误）
- [x] make install 完成（DESTDIR 隔离安装验证通过）

### Phase 2.5: 独立目录安装验证
- [x] 干净源码 + 补丁应用
- [x] 独立 TEST_PREFIX configure + make install
- [x] 产物验证: bin/xz, bin/xzdec, bin/lzmadec, bin/lzmainfo, lib/liblzma.{a,so}, include/lzma.h

### Phase 3: 测试验证
- [x] make check 结果: 18/18 PASS (with --disable-scripts)
  - 无 --disable-scripts: 18/19 PASS (test_scripts.sh FAIL: "Bad file descriptor")
  - 有 --disable-scripts: 18/18 PASS (test_scripts.sh 被跳过)
- [x] 安全弹窗: 无需触发（已有 bash 环境）

### Phase 4: Conan 配方
- [x] conan-init 生成基础配方
- [x] 手动定制 conanfile.py（基于 5.6.2 经验）
- [x] conandata.yml 更新 SHA256 和补丁声明
- [x] test_package/ 包含实质性测试代码（LZMA API 调用）
- [x] MANIFEST.yml 填写上游测试声明
- [x] commands.json 创建（R38，命令行工具声明）

## 三、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| build-aux/config.guess | HarmonyOS/OHOS 平台检测 | 添加 case 分支 | ✅ 0001-build-aux-config.guess.patch |

## 四、与 5.6.2 的差异
| 项目 | 5.6.2 | 5.8.3 |
|------|-------|-------|
| 补丁数 | 12 | 1 |
| config.guess 补丁 | 需要 | 需要 |
| config.sub 补丁 | 需要 | 不需要（已内置） |
| po/Makefile.in 补丁 | 需要（文件缺失） | 不需要（模板已存在） |
| po/POTFILES 补丁 | 需要（文件缺失） | 不需要（模板已存在） |
| 脚本补丁 (8个) | 需要 | 不需要（--disable-scripts） |
| --disable-scripts | 是 | 是 |
| mktemp wrapper | 是 | 是 |
| -static ldflags | 是 | 是 |

## 五、结束记录
- **最终状态**: ✅ 编译成功
- **结束时间**: 2026-07-27
- **测试**: 18/18 PASS
- **补丁**: 1 个（config.guess）
---

**编译结束**: 2026-07-27 11:33
**最终状态**: built

## 六、CI 验证记录

### 本地 CI 模拟构建 (2026-07-31)
完整运行 `ci/conan/build_and_test.sh`，所有门禁通过：

| 门禁 | 结果 | 详情 |
|------|------|------|
| L0 | ✅ pass | 结构完整性 + MANIFEST + 补丁格式全部通过 |
| L1 | ✅ pass | 上游 make check 18/18 + test_package 执行 |
| L1e | ✅ pass | 破坏性反向验证：测试确实依赖 xz 包 |
| L2 | ✅ pass | 9个二进制 (xz/xzdec/lzmadec/lzmainfo/lzcat/lzma/unlzma/unxz/xzcat) --version 全部通过 |
| L4 | ⚠️ warn | config.guess 补丁中 "targets" 误匹配 gets\b（非阻塞） |
| L5 | ✅ pass | bin/ 产物完整 |

### CI 远端失败分析
- **失败步骤**: conan-build-test (elapsed 0.11s)
- **错误**: `Path in CI_PACKAGES has no conanfile.py: archives/x/xz/5.8.3`
- **根因**: CI worker git checkout 异常 — conanfile.py 在 git tree 中存在（`git ls-tree` + `git cat-file` 验证），但 CI worker 构建目录中未检出
- **本地验证**: conan create + 完整 CI 脚本均通过，配方无问题
