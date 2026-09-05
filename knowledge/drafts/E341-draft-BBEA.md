# E341 — Minimal OHOS Make projects need evidence-bound test gating and Conan-native packaging

## 错误特征

An OHOS device can compile a small C socket library and its TCP/UDP tests, then
fail two later stages independently:

```text
bind: Operation not permitted
make: install: No such file or directory
```

The first message occurs for pathname Unix-domain sockets even when the test is
run below a user-writable directory. The second occurs when a Makefile invokes
the GNU `install` utility that is absent from the device toolset.

## 触发条件

- 构建系统: a minimal C Makefile project
- 阶段: upstream integration testing and Conan `package()`
- 平台: HarmonyOS PC arm64 / OHOS profile

## 根因分析

These are capability boundaries, not evidence that the socket library itself
failed to compile. The upstream harness launches TCP, UDP, and pathname
AF_UNIX client/server pairs. OHOS permits the TCP and UDP pairs on the tested
runner but rejects the pathname `bind()` operation. Separately, the Makefile's
install target assumes GNU coreutils `install`, which is not present. Treating
either failure as a generic test failure hides the supported coverage; treating
it as a blanket pass is equally misleading.

## 解决方案

### 推荐方案

1. Run the original upstream Unix-socket case in a writable, task-private
   directory and capture the exact errno before changing the recipe.
2. Add a narrow, opt-in source-level gate such as
   `SOCKET99_SKIP_UNIX=1` around only the unsupported test group. Leave the
   upstream TCP and UDP groups unchanged and make the OHOS recipe set the gate
   explicitly.
3. Record declared, executed, passed, and skipped roles separately. A skipped
   role is not a passed role.
4. When `install` is unavailable, use Conan's `mkdir()` and `copy()` helpers in
   `package()` to materialize the exact library and public headers. This keeps
   packaging inside Conan without installing extra system tools.
5. Finish with an installed-package consumer that compiles against the public
   header, links the packaged archive, and exercises representative API
   behavior.

### 禁止做法

- Do not wrap the entire upstream suite in `|| true` or unconditionally return
  success.
- Do not claim skipped roles as passed, or infer that all AF_UNIX forms are
  unavailable from one pathname-bind failure.
- Do not relax system permissions or install tools globally just to make one
  package pass.

## 验证
```bash
command -v install
<run the unmodified upstream harness in a writable task-private directory>
SOCKET99_SKIP_UNIX=1 make -j1 test
conan create <recipe-dir> --build=missing -pr:h=<ohos-profile> -pr:b=<ohos-profile>
<run the generated installed-package consumer>
```

## 关联条目

- E024: Unix-domain socket bind is restricted on OHOS.
- E098 and E174: the OHOS device may lack the GNU `install` command.
- E340: a broader AF_UNIX filesystem capability matrix and abstract-namespace
  alternative.
- E341 is narrower: it documents the combined recipe/test accounting pattern
  for a small Make project, including Conan-native packaging.

## socket99 evidence

The `socket99/0.2.2` recipe first built and ran its upstream harness on the
OHOS runner. TCP blocking, TCP nonblocking, and UDP client/server roles passed;
both pathname Unix-domain groups (four client/server roles) failed at `bind()`
with `Operation not permitted`. The same errno was reproduced under a writable
user directory. After adding the explicit gate and replacing `make install` with
Conan `mkdir/copy`, the same Conan create completed: 6 of 10 upstream roles
passed, 4 of 10 were explicitly skipped for the recorded OHOS limitation, and the
consumer executable passed 8 of 8 checks.
