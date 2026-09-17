# DRAFT-lz4-1.10.0.3：真机工具链迁移致 profile 失配与远端作业三坑（2026-09）

> Contributor: gcw_6YxinkyD | Status: Draft | Updated: 2026-09-10
> Source: PR !9359 【知识库扩展】feat(lz4): 1.10.0.3 编译完成（真机 frp 隧道）

## 背景

2026-09 起真机（frp 隧道设备 / 10.62.134.118）的工具链布局发生迁移：
`clang` / `clang++` / `cmake`（4.1.2 vanilla）已位于
`/storage/Users/currentUser/usr/local/bin`，`/data/service/hnp/bin` 下仅剩
git 系列（早期会话记录该目录含 clang/make/ar，已过时）。共享
`~/.conan2/profiles/ohos-aarch64` 的 `compiler_executables` 仍指向 CI 的
`/data/service/hnp/bin/clang`，与真机现状失配。

## 坑 1：profile 编译器路径失配 → test_package cmake.configure 失败

### 现象

```text
-- The C compiler identification is unknown
CMake Error at CMakeLists.txt:2 (project):
  The CMAKE_C_COMPILER:
    /data/service/hnp/bin/clang
  is not a full path to an existing compiler tool.
```

主包构建（纯 Makefile，`CC=clang` 走 PATH）不受影响，**只在 test_package
的 CMakeToolchain 阶段**爆出——`tools.build:compiler_executables` 写入
conan_toolchain.cmake 的绝对路径不存在。

### 修复（隔离作业内修正，勿动共享配置）

```sh
CH="$BASE/conan-home"
cp -r "$HOME/.conan2/profiles" "$CH/profiles"
sed -i "s|/data/service/hnp/bin/clang|/storage/Users/currentUser/usr/local/bin/clang|g" \
    "$CH/profiles/ohos-aarch64"
```

共享 `~/.conan2` 是他人共用的（历史上其他分支有未提交依赖），只在隔离
CONAN_HOME 的副本上修。附带：vanilla cmake 对 `CMAKE_SYSTEM_NAME=HarmonyOS`
打 "System is unknown" 警告但 configure 继续，非致命。

## 坑 2：构建脚本从 payload tar 重新解包，热修被回滚

### 现象

改了设备上 `payload/conanfile.py` 重跑脚本，日志显示 make 命令仍是旧版
（SHELL= 仍带硬编码路径）。

### 根因

脚本第 1 步 `tar xzf lz4-payload.tar.gz` 每次运行都会用 tar 里的旧文件
**覆盖**被热修的 payload 副本，随后 `cp` 到 PKG 目录的自然也是旧版。

### 修复

热修必须改打包源并重打 tar（或直接改 PKG 目录且脚本不再走解包步骤）；
验证生效看 conan 日志的 `RUN: make ...` 实际命令行，不要只看退出码。

## 坑 3：ssh 远端后台启动的竞态把脚本截成 0 字节

### 现象

`ssh 'cat > script && nohup sh script > log 2>&1 & echo started' < local.sh`
返回 started，但设备上 script 为 0 字节、log 全空。

### 根因

`&` 把整条 `cat > … && nohup …` 链后台化，`echo` 立即返回后 ssh 会话即
关闭，stdin 传输被截断/杀掉。

### 修复

传输与启动分两次 ssh 调用：第一次 `cat > f && sed -i 's/\r$//' && wc -c f`
（前台、带字节数校验），第二次 `nohup sh f > log 2>&1 &`。

## 附带

- `grep "A\|B"` 在真机 toybox grep 下不按预期交替（BRE 无 `\|`），用
  `grep -E "A|B"`；
- 真机隔离作业基线：CONAN_HOME 独立目录 + `global.conf` 写
  `core.download:download_cache` 与 `tools.build:jobs=1` + TMPDIR 指向
  `$HOME/tmp`（/tmp 只读）+ 源码预置 `<dl>/s/<sha256>` 离线。

## 适用范围

一切在真机做隔离 Conan 作业的适配（尤其 CMake 类 test_package）；复用
botan3/chaiscript 会话模板但设备已迁移的场景；远端脚本分发与热修流程。

## 验证

真机 lz4 1.10.0.3（同源）：profile 修正后 test_package cmake.configure 通过，
static + shared 双轮全绿（详见 PR !9359 与
archives/l/lz4/1.10.0.3/notes.md 四B 节）。
