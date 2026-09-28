# DRAFT-dmenu-5.4-downloaded-deps-codesign-device-enforced

> 设备强制 ELF 签名拦截 conan 下载依赖库：消费者测试运行期 dlopen EPERM，
> 本机 binary-sign-tool selfSign 重签缓存即放行。

## 一句话

OHOS PC **设备侧**对共享库按 `.codesign` 签名做内容级放行（**CI worker 不强制**）：
conan 下载进本机缓存的依赖库若签名不被本机信任，消费者可执行文件运行期加载它们时报
`Error loading shared library libX.so.N: (needed by …)`（同目录自编库却能加载），
直接 exec 该库报 `Operation not permitted`；按 E077 四步对本机缓存内的被拦库
去旧段 + `binary-sign-tool sign -selfSign 1` + chmod 即放行。

## 可复现症状（dmenu 5.4 实测，2026-09-22 DS-33）

1. conan-verify G2 编译/链接/安装全过，test_package 运行期刷屏：
   `Error relocating …/bin/dmenu: FcCharSetCreate: symbol not found`（Xft/fontconfig 符号）
2. 补上 `LD_LIBRARY_PATH=<全部依赖 lib 目录>` 后症状变为：
   `Error loading shared library libfontconfig.so.1: (needed by …/bin/dmenu)`——
   但**同一次运行里 libX11.so.6 从同级目录正常加载** ⇒ 不是路径问题，是文件级拦截
3. 交叉印证：`./libfontconfig.so.1` 直接执行 → `Operation not permitted`；
   `llvm-readelf -S` 见三库 `.codesign` 段俱在（占位段/他机签名不被本机信任）

## 根因

设备加载器按内容哈希/签名放行 ELF（经验汇总既有实测：设备强制、CI 不强制，见
catch2/2.13.10-r0 先例）。本机 clang 新链接产物自带 ad-hoc 签名 → 直接可加载；
制品仓下载库的签名来自他机构建链 → 不被信任 → `mmap PROT_EXEC`/打开被拒，
musl 层面表现为"库不存在"或"符号全缺"两种迷惑形态。

## 最小修复（对本机任务缓存，非制品仓、非配方）

```sh
llvm-objcopy --remove-section .codesign <被拦库>      # 旧段不除，签名时报 already exists
LD_LIBRARY_PATH= binary-sign-tool sign -inFile <lib> -outFile <lib> -selfSign 1
chmod a+x <lib>                                        # 签名后权限归零，必须恢复
```

- 只动本机 `CONAN_HOME` 缓存副本（可重建、可丢弃），配方与制品仓零改动；
  CI worker 不强制签名，本操作对 CI 无影响也无需复刻。
- dmenu 实测：36/36 制品 .so 重签后，`LD_LIBRARY_PATH=<conan lib 目录> dmenu -v`
  输出 `dmenu-5.4`（rc=0）；test_package 4/4 PASS（conan-create.log）。

## 判别要点（防止误诊）

| 误诊 | 判据 |
|---|---|
| "依赖没装/路径不对" | 同一 LD_LIBRARY_PATH 里自编库能加载、下载库不能 ⇒ 文件级 |
| "库缺符号（误修符号/版本）" | `Error relocating ... symbol not found` 只是加载失败的下游表现 |
| "E077 已覆盖" | E077 是配方**自身产物**打包后重签；本条是**依赖侧制品**在消费者测试运行期被拦 |

## 适用面 / 边界

- 适用：application/tool 包 + DT_NEEDED 指向 conan 下载共享库 + 设备上真实执行消费者测试。
- 不适用：纯库包；CI 侧验证；依赖带 `.a` 可全静态链接的场景（优先静态链接绕开签名议题）。
- 关联：E077（自身产物重签，工具链同源）、E083（JDK native 库自签）、
  catch2 2.13.10-r0（CI 不强制的实证数据点）。
