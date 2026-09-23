# HMDFS 拒绝脚本直接 exec：Autotools 配方用 sh 调用 configure

- **软件**: libdisasm 0.23（泛化到所有 Autotools 配方）
- **阶段**: build（conan create）
- **severity**: 2
- **状态**: DRAFT

## 现象

```
/system/bin/sh: /path/to/conan-home/p/b/<hash>/b/configure: Permission denied
libdisasm/0.23: ERROR: ... autotools.configure() ConanException: Error 126 while executing
```

此时 `ls -la configure` 显示 mode 已是 `rwxr-x---`（有 owner 执行位），
`test -x configure` 也返回真。

## 根因

HMDFS 用户目录（`/storage/Users/<user>`）对**脚本**的直接 execve 一律拒绝：

1. HMDFS 权限判定把当前进程归入 others 类（即使 stat 显示的 owner uid 与进程一致），
   others 位无 x 即拒。
2. chmod 无法补 o+x：`chmod 755` 静默无效；`umask(0)` + `os.open(..., 0o755)` 创建时
   mode 被强制钳为 `0770`（剥 o+x、加 g+w）。
3. **ELF 不受影响**：同目录 mode 750 的 ELF 二进制可直接执行（clang/make/ar/ranlib/
   测试二进制全部正常）。只有 binfmt_script 路径被拒。

`conan.tools.gnu.Autotools.configure()` 硬编码直接 exec `"<build>/configure"`，
因此在这类 worker 上必然 Error 126。`config.guess/config.sub/config.status/libtool`
由 configure 与 automake Makefile 以 `$SHELL` 前缀调用，不受影响。

## 修复

build() 中改用 shell 调用（与上游文档 `sh ./configure` 一致，CI/Linux 通用）：

```python
tc = AutotoolsToolchain(self)
configure_args = tc.configure_args + self._ohos_configure_args()
self.run('sh "{}" {}'.format(os.path.join(self.source_folder, "configure"),
                             " ".join(configure_args)))
```

配套环境：`SHELL=/bin/sh`、`CONFIG_SHELL=/bin/sh`、`TMPDIR` 指向可写目录
（clang 在 /tmp 只读时也需 TMPDIR）。

与 dirb 2.22 的 `os.chmod(configure, 0o755)` 修复互补：那类 worker chmod 可置位且
750 即可 exec；本类 worker chmod 完全无效，sh 调用是唯一通用解。

## 证据

libdisasm 0.23 真机（10.62.178.77，isolated `CONAN_HOME=$HOME/tmp/.../conan-home`）：

- 首跑 Error 126，configure mode 为 `rwxr-x---`；
- `chmod +x`/`chmod 755` 不改变 mode；umask(0)+0755 重建后被钳为 `0770` 仍拒；
- ELF 探针（mode 750）直接 exec 正常，脚本 denied、`sh` 调用正常；
- 改 `sh` 调用后 conan create 全绿（`libdisasm.a` + `x86dis` 打包成功，
  package id `21b17f8b2bc0e9511e276e3d57a23893067cefe5`），test_package 21/21 通过。
