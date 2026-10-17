# DRAFT-libyubikey-1.13-conanbuild-path-hnp-ar-libtool-probe

> Status: Draft | Updated: 2026-09-27 | Source: libyubikey 1.13 真机 shadow CI r2（job libyubikey-1.13-20260927）

## 摘要

OHOS CI 的 conanbuild 环境 PATH **不含** `/data/service/hnp/bin`：CC/CXX 由
profile 以绝对路径注入所以 clang 正常，但裸名 `ar`/`ranlib` 解析不到。autoconf
探测不到 ar 时会退化为 MSVC 风格的 `link -lib` archiver 探测，随后失败：

```
checking for ar... no
checking for lib... no
checking for link... link -lib
checking the archiver (link -lib) interface... unknown
configure: error: could not determine link -lib interface
```

该签名在知识库（graph + drafts）中无条目。影响所有需要打静态库的 autotools
包（几乎全部）：**编译器探测通过 ≠ 工具链可用**，binutils 探测是独立失败点。

## 根因

- profile `[conf] tools.build:compiler_executables` 以绝对路径给 CC/CXX
  （`/data/service/hnp/bin/clang`），configure 的 `checking for gcc...` 直接可用；
- conanbuild 聚合 PATH 里有 make/awk/install（~/usr/local/bin 与系统目录）但
  没有 hnp bin，`AC_CHECK_TOOL([ar])`/ranlib 找不到；
- autoconf 在无 ar 时回退探测 `lib`/`link -lib`（本为 MSVC 环境设计），
  `ax_check_compile_flag` 类 archiver interface 探测在 OHOS 上必然 unknown。

## 修复（按稳健度排序）

1. build() 内 OHOS 分支把 hnp bin 前置到 PATH（本案例采用，与探针环境一致）：

```python
_hnp_bin = "/data/service/hnp/bin"
if os.path.isdir(_hnp_bin):
    os.environ["PATH"] = _hnp_bin + os.pathsep + os.environ.get("PATH", "")
```

2. 更通用的写法（参照 DRAFT-9639 minibwa 的推导思路）：从 CC 的 dirname 推导
   工具目录，显式设置 `AR=<dir>/llvm-ar`、`RANLIB=<dir>/llvm-ranlib` 并做
   isfile/shutil.which 校验——不依赖固定路径，可移植到工具链装在其他位置的机器。

## 验证

- libyubikey/1.13 r3 起 `checking for ar... ar`、`checking for ranlib... ranlib`
  通过，编译 + make check（TOTAL=1 PASS=1）+ 安装 + test_package 全绿；
- r4 全量：L0/L1/L2/L5 pass、exit 0
  （run codex-1.13-libyubikey-1.13-20260927-conan-20260927-150715-23005）。

## 相关条目

- DRAFT-9639（minibwa）：conf 里 CC 绝对路径**不存在**时从 PATH 回退——方向相反
  （那是路径失效，本条是路径有效但目录不在 PATH、裸名工具不可达）。
- E232 / DRAFT-libyubikey-1.13-hmdfs-config-status-mktemp-chain：同一次适配的
  前两级失败（脚本 execve、config.status mktemp），本条是第三级。
