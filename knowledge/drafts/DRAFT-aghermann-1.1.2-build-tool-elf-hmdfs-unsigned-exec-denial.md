# DRAFT: conan 缓存内构建期工具未签名被 HMDFS 拒绝执行（aghermann 1.1.2 案例）

## 错误现象

PR #10748（aghermann 1.1.2）CI 构建 #51312：编译、链接全部通过后，在 build
尾声的 data/ui 阶段失败：

```
.../build-release/_glib_tools/glib-compile-resources --sourcedir=... --target=aghermann.gresource ...
.../_glib_tools/glib-compile-resources[3]: /storage/Users/currentUser/.cache/conan2/p/glibcad.../p/bin/glib-compile-resources: Operation not permitted
make[3]: *** [Makefile:562: aghermann.gresource] Error 126
```

特点：报错行由 sh 打出、路径指向 conan 缓存内工具二进制；`file` 确认是
ELF shared object。同一缓存路径本地可执行 → 环境差异（worker 签名校验状态）。

## 根因

HarmonyOS 对用户区 ELF 有签名校验（E318/E486 同族）。conan 依赖包（glib 等）
`bin/` 下的构建期工具是包发布时链出的 ELF，部分 CI worker 的签名校验状态会
拒绝执行 conan 缓存内的未签名 ELF，`execve` 返回 EPERM，make 报 Error 126。

与 E079（硬链接 EPERM）、E024（AF_UNIX bind EPERM）报错文本相同但系统调用
不同：本条是 execve 一个 ELF 被拒。

## 修复方案（已在 PR #10748 commit cbee1679de 验证通过）

配方 `_prepend_glib_tools()` 内，执行前对每个工具：

1. `shutil.copy2` 复制到构建私有目录 `_glib_tools/`（**勿改缓存原文件**）；
2. `llvm-objcopy --remove-section .codesign` 清旧签名段（`|| true` 容错）；
3. `binary-sign-tool sign -inFile X -outFile X.signed -selfSign 1` 自签；
4. `os.replace` + `chmod 0755`，wrapper 脚本 exec 指向已签副本；
5. 签名工具缺失或失败时降级为原路径（已在允许执行的环境不受影响）。

wrapper 同时补 `LD_LIBRARY_PATH`（收集所有依赖包 lib 目录），一并解决
relocation 后 libgio/libglib 加载失败。

本地全链路验证：`CI_PACKAGES="archives/a/aghermann/1.1.2" zsh ci/conan/build_and_test.sh`
→ L0/L1/L5 pass，签名日志 `add codesign section success`。

## 适用范围

所有在 build() 期间执行 conan 依赖包 bin/ 下工具的配方：glib-compile-resources、
glib-compile-schemas、glib-genmarshal、gdbus-codegen、gettext 工具、itstool 等。

---
*草稿待审核 promote；配套 kv: DRAFT-aghermann-1.1.2-build-tool-elf-hmdfs-unsigned-exec-denial.kv*
