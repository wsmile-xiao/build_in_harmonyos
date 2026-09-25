# zork/1.1.0 适配笔记

## 上游信息
- 项目：Zork I (Dungeon) 经典文字冒险游戏 C 移植版
- 上游：https://github.com/devshane/zork
- 版本：v1.1.0 (2026-06-30)
- 许可证：MIT

## 依赖分析
- **强制第三方依赖**：无（仅平台 libc）
- **不需要单独适配**：libc / make / cc
- **下一步唯一待处理依赖**：无
- **评估**：依赖少且测试清晰的标准任务

## 适配要点

### 1. 构建期 Makefile 修改（conanfile.py build()）
- 修改 Makefile 的 `DATADIR = /usr/games/lib` → `DATADIR = <package_folder>/share/zork`
- dinit.o 规则使用 `-DTEXTFILE="$(DATADIR)/dtextc.dat"`，设置 DATADIR 后自动变成正确的 C 字符串字面量
- 使用 `-DMORE_NONE` 避免链接 `-ltermcap`（OHOS 不提供）

### 2. conanfile.py 构建逻辑
- `build()` 内 patch Makefile 的 DATADIR 变量
- 写入 `build_ohos.sh` 包装脚本，设置 `CC` / `LIBS=` / `TERMFLAG=-DMORE_NONE`
- `package()` 复制 `zork` 二进制、`dtextc.dat`、`dungeon.6`
- 不使用补丁文件，所有修改在 build() 内完成

### 3. test_package 修复（关键）
- **问题**：`self.run("... zork", env="conanrun")` 找不到 zork（application 包不导出 PATH）
- **修复**：使用 `self.dependencies["zork"].package_folder` 拼完整二进制路径 + `subprocess.run` 直接执行
- **测试断言**：4 项（Welcome to Dungeon / white house / mailbox / game is over）

### 4. conandata.yml
- 仅使用官方 GitHub URL（`https://github.com/devshane/zork/archive/refs/tags/v1.1.0.tar.gz`）
- 不使用镜像前缀（`gh-proxy.com` / `ghfast.top`）

### 5. 避免的坑
- 不要尝试用 `content.replace("-DTEXTFILE=...", ...)` — `$(DATADIR)` 是 make 变量，在 Makefile 被读取时才展开；用 `-D` 直接注入路径会因缺少 C 字符串引号导致编译错误（`/` 被解析为除法运算符）
- 不要在 test_package 中依赖 `env="conanrun"` 来查找 application 包的二进制 — 直接用 `dep.package_folder` 拼完整路径

## 验证结果
- conan create：真编成功（arm64+musl ELF, 354KB）
- 上游测试：4/4 PASS（Welcome to Dungeon / white house / mailbox / game is over）
- test_package：4/4 PASS（含 OHOS 消费者用例）
- conan-verify：PASS（G0-G4 全过）
- W3 本地 CI：PASS（L0/L1/L2/L4/L5 全过）
- finish：built（框架层 step5b/step8 为已知 bug，非阻塞）

---
**编译结束**: 2026-09-22 23:32
**最终状态**: built
---

**编译结束**: 2026-09-22 23:45
**最终状态**: built
