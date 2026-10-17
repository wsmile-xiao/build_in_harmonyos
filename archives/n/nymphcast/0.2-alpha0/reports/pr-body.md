## PR 信息
- **三方库名称**：nymphcast
- **上游版本**：v0.2-alpha0
- **上游仓库地址**：https://github.com/MayaPosch/NymphCast
- **适配路径**：路径 A（基础适配）
- **使用知识库**：贡献 4 个知识草稿（knowledge/drafts/DRAFT-ohos-pthread-cancel-decl、DRAFT-ohos-elf-skip-strip-codesign、DRAFT-ohos-conan-copy-fnmatch-anchored、DRAFT-ohos-conan-make-executable-conf）

---

## 测试用例对比
### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 5 | 来源：src/test/Makefile（test_databuffer、test_databuffer_mm、test_screensaver、test_databuffer_mport、test_ffplay_local_file） |
| 集成测试 | 2 | 来源：src/test/test_file_seeking.sh、src/test/test_file_transfer.sh（依赖 test_server） |
| 其他测试 | 0 | 无 |
| **合计** | **7** | |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 5 | 不变 | 5 项上游单测全部接入 build() 实测：test_screensaver exit 0（仅 abort 路径）、test_ffplay_local_file exit 124（上游 teardown 挂起缺陷）、test_databuffer/test_databuffer_mport 上游编译缺陷无法构建、test_databuffer_mm exit 0 通过 |
| 集成测试 | 2 | 不变 | 2 项集成脚本实测执行：均因上游 test_server build-blocked（stale nymphrpc API）exit 1；另 nymphcast_client 端到端 localhost 200KB 传输成功（正向数据点） |
| 鸿蒙特有测试 | 1 | 新增 | test_package/test.cpp 真实调用 nymphcast_server --version 并断言版本横幅（3 断言，conanrun env 运行） |
| **合计** | **8** | **+1** | |

---

## 上游测试用例修改说明

**是否存在对上游测试用例的修改？**
- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（逐条说明如下）

1. **patches/0008-src-test-test_ffplay_local_file-subtitle_disable.patch**（bugfix）
   - 修改文件：src/test/test_ffplay_local_file.cpp
   - 修改原因：上游类型不匹配缺陷——`int subtitle_disable` 重定义了 ffplay/types.h 中声明为 `bool` 的 extern 变量，导致测试无法编译（该缺陷在 v0.2-alpha0 和 master 均存在）
   - 修改内容：将变量声明改为 extern 引用，使测试可编译
2. **patches/0009-src-test-ohos-test-compat.patch**（portability）
   - 修改文件：新增 src/test/ohos_server_glue.cpp + src/test/ohos_ffplay_globals.cpp
   - 修改原因：测试构建兼容胶水——ffplay 测试链接闭包需要 NymphCastServer.cpp 提供的 server 侧符号与 ffplay 全局变量块
   - 修改内容：仅新增测试构建辅助文件，不修改上游测试逻辑本身

---

## 补全测试用例说明

**上游是否存在无测试用例，适配后补全的情况？**
- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，补全（说明如下）

补全的测试范围：鸿蒙平台包级验证——上游测试全部针对源码树内部模块，无任何"安装后包可用性"测试。补全原因：conan 包消费方需要验证打包产物可执行。新增测试文件清单：test_package/test.cpp（调用打包的 nymphcast_server --version，断言 exit 0 + 版本横幅输出）。

---

## 验证结果
- 编译状态：通过
- 上游测试用例通过率：1/7（14.3%）
- 新增测试用例通过率：1/1（100%）

---

## 补充说明

### 上游测试执行缺口逐条说明（非 100% 通过率豁免）

上游 7 项测试中仅 1 项完整通过，其余 6 项失败/未执行全部归因于上游源码缺陷或上游测试环境依赖，非 OHOS 适配问题，逐条豁免如下：

| # | 测试项 | 实测结果 | 失败原因（上游缺陷证据） |
|---|--------|---------|------------------------|
| 1 | test_databuffer_mm | ✅ exit 0 通过 | —（完整通过） |
| 2 | test_databuffer | ❌ 编译失败 | 上游缺陷：test_databuffer.cpp:32 调用 `DataBuffer::setDataRequestCondition()`，该方法在 v0.2-alpha0 与 master 的 databuffer.h 中均不存在（GitHub raw HTTP 200 双版本核验），上游测试与头文件 API 长期不匹配 |
| 3 | test_databuffer_mport | ❌ 编译失败 | 上游缺陷：NymphLogger 未声明（nymph_logger.h 不在 v0.2-alpha0 源码树）+ setDataRequestCondition 不存在 + 官方 Makefile test_db_mp target 缺 -I../server |
| 4 | test_screensaver | ⚠️ exit 0（仅 abort 路径） | 上游测试从不调用 setDataPath，无壁纸时只走 "Found 0 wallpapers. Abort" 路径即退出，不执行真渲染；OHOS 无头环境（SDL dummy 驱动）无显示环境，不视为全功能通过 |
| 5 | test_ffplay_local_file | ❌ exit 124（超时） | 上游缺陷：完整播放流程后 teardown 挂起——event loop quit push 被上游注释（源码注释证据），挂起时 33 线程全部阻塞 FUTEX；SDL dummy/offscreen 双驱动均复现（驱动无关），排除 SDL 适配缺陷 |
| 6 | test_file_seeking.sh | ❌ exit 1 | 上游缺陷：依赖的 test_server build-blocked（stale pre-2021 nymphrpc API：NymphString/NymphBoolean 等旧值类型已被官方 2021-10-10 commit 1f0a64982c 移除，上游 NymphCastServer.cpp 已迁移新 API，独留 test_server 未更新），`./bin/test_server: inaccessible or not found` |
| 7 | test_file_transfer.sh | ❌ exit 1 | 同上：test_server build-blocked，`Connecting to remote server failed: 127.0.0.1:4004` |

**正向数据点**：nymphcast_client 编译+链接成功（4.4MB），localhost server+client 200KB blocks 端到端传输实测成功，验证 nymphcast 核心投屏传输链路在 OHOS 上可用。

**恢复条件**：上游修复 setDataRequestCondition（databuffer.h）、test_db_mp 补 NymphLogger/-I../server、test_server 恢复构建、提供图形/显示环境后，可重新完整运行上游测试。

### 适配技术要点

- 构建系统：上游仅 GNU Make（无 CMakeLists.txt），配方用 `make -C src/server TOOLCHAIN=clang` 交叉编译
- 源码获取：GitHub tag tarball 哈希不稳定（gzip 时间戳），改用 gitcode 官方镜像固定到 v0.2-alpha0 tag 指向的不可变 commit（3f500599，内容寻址保证可复现）
- OHOS 适配 patch 共 9 个：pthread cancel 声明型兼容头（符号在设备 libc 存在仅缺声明）、OHOS stub headers、VolumeControl 无 ALSA 分支、Makefile 链接裁剪（去 -lstdc++fs/-latomic/-lGL/-lasound）、strip 跳过（strip 会破坏链接器生成的 .codesign 签名导致 EPERM）
- FFmpeg 固定 6.1.6：上游 ffplay fork 使用已废弃的 avfft.h API（FFmpeg 7+ 移除）
