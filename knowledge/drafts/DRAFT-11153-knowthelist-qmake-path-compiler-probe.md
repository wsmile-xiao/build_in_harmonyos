# DRAFT-11153-knowthelist-qmake-path-compiler-probe：qmake 探测目标编译器走 PATH（clang++），CI worker 受限 PATH 下 "Cannot run target compiler 'clang++'"

> Contributor: ohc-worker | Status: Draft | Updated: 2026-09-20
> Source: knowthelist 2.3.1 适配（PR #11153）CI 构建 #51439 失败，本地 conan create 通过
> 对应：`knowledge/drafts/DRAFT-11153-knowthelist-qmake-path-compiler-probe.kv`

## 现象

qmake 工程（Qt5 qmake 构建，依赖 `qt/5.15.19`）本地 `conan create` 通过，但提交到 CI 后
`conan-build-test` 步骤在 `build()` 的 qmake 调用处失败：

```console
knowthelist/2.3.1: RUN: ".../qt50272a33cb52e/p/bin/qmake" QMAKE_PKG_CONFIG=pkg-config src.pro
Project ERROR: Cannot run target compiler 'clang++'. Output:
===================
===================
Maybe you forgot to setup the environment?
```

关键特征：**Output 段为空**，没有任何 `Operation not permitted` 之类的权限/签名报错。

## 根因

qmake 的 mkspec（`common/clang.conf`）定义目标编译器为：

```makefile
QMAKE_CXX = $${CROSS_COMPILE}clang++
```

交叉构建时 `CROSS_COMPILE` 为空 → 编译器名字就是裸的 `clang++`。qmake 运行时从 **PATH**
解析 `clang++` 并执行探测，并且：

1. **不读 `CC`/`CXX` 环境变量**（实验确认：仅设 `CC=/data/service/hnp/bin/clang`、
   `CXX=/data/service/hnp/bin/clang++` 不解决问题）；
2. **不接受命令行 `QMAKE_CXX=` 赋值**（探测发生在赋值解析之前）。

而 CI worker（buildbot appspawn 沙箱）的 PATH 受限，通常为
`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:~/.local/bin`，**不含**工具链目录
`/data/service/hnp/bin`（clang++ 所在）。本地 shell 的 PATH 含该目录，所以本地通过、
CI 失败。配方仅靠 `Environment().vars(self).apply()` 注入 PATH 时，在该类 worker 上注入
不可靠，探测失败且输出为空。

## 推荐方案（PR #11153 修复，已验证）

在 `build()`/`package()` 的 `self.run` 命令内**内联 PATH 前缀**，与
`Environment().vars(self).apply()` 双保险（参照 posixsignalmanager，同依赖 qt/5.15.19 且
CI 通过）：

```python
def _run_prefix(self):
    qt = self.dependencies["qt"]
    return "PATH=%s/bin:/data/service/hnp/bin:$PATH " % qt.package_folder

# build()
with self._build_env().vars(self).apply():
    self.run(self._run_prefix() + '"%s" QMAKE_PKG_CONFIG=pkg-config src.pro' % qmake, cwd=src_dir)
    self.run(self._run_prefix() + "make -j1", cwd=src_dir)

# package()
with self._build_env().vars(self).apply():
    self.run(self._run_prefix() + 'make install INSTALL_ROOT="%s" STRIP=true' % self.package_folder, cwd=src_dir)
```

qt bin 前置保证 qmake/moc/uic/rcc 可达，`/data/service/hnp/bin` 前置保证 clang++ 可达，
不依赖 worker 的 PATH 或 conan env 注入是否生效。

验证：
- 本地完整 PATH 跑 `CI_PACKAGES="archives/k/knowthelist/2.3.1" zsh ci/conan/build_and_test.sh` → PASS；
- 本地用 CI 式受限 PATH（不含 `/data/service/hnp/bin`，保留 zsh/python3 工具链）模拟跑 → PASS，
  且 qmake 阶段无 "Cannot run target compiler"。

## 与 ELF 签名族的区分

| 条目 | 症状 | 输出特征 | 根因 |
|------|------|----------|------|
| 本条 | Cannot run target compiler 'clang++' | Output 段**为空**，无权限字样 | PATH 找不到 clang++（环境变量/PATH 问题） |
| E318/E486/E511 | exec 拒绝 | 含 `Operation not permitted` / `Error 126` | HarmonyOS 拒绝执行未签名 ELF（签名问题） |

## 来源

- 事件：knowthelist 2.3.1 适配 PR #11153，CI 构建 #51439 失败（qmake 编译器探测失败）
- 修复提交：`2a5964184a`
