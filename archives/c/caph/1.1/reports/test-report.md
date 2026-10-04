# Test Report — caph 1.1 (鸿蒙适配)

## 上游测试清点

| 项目 | 值 |
|------|-----|
| 软件名 | caph |
| 上游版本 | 1.1 |
| 上游仓库 | http://caphgame.sourceforge.net/ |
| 构建系统 | 自定义 Makefile (mkgen + confg) |
| 依赖 | SDL 1.2, libpng, OpenGL(已移除), libm |
| 上游测试框架 | **无** |
| 上游自动化测试数 | **0** |
| 测试入口 | 无 (GUI 应用，需交互显示) |

### 清点过程

1. 源码目录结构: `src/` (4个 .c 文件), `include/` (4个 .h), `share/caph/` (数据文件), `doc/caph/` (文档)
2. 无 `tests/`, `test/`, `testing/` 目录
3. 无 `configure.ac`/`Makefile.am` 中的 `check` 目标
4. 无 `ctest`, `pytest` 注册
5. `make check` 不存在
6. 二进制是 GUI 应用 (`main()` 进入 SDL 事件循环)，无内置自测模式

**结论: 上游无自动化测试。**

## 适配后测试用例统计

| 测试类型 | 用例数 | 说明 |
|---------|--------|------|
| 上游测试 | 0 | 上游无自动化测试 |
| 消费者测试 (test_package) | 1 | 验证二进制完整性 + 数据文件 + 链接契约 + 10s 运行时烟雾 |
| 鸿蒙特有测试 | 1 | SDL dummy 驱动下 10s 无崩溃 (消费者用例) |

## 测试命令

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 验证结果

| 阶段 | 状态 | 备注 |
|------|------|------|
| conan create 编译 | ✅ PASS | 移除 OpenGL，SDL 软件渲染 |
| conan create test_package | ✅ PASS | 二进制+数据完整性 + 链接契约 + 10s dummy 驱动 |
| W3 本地 CI (L0a-L0e) | ✅ PASS | 配方/结构/命令完整 |
| finish 归档 | ⚠️ 部分 | finalize-archive 框架 bug ('str' object has no attribute 'append') |

## 适配修改说明

1. **移除 OpenGL 依赖**: OHOS sandbox 无 GPU 上下文，`-D_OPENGL` 和 `-lGL` 会导致链接失败
   - 修改: `src/confg` 中注释掉 `-D_OPENGL` 和 pkg-config gl 检测
2. **修复 shebang**: `/bin/bash` 在 OHOS 不存在，改为 `#!/system/bin/sh`
3. **修复 SYS_DATA_DIR**: 从 `../share/caph/` 改为 `../res/caph/` (匹配 conan 包布局)
4. **使用 deps_cpp_info 获取编译标志**: 不依赖 pkg-config (worker 环境 PATH 不完整)

## 消费者测试详情

### 测试文件: test_package/conanfile.py

**Phase 1 — 二进制 + 数据完整性:**
- caph 二进制存在且可执行
- caph.conf 存在
- 3 个 PNG 资源文件存在 (icon.png, paper.png, brush.png)
- maps/maps.list 存在且列出的全部 25 个 .map 文件存在

**Phase 2 — 链接契约:**
- readelf -d 显示 NEEDED 包含 libSDL-1.2.so.0
- readelf -d 显示 NEEDED 包含 libpng16.so.16

**Phase 3 — 运行时烟雾:**
- 在 SDL_VIDEODRIVER=dummy + SDL_AUDIODRIVER=dummy 环境下启动 caph
- 通过 `self.run()` 调用二进制 (满足 R34 实质性测试要求)
- 10 秒后仍在运行 (通过 dummy 驱动的事件循环)
