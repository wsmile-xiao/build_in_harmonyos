# nrg2iso 0.4.1 适配笔记

## 编译环境
- 构建系统: makefile（原始 Makefile 为简单手写版，非 autotools）
- 编译日期: 2026-06-11
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published
- 目标平台: OpenHarmony / aarch64 (musl libc)

## 编译步骤

1. `ohc-run.py init-build nrg2iso 0.4.1 --url=https://distfiles.macports.org/nrg2iso/nrg2iso-0.4.1.tar.gz`
2. 读取 `.build-context-nrg2iso-0.4.1` 获取环境变量
3. 发现原始 Makefile 硬编码 gcc，无 install/DESTDIR 支持 → 重写 Makefile
4. `cd $BUILD_SRC_DIR && make -j1 CC=clang CFLAGS="-fPIC -O2" PREFIX=$DEFAULT_PREFIX`
5. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`（DESTDIR 模式，R20）
6. `make install PREFIX=$DEFAULT_PREFIX`（本地安装模拟用户部署）
7. `ohc-run.py verify-build nrg2iso 0.4.1` → PASS
8. `ohc-run.py package nrg2iso 0.4.1` → 打包完成
9. `ohc-run.py finish nrg2iso 0.4.1 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始 Makefile 硬编码 gcc，无 install/DESTDIR 目标 | 上游 Makefile 过于简陋，仅 `gcc nrg2iso.c -o nrg2iso` 一行 | 重写 Makefile，引入 CC/CFLAGS/PREFIX/DESTDIR 变量，添加 install/uninstall 目标 |
| 2 | 元数据标记构建系统为 autotools，实际为 makefile | tarball 内无 configure 脽本，只有简单 Makefile | 修正 build_system 字段为 makefile |
| 3 | manifest 缺少顶层 build_system 字段 | init-build 模板默认不生成此字段 | 手动添加 `build_system: makefile` |
| 4 | manifest.sha256 为空 | init-build 未自动计算 | 手动计算并填入 sha256 校验和 |
| 5 | patches_applied 列表为空但磁盘有 1 个补丁 | refresh-patch 后未自动同步 manifest | 手动更新为 `["0001-Makefile.patch"]` |

## 源码修改

- **0001-Makefile.patch**: 重写 Makefile（+17/-3 行）
  - 硬编码 gcc → 环境变量 CC（默认 clang）
  - 添加 CFLAGS（默认 -fPIC -O2）
  - 添加 PREFIX/DESTDIR 支持
  - 添加 install/uninstall 目标
  - 修正 clean 目标格式

## 依赖版本

无依赖。nrg2iso 是纯 C 单文件程序，仅依赖 libc（musl）。

## 验证结果

```bash
# 版本检查
$ nrg2iso --version
nrg2iso v0.4

# 帮助信息
$ nrg2iso --help
Nrg2Iso v0.4 by G. Kokanosky
released under the GNU GPL v3 or later

Usage :
nrg2iso image.nrg image.iso

--version    display version number
--help       display this notice

# 核心功能测试：NRG → ISO 转换
# 构造模拟 NRG 文件（307200字节头部 + 40960字节ISO数据）
$ nrg2iso test-dummy.nrg test-dummy.iso
|======================================================================>[100%]
test-dummy.iso written : 40960 bytes
# 输出大小验证：40960字节（正确剥离307200字节NRG头部） ✅

# 边界测试：ISO文件检测（拒绝转换已经是ISO的文件）
$ nrg2iso test-real-iso.bin output.iso
It seems that test-real-iso.bin is already an ISO 9660 image
[Aborting conversion] ✅

# 边界测试：不存在文件
$ nrg2iso nonexistent.nrg output.iso
nonexistent.nrg : No such file ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nrg2iso-0.4.1-ohos-aarch64.tar.gz | 78881 字节 (77KB) | 预编译主包（ELF 已签名、已 strip） |
| nrg2iso-0.4.1-ohos-aarch64-debug.tar.gz | 26647 字节 | 调试符号包 |
| 0001-Makefile.patch | - | Makefile 适配补丁（+17/-3 行） |

## 注意事项

- 上游源码 VERSION 宏定义为 `"0.4"`（不是 `"0.4.1"`），`--version` 输出为 `nrg2iso v0.4`，与 tarball 版本号 0.4.1 的差异是上游行为
- nrg2iso 无自动化测试套件（无 make check 目标），功能验证通过手动构造测试文件完成
- 二进制为动态链接（ld-musl-aarch64.so.1），无外部库依赖

---

**编译结束**: 2026-06-11 02:51
**最终状态**: published