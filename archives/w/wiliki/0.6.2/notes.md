# wiliki 0.6.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-17
- 编译器: clang/clang++
- 状态: published

## 编译步骤
1. 解压官方源码包 `WiLiKi-0.6.2.tgz`（SourceForge 官方源，Ubuntu 镜像同 sha256）
2. `./configure --prefix=/storage/Users/currentUser/usr/local`（gauche/0.9.15.2 工具链在 PATH）
3. `make -j1`（gosh 生成 src/wiliki/version.scm）
4. `make install DESTDIR=...`（staging 隔离）
5. `make check`（test/ 下 7 个测试文件全部通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 报 `can't create ./confXXX/subs1.awk: Permission denied` | HMDFS 对 umask 077 创建的临时目录拒绝写入（E011/E052） | 补丁 `0001-configure.patch`：configure 中 `umask 077` → `umask 022` |
| 2 | 制品仓 gauche 包内符号链接悬空 | 排查时误删本机 gauche 构建缓存（`gauchfd62a34becebe`） | 用发布一致的 settings 重新构建 gauche 恢复缓存，符号链接目标恢复 |
| 3 | conan 构建 out-of-source 失败（`wiliki/version.scm: No such file or directory`） | wiliki Makefile 使用 `./gen-version`、`> wiliki/version.scm` 等 in-source 相对路径 | `layout()` 设 `self.folders.build = self.folders.source`（in-source 构建） |
| 4 | `package_type = "library"` 报 no shared option | Conan 要求 library 类型声明 shared option | 声明 `options = {"shared": [True, False]}`，默认 False（纯 Scheme 无影响） |
| 5 | gauche 工具找不到模块（file/filter、srfi/13） | gauche 包以 prefix=/ 配置，运行环境缺 GAUCHE_LOAD_PATH/GAUCHE_DYNLOAD_PATH | `generate()` 里 prepend gauche bin 到 PATH 并 compose `runenv_info`（含 GAUCHE_LOAD_PATH/DYNLOAD_PATH），显式传给 `tc.generate(env=env)` |
| 6 | test_package `copy()` 报 src/dst 相同 | test_package 的 source_folder 与 build_folder 相同 | test() 直接运行 `gosh {source_folder}/test_wiliki.scm`，不 copy |

## 源码修改
- `configure`：umask 077 → 022（HMDFS 临时目录，E011），固化为 `patches/0001-configure.patch`

## 测试结果
- 上游 `make check`：test/core、format、log、edit、rss、auth、test-wiliki（CGI 集成）全部通过
- Conan test_package（L1）：gosh 加载 wiliki.parse 并调用 `wiliki-parse-string` 验证（R34 实质测试）
- conan-verify：G0-G4 + L2/L4/L5 全部通过；W3 本地 CI 模拟通过
---

**编译结束**: 2026-08-17 17:48
**最终状态**: published
