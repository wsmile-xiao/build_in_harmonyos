# TCL 9.0.3.1 编译笔记（HarmonyOS PC · 标准 Conan Autotools）

## 定位
- 产出**动态** `libtcl9.0.so`（供 dlopen，及作 tk 等的交叉编译依赖），区别于 8.6.14 的静态 `libtcl8.6.a`。
- 源码 = **ohos_tcl fork**（`9.0.3.1` 分支，OHOS 源码适配已 baked in）；用**标准 conan Autotools**
  构建（`unix/configure` + `make`），吃 CI profile 的原生 clang（`/data/service/hnp/bin/clang`），
  不依赖交叉 NDK / 自定义脚本。

## 关键适配（都在 conanfile 里，均为 OHOS 原生构建暴露的坑）
1. **系统识别**：tcl.m4 的 `SC_CONFIG_SYSTEM` 用 `uname` 判系统，HarmonyOS 不被识别 →
   "Can't figure out how to do dynamic loading or shared libraries"。修：
   - configure 传 `tcl_cv_sys_version=Linux-6.6`（覆盖缓存，走 Linux 分支）；
   - build() 造 `uname` shim 报 Linux/aarch64 放 PATH 前（configure.ac 有几处直接调 uname）。
2. **umask 077（E011）**：HMDFS 上临时目录归服务 uid，`config.status` 硬编码 `(umask 077 && mktemp)`
   → 构建进程读不了 subs*.awk（Permission denied）。修：build() 把源码树内**所有** configure
   （主 + 10 余捆绑子包）的 `umask 077` 文本替换成 `022`（`os.umask` 覆盖不了子壳里的显式 077）。
3. **只建核心**：`make binaries libraries` + `install-binaries install-libraries`，**跳过 packages**
   （可选扩展 thread/itcl/tdbc/sqlite）——tk/dlopen 用不到，且其构建期跑刚建的 tclsh 做打包、
   加载不到自产 libtcl9.0.so 而失败。原 build-ohos.sh 也只出核心。
4. **`--disable-zipfs`（关键，关系代码签名）**：`ZIPFS_BUILD=1` 时 Makefile 会在链接后
   `cat 脚本库zip >> libtcl9.0.so`（尾拼），**尾拼数据破坏链接器自动代码签名** → 独立 dlopen 被
   XPM 判 Permission denied（ML-0003）。关掉 zipfs 后 libtcl9.0.so 保持**干净 ELF**、链接器自签有效，
   **无需配方再显式重签**（与 mac 等其它包一致）。脚本库改以**散文件**装 `lib/tcl9.0`，运行期靠 `TCL_LIBRARY`。

## 产物
- `lib/libtcl9.0.so`（动态库，干净 ELF + 链接器自签）
- `bin/tclsh`、`lib/tclConfig.sh`、`lib/libtclstub.a`、`include/*.h`、`lib/tcl9.0/`（散脚本库）

## 验证
- test_package：`clang` 编译 → `dlopen`（注入全路径）libtcl9.0.so + `dlsym Tcl_CreateInterp` 并调用 → OK（真机+CI）。
  - R34 破坏性反向验证（L1e）：移走 bin/lib/include 后 test 失败 → test 确实依赖 tcl ✅
- conan-verify：G0-G4 + L2/L4/L5 全部 PASS（2026-07-08）
- CI 本地模拟（W3）：L0 PASS，conan create PASS，L1a/L1b PASS，L1e PASS，L5 PASS
  - L2 smoke test：tclsh9.0 为交互式 shell，--version 进入交互模式（非阻塞，已知行为）
  - L0k：commands.json 已补齐（R38）

## 知识提取
- **tcl 9 的 zipfs 尾拼**：`ZIPFS_BUILD=1` 把脚本库 zip `cat >>` 进 libtcl9.0.so，破坏链接器自签；
  作 conan 动态库分发时用 `--disable-zipfs` 出干净 .so，签名交由工具链链接器自动完成。
- **E011**：umask 077 在 HMDFS 致临时文件权限问题（主 + 子包 configure 都要改）。
- **系统识别**：uname shim + `tcl_cv_sys_version` 缓存覆盖，让 tcl 认 Linux 才建动态库。

---
**状态**：built（conan-verify 全门禁通过 + CI 本地模拟通过，待 CI upload 后标 published）
