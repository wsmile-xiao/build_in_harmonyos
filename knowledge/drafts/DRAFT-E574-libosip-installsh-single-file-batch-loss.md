# DRAFT: 老版 install-sh 单文件限制 + automake 批量调用 —— make install rc=0 但批量安装静默丢文件

- **包**: libosip/5.3.2 (autotools)
- **日期**: 2026-09-11
- **环境**: OHOS PC (aarch64, musl)；工作区 hmdfs，/tmp tmpfs 对照
- **状态**: 实测复现确认（最小复现矩阵 + conan create 修复前/后对比）

## 症状

`make install`（install-data-am）exit=0，日志列出全部头文件的
`install-sh -c -m 644 a.h b.h ...` 批量调用，但安装后
`find $PKGROOT/include -type f | wc -l` 只有 3 个文件，其余 28 个头文件
全部丢失，**无任何错误输出**（修复前 3 → 修复后 31）。

## 最小复现（hmdfs 与 /tmp tmpfs 上结果一致）

```
mkdir d
./install-sh -c -m 644 a.h b.h c.h d.h d/     # rc=0
ls d/ | wc -l                                   # → 1（只有 a.h）
```

- [对照] 新版 automake-1.16 install-sh 同命令 → 4/4 全装。
- [对照] 旧版单文件安装到已存在目录：目录完好，未被覆盖为文件。
- [破坏性反向] 不替换 install-sh 时 3/31 头文件落盘；替换后 31/31。

## 根因（修正稿）

三因叠加，与 hmdfs 文件系统无关：

1. **OHOS PC 无 `/usr/bin/install`**（精简 userland 不带 coreutils install），
   configure 探测失败回退到 tarball 自带 install-sh；
2. **tarball 内 install-sh 是 1991 X11R5 版**（无 scriptversion 行，251 行），
   参数循环注释明说 "can only install one file at a time"：src 只取第一个
   文件参数，其余静默丢弃，rc=0；
3. **automake-1.16 的 `am__base_list` 批量机制**每批最多 64 个文件一次
   调用 install-sh → 每批只装第 1 个。

libosip 3 个头文件目录各 1 批 = 恰好 3 个头文件，与草稿初版记录的
"3 → 31" 完全吻合（交叉验证）。

> 初版草稿所称 "hmfs uid 映射导致目录被覆盖为文件" 不成立：单文件重复
> 安装与批量安装下目标目录均完好（hmdfs/tmpfs 一致），已删除该说法。

## 修复

`_patch_source_tree()` 中把 tarball 的 `scripts/install-sh` 替换为主机
automake-1.16 版本（连同 config.guess/config.sub/missing/compile/depcomp，
它们同 vintage，见 E007）：

```python
am_dir = glob(os.path.join(toolchain_share, "automake-*"))
for name in ("install-sh", "config.guess", "config.sub",
             "missing", "compile", "depcomp"):
    shutil.copy2(os.path.join(am_dir[-1], name),
                 os.path.join(src, "scripts", name))
    os.chmod(dst, 0o755)
```

防护层：package() 后断言关键产物数量，不信任 make install 退出码。

## 与现有知识的关系

- E490（执行位丢失）、E514（ltmain aux-dir）：分别处理权限位与 libtoolize
  辅助目录，未覆盖 install-sh 安装语义本身；
- DRAFT-postgresql-18.3-install-shim-separate-args：同一问题域（OHOS install
  工具环境），但根因不同——PATH 首位的 install shim 不支持分离参数
  （`cp: bad '755'`，显式报错中断），本条是无 /usr/bin/install 回退 +
  老脚本单文件静默丢文件；
- E007：config.guess/sub 需替换的三元组识别问题，本条连带替换顺带解决。

## 通用性

任何 2010 年代中期以前发布、tarball 内置老版 install-sh 的 autotools 包，
在无 /usr/bin/install 的 OHOS PC 环境构建时都存在此风险；
"install rc=0 但文件数不对"是关键信号。
