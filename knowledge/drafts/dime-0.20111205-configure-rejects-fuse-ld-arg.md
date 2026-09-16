# 老 configure 拒绝 `-fuse-ld=` 参数（OHOS 交叉链接器指定失效）

> Draft: DRAFT-DIME-CONFIGURE-REJECTS-FUSE-LD-ARG
> Stem: `dime-0.20111205-configure-rejects-fuse-ld-arg` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-DIME-CONFIGURE-REJECTS-FUSE-LD-ARG
- **严重度**: 2
- **类别**: autotools-cross-linker
- **触发工具**: autotools
- **阶段**: configure

## 错误特征

```
dime/0.20111205: RUN: bash ".../src/configure" --disable-shared --enable-static \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
  -fuse-ld=/storage/Users/currentUser/usr/local/bin/ld.lld
configure: error: unrecognized option: `-fuse-ld=/storage/Users/currentUser/usr/local/bin/ld.lld'
Try `.../src/configure --help' for more information.
```

## 可复现问题

OHOS 真机上对 dime 0.20111205（2009 年 autoconf 生成的 configure）传
`-fuse-ld=<path>` 作为 configure 命令行参数，configure 在选项解析阶段
直接报错退出，编译探测根本没跑。同一写法在 celt 1.0.0（较新的
configure）上可用——**不能把 celt 的 configure_args 写法照搬到更老的项目**。

## 根因分析

两层因素叠加：

1. OHOS 交叉环境**必须**显式指定链接器：OHOS 只带 `ld.lld` 没有裸 `ld`，
   且 clang 驱动不会在 PATH 里搜索链接器，configure 的 "compiler works"
   链接探测不带 `-fuse-ld` 必挂。
2. 老版 autoconf 的选项解析器把无法识别的非 `--` 参数当致命错误
   （新版会静默透传给编译器），`-fuse-ld=...` 因此无处安放。

## 解决方案

**主方案**: fuse-ld-via-toolchain-flag-lists

```python
if str(self.settings.os) == "OHOS":
    tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
    tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
    fuse_ld = f"-fuse-ld={self._lld_path()}"
    tc.extra_cflags.append(fuse_ld)      # 不放 configure_args
    tc.extra_cxxflags.append(fuse_ld)
    tc.extra_ldflags.append(fuse_ld)
```

原理：configure 的 AC_TRY_LINK 类探测是**编译+链接一步走**，flag 经
环境变量 CFLAGS/CXXFLAGS 一样到达链接器；最终库链接经 LDFLAGS 生效。
纯编译阶段多出的 `-fuse-ld` 只产生无害的 unused-argument 警告
（真机日志实证，构建通过）。

## 判别方法

- `grep timestamp= <src>/cfg/config.guess` 老于 2012 → 高概率中招；
- 或先拿 `-fuse-ld` 小参数试跑 configure，报 `unrecognized option`
  即换 flags 注入路线。
