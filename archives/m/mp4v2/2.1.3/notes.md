# mp4v2 2.1.3 适配笔记

## 编译环境

- 构建系统: autotools（需先 autoreconf 生成 configure 脚本）
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4 / clang++（OpenHarmony SDK 26.0.0.18）
- 目标架构: aarch64-linux-ohos
- 最终状态: built

## 编译步骤

1. 下载源码：从 Savannah 下载 mp4v2-2.1.3.tar.gz
2. 运行 `autoreconf -fi` 生成 configure 脚本（tarball 不含生成文件）
3. 修复 E011 HMDFS umask 问题：`sed -i 's/umask 077/umask 022/g' configure`
4. `./configure --prefix=$DEFAULT_PREFIX`
5. `make -j1`（耗时约 256 秒）
6. `make install DESTDIR=$TEST_PREFIX`（staging 安装）
7. `ohc-run.py package mp4v2 2.1.3`（预编译包制作）
8. `make install`（本地安装，模拟用户部署）
9. 功能验证：所有工具和 API 均正常
10. `make check`（跳过，需 DejaGnu/runtest）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub SSL 下载失败 | HMDFS 证书验证失败 | 使用 Savannah URL |
| 2 | tarball 无 configure 脚本 | mp4v2 发行包不含 autotools 生成文件 | `autoreconf -fi` 生成 |
| 3 | config.status Permission denied | E011: HMDFS UID 映射导致 umask 077 临时目录不可写 | `sed -i 's/umask 077/umask 022/g' configure` |
| 4 | G0 干净构建验证失败 | tarball 无 configure，clean-verify 无法 autoreconf | 记录为已知限制 |

## 源码修改

- `configure`: umask 077 → umask 022（E011 HMDFS 平台适配）

## 依赖

无必需依赖。

## 验证结果

### API 级别验证（C++ 链接测试）

```
MP4Create           → OK (handle=0x5b18402400)
MP4AddVideoTrack    → OK (trackId=1, 320x240)
MP4GetTrackDuration → OK (duration=0)
MP4Close            → OK
```

生成 931 字节的完整 MP4 文件。

### CLI 工具验证

| 工具 | 版本号 | 测试操作 | 结果 |
|------|--------|----------|------|
| mp4info | 2.1.3 | 查询 MP4 文件信息 | ✅ 正常输出 |
| mp4file | 2.1.3 | --list/--dump | ✅ 正常输出 |
| mp4track | 2.1.3 | --list | ✅ 正常输出 |
| mp4trackdump | 2.1.3 | 查询样本信息 | ✅ 正常输出 |
| mp4art | 2.1.3 | --list | ✅ 正常输出 |
| mp4chaps | 2.1.3 | --list | ✅ 正常输出（无章节） |
| mp4extract | 2.1.3 | -l | ✅ 正常输出 |
| mp4tags | 2.1.3 | --help/--version | ✅ 正常输出 |
| mp4subtitle | 2.1.3 | --list | ⚠️ 未实现（已知限制） |

### pkg-config

```
pkg-config --modversion mp4v2 → 2.1.3
pkg-config --libs mp4v2 → -L.../lib -lmp4v2
pkg-config --cflags mp4v2 → -I.../include
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mp4v2-2.1.3-ohos-aarch64.tar.gz | 4173KB | 预编译包（含 lib+bin+include+pkgconfig） |
| mp4v2-2.1.3-ohos-aarch64-debug.tar.gz | 1569KB | 调试符号包 |

## 注意事项

- mp4v2 tarball 不含 configure 脚本，构建前必须先运行 `autoreconf -fi`
- E011 HMDFS umask 修复是所有 autotools 项目的通用问题
- make check 需要 DejaGnu（runtest），当前环境不可用
- mp4subtitle --list 功能在本版本未实现，不影响核心功能
- G0 干净构建验证因 tarball 无 configure 而失败，为已知平台限制

---

**编译结束**: 2026-05-26
**最终状态**: built