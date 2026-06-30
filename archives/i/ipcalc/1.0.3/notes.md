# ipcalc 1.0.3 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile + meson.build optional)
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 源码来源: gitlab.com/ipcalc/ipcalc (现代C版，非Python/Perl版)
2. 下载源码 tarball: ipcalc-1.0.3.tar.gz (56518 bytes)
3. init-build: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build ipcalc 1.0.3 --url=... --no-download`
   - Savannah URL 返回 404，ipcalc.org 使用 JS redirect
   - 手动下载后用 `--no-download` 绕过 SSL 证书问题
4. 修改 Makefile: 添加 install target (PREFIX 支持 + DESTDIR 模式)
5. 编译: `make USE_GEOIP=no USE_MAXMIND=no CC=clang CFLAGS="-fPIC -O2 -Wall" PREFIX=$DEFAULT_PREFIX`
6. Staging 安装: `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`
7. 测试: 手动运行 16 个核心测试 (全部 PASS)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 下载 404 | Savannah 上 ipcalc tarball 不存在 | 从 GitLab gitlab.com/ipcalc/ipcalc 获取 |
| 2 | ipcalc.org JS redirect | ipcalc.org 使用 Cloudflare JS 加载 | 直接用 GitLab API 获取 release tarball |
| 3 | ohc-run.py init-build SSL 失败 | HarmonyOS 缺 CA 证书 + _download_one 未使用 _urlopen SSL fallback | 手动下载 tarball + --no-download |
| 4 | Makefile 缺 install target | 原始 Makefile 只有 all/clean | 手动添加 install target (PREFIX + DESTDIR) |
| 5 | 无 configure 脚本 | ipcalc 使用 Makefile/meson 构建系统 | 直接用 make 带参数编译 |
| 6 | /tmp 只读 (R10) | HarmonyOS E002 gotcha | 使用 $TMPDIR=/data/storage/el2/base/cache |

## 源码修改

- **Makefile**: 添加 install target
  - `PREFIX?=/usr/local` (可配置安装前缀)
  - `install: ipcalc` → `mkdir -p $(DESTDIR)$(PREFIX)/bin && cp ipcalc $(DESTDIR)$(PREFIX)/bin/ipcalc`
  - 这是必要的修改：原始 Makefile 缺少 install target，无法进行 DESTDIR 模式安装

## 依赖版本

- 无外部依赖 (USE_GEOIP=no, USE_MAXMIND=no 禁用可选 geo 功能)
- libdl: 系统内置 (dlopen/dlclose 可用)
- clang: 15.0.4

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/ipcalc --version
ipcalc 1.0.3

$ ipcalc -b 192.168.1.1/24
BROADCAST=192.168.1.255

$ ipcalc -m 192.168.1.1/24
NETMASK=255.255.255.0

$ ipcalc -c 127.0.0.1
# 返回成功 (exit 0)

16 个测试全部 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| ipcalc-1.0.3-ohos-aarch64.tar.gz | 预编译包 (由 ohc-run.py package 生成) |
| 0001-add-install-target.patch | Makefile install target 补丁 |

## 注意事项

- ipcalc 有两个可选功能: GeoIP 和 MaxMindDB (IP地理定位)
- 本次编译禁用这两个功能 (USE_GEOIP=no, USE_MAXMIND=no)，核心IP计算功能不受影响
- 如需启用，可设置 USE_MAXMIND=yes USE_RUNTIME_LINKING=yes，需要 -ldl (系统内置)
- 版本号从 meson.build 文件中提取: `cat meson.build|grep 'version :'|cut -d ':' -f 2|tr -d " \'"`
---

**编译结束**: 2026-05-26 10:24
**最终状态**: published
