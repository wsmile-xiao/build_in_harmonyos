# DRAFT-ohos-siril-autoconf-cross-args-conftest：OHOS 上 autotools 必须按 cross 语义跑 configure

> Contributor: SnowTT | Status: Draft | Updated: 2026-09-05
> Source: siril 1.2.3 适配（conan-verify G2 修复链）

## 背景

siril 1.2.3（GTK3 天文图像处理应用）在 HarmonyOS PC (aarch64) 上用 conan（双 profile
= ci/conan/profiles/ohos-aarch64）做 autotools 适配时，configure 在"本机模式"下失败：

```text
checking whether we are cross compiling... configure: error: cannot run C compiled programs.
If you meant to cross compile, use '--host'.
```

根因：conftest 链接 conan 依赖（gtk/cairo/opencv 等）后，运行时加载器找不到 HMDFS
缓存路径（.conan2）下的 libcairo.so.2 等依赖 .so；且本机无图形/D-Bus 会话，GLib/GTK
库加载还可能二次死锁。autoconf 因未显式给 --host 而判定"本机编译"，遂执行 ./conftest → 失败。

## 修复

在 conanfile.py 的 generate() 中给 AutotoolsToolchain.configure_args 显式追加：

```python
tc.configure_args.append("--build=x86_64-unknown-linux-gnu")
tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
```

host≠build 使 autoconf 判定 cross_compiling=yes，跳过一切 conftest 运行（仅做
编译/链接探测）。环境 config.guess/config.sub 已识别 *-linux-ohos（exit 0），无需替换。

连带处理：configure.ac 中 `test "$cross_compiling" != "yes"` 分支会把内置子构建
（siril 的 htmesh、librtprocess）改成 AC_MSG_ERROR —— 需放开 cross 分支允许走内置
cmake 构建（0006 补丁）或降级为可选（0001 补丁 librtprocess 先例）。

## 相关既有条目差异化定位

| 既有条目 | 差异点 |
|---------|--------|
| E323 conan-verify ghfast-bak rollback | 本条目针对 autotools 交叉语义（--host/--build），非制品回滚问题 |
| E490 autotools helper script 权限 | E490 管 configure 脚本可执行位；本条管 configure 阶段 conftest 执行被跳过（cross 语义），互不重叠 |
| DRAFT-6048-babeltrace AM_PATH_GLIB 运行检测 | babeltrace 用 --disable-glibtest 单点绕过；本条给出通用 cross 语义方案（适用于整树 GTK 依赖链） |

## 验证

conan-verify G0-G4 全绿；G2 conan create 成功，test_package `siril-cli --version`
输出 `siril 1.2.3` rc=0。
