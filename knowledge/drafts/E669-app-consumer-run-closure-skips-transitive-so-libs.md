# E669-app-consumer-run-closure-skips-transitive-so-libs：application 消费者的运行闭包跳过 DT_NEEDED 传递共享库，musl 报 `symbol not found`

> Contributor: lnav-0.13.2 任务 | Status: Draft | Updated: 2026-09-22
> Source: lnav 0.13.2 适配（feat/lnav-0.13.2）
> 对应：`knowledge/drafts/E669-app-consumer-run-closure-skips-transitive-so-libs.kv`

## 现象

test_package / 任何消费者真跑 `bin/lnav` 时（采信轮 verify-round4–7 连续 4 轮 G2 FAIL）：

```console
A1 FAIL: lnav -V => 'Error relocating .../p/bin/lnav: deflateBound: symbol not found'
A1 FAIL: lnav -V => 'Error relocating .../p/bin/lnav: curl_easy_cleanup: symbol not found'
```

而同一条 `conan create` 的图输出里：

```console
Requirements
    curl/8.15.0.1#... - Cache
    lnav/0.13.2@ohpcd/stable#... - Cache
    tzdata/2026.3#... - Cache
Skipped binaries
    bzip2/1.0.8.2, libarchive/3.8.7, libunistring/1.0, openssl/3.5.6.1,
    pcre2/10.48, sqlite3/3.49.1, xz/5.6.2, zlib/1.3.1.1
```

`bin/lnav` 的 `readelf -d` 只有 4 个 NEEDED：`libarchive.so.13`、`libcurl.so`、
`libc++_shared.so`、`libc.so`——**恰恰是被 Skipped 的 libarchive**；zlib 静态链入
libarchive 后以全局符号**再导出**（`deflateBound` 在 libarchive.so.13 内是
GLOBAL DEFAULT 定义），所以缺的不是 zlib，是 libarchive 的目录。

## 根因

conan 2 给消费者图计算 `necessary packages` 时，传递依赖只在**贡献 runenv**
（包自身 `runenv_info` 有内容，如 curl 的 PATH）或**被依赖方 package_info
访问过 `package_folder`**（如 lnav 的 TZDIR→tzdata）时计入运行闭包，其余全部
`Skipped binaries`。被 skip 的后果有两层：

1. 不进 test_package 的 `self.dependencies.host` —— `test()` 按
   `package_folder` 枚举 `lib/lib64` 注入 `LD_LIBRARY_PATH` 时**拿不到它的目录**；
2. `VirtualRunEnv` 也不为它生成 libdir（组件化包 `cpp_info.libdirs` 还为空，
   双重失效）。

设备 `/system/lib` 下没有同名库兜底（实测无 libarchive/libcurl/libz），musl
加载即报错；符号 provider 还可能不是显而易见的那个库（zlib→libarchive 再导出），
极易误判成「zlib 装错了」。

## 修法（推荐）

test_package 的 `requirements()` 显式声明运行期 .so 直依赖（与配方同版本，去重无冲突）：

```python
def requirements(self):
    self.requires(self.tested_reference_str)
    # DT_NEEDED 指向的共享库必须是直依赖，否则被 Skipped → 不进依赖表
    self.requires("libarchive/3.8.7")
```

`test()` 侧枚举依赖包目录注入（组件化包 cpp_info.libdirs 为空，不能只读 cpp_info）：

```python
for dep in self.dependencies.host.values():
    for sub in ("lib", "lib64"):
        d = os.path.join(dep.package_folder, sub)
        if os.path.isdir(d) and d not in seen:
            seen.add(d); ld_dirs.append(d)
```

实测（lnav 0.13.2）：显式 requires 后 `conan install --format=json` 中
libarchive 由 `Skip` 转 `Cache`、`package_folder` 可用；注入后 `test.sh`
6/6 断言通过（A1 `lnav -V` 正常自报）。

## 兜底

配方 `package_info()` 里访问该依赖 `package_folder` 并
`runenv_info.prepend_path("LD_LIBRARY_PATH", <包目录>/lib)`——与本仓 tzdata 的
TZDIR 同款通道，把包重新拉回运行闭包，所有消费者（含 CI shadow 轮）都受益。

## 禁止

- 为消错误弱化/删除 test_package 断言或让 test 空跑（假绿通道）；
- 把 `LD_LIBRARY_PATH` 指向设备系统库或 `patchelf` 改写 DT_NEEDED——设备与
  CI worker 库形态不同，形成静默错配（R49/E524 共享前缀禁令同族）。

## 复现/验证（设备可直接执行）

```console
# ① DT_NEEDED 清单（本任务包）
RD=/data/service/hnp/bin/readelf
"$RD" -d "$(ls -d /storage/Users/currentUser/.conan2/p/b/lnav*/p | head -1)/bin/lnav" | grep NEEDED
# ② 图算法命中判定：provider 为 Skip 即本条场景
cd /storage/Users/currentUser/tmp/lnav-0.13.2/scratch && \
  /storage/Users/currentUser/usr/local/bin/conan install . \
  -pr:h=/storage/Users/currentUser/ws/worktrees/lnav-0.13.2/ci/conan/profiles/ohos-aarch64 \
  -pr:b=/storage/Users/currentUser/ws/worktrees/lnav-0.13.2/ci/conan/profiles/ohos-aarch64 \
  --format=json | python3 -c 'import json,sys; [print(n.get("ref"),n.get("binary")) for n in json.load(sys.stdin)["graph"]["nodes"].values()]'
```
