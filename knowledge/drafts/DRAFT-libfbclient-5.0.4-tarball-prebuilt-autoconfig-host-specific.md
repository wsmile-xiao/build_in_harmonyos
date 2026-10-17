# DRAFT-libfbclient-5.0.4-tarball-prebuilt-autoconfig-host-specific

## 可复现症状与稳定错误签名

`--enable-client-only` 配置完成、`configure` 返回 0 之后，`make` 在编译公共代码时报：

```
src/common/ThreadStart.cpp:185:11: error: use of undeclared identifier 'pthread_setcanceltype'; did you mean 'pthread_setname_np'?
src/common/ThreadStart.cpp:185:62: error: cannot initialize a parameter of type 'const char *' with an rvalue of type 'int *'
src/common/ThreadStart.cpp:213:3: error: use of undeclared identifier 'pthread_cancel'
```

稳定签名：`use of undeclared identifier 'pthread_cancel'` / `'pthread_setcanceltype'`，
且报错文件是 `src/common/ThreadStart.cpp`（Firebird 公共线程封装）。

## 根因与最小复现

- 上游 release tarball 中的 `src/include/gen/autoconfig.auto` 是**打包者在 glibc 宿主上
  执行 configure 的产物**（文件头：`Generated from config.h.in by configure`），含：

  ```
  #define HAVE_PTHREAD_CANCEL 1
  #define HAVE_DLINFO 1
  ```

- `src/include/gen/autoconfig.h` 是指向 `autoconfig.auto` 的**符号链接**，因此只要没有在
  本机重新执行 configure，整棵源码树就按 glibc 能力集编译。
- OHOS（musl）不提供 `pthread_cancel`/`pthread_setcanceltype`/`dlinfo`，而
  `src/common/ThreadStart.cpp` 在 `HAVE_PTHREAD_CANCEL` 为真时无条件调用它们。
- 最小复现（本机实测）：把 `autoconfig.auto` 还原成 tarball 版 → `make` 立即在上述三行报错；
  重新执行 `./configure --enable-client-only --without-editline --disable-rpath` 后
  `grep HAVE_PTHREAD_CANCEL` 变为 `/* #undef HAVE_PTHREAD_CANCEL */` → `make -j4` rc=0。

## 修复

1. **保证 configure 在构建树内真实执行**（本包为 in-source 构建：
   `basic_layout(self, src_folder=".")` + `self.folders.build = "."`），生成态即为正确态。
2. **不要把它当"生成物"还原**：`refresh-patch --auto` 会把被 configure 改写的
   `src/include/gen/autoconfig.auto` 列为变更文件；正确动作是把它从变更集里排除并**更新
   edit-tracker 基线**（把 configure 生成后的内容作为基线），而不是 `cp` 回 tarball 版本。
   本次实测教训：先在 `configure` 后把该文件还原为 tarball 内容 → 下一次 `make` 直接失败
   （错误签名如上），并会被误判为"平台工具链不支持 pthread 取消"。
3. 自检：`grep -n 'HAVE_PTHREAD_CANCEL\|HAVE_DLINFO' src/include/gen/autoconfig.auto`
   在 OHOS 上应为 `#undef`（本例：313 行 `/* #undef HAVE_PTHREAD_CANCEL */`）。

## 适用范围

所有 **release tarball 里预置 configure 产物**的 autotools 项目（尤其是"源 tarball 由
维护者在另一发行版上 `make dist` 生成"的项目；git tag 快照通常不含该文件，反而不会踩到）。
判定方法：`head -3 src/include/gen/autoconfig.auto`（或等价 config.h 产物）看到
`Generated ... by configure`，且其中宏与目标平台能力不符。

## 证据

- 还原 tarball 版：`ThreadStart.cpp` 三处编译错误（100% 复现）。
- 生成版：`make -j4` rc=0；`conan create` 成功；上游 `common_test` 13/13 通过。
- 对照宏：tarball `#define HAVE_PTHREAD_CANCEL 1` / `#define HAVE_DLINFO 1`
  vs 生成 `/* #undef HAVE_PTHREAD_CANCEL */` / `/* #undef HAVE_DLINFO */`。
