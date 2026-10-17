# shadow CI 隔离 job 的 conan-home 缺 ohpcd remote

## Error signature

依赖解析回落 conancenter，命中同名但构建系统不同的配方，随后在源码构建阶段失败：

```text
zlib/1.3.1: Not found in local cache, looking in remotes...
zlib/1.3.1: Checking remote: conancenter
zlib/1.3.1: Downloaded recipe revision cac0f6daea041b0ccf42934163defb20
zlib/1.3.1: Building from source
zlib/1.3.1: Running CMake.configure()
/system/bin/sh: cmake: inaccessible or not found
ERROR: zlib/1.3.1: Error in build() method, line 81
	cmake.configure()
	ConanException: Error 127 while executing
```

## Root cause

`ohos-prepare-isolated-conan-job.sh` 从已有 job 复制 repo 时，新 job 的 `conan-home/remotes.json` 可能只含默认 `conancenter`（无 `ohpcd`）。conan create 解析 `self.requires()` 依赖时只查 conancenter，命中其同名配方（例如 conancenter 的 zlib/1.3.1 用 CMake 构建，而 ohpcd 的 zlib/1.3.1 是 Makefile 配方的预编译包），真机无 cmake，依赖从源码构建失败。

全局 `conan remote list` 显示 ohpcd 已启用也不起作用——隔离 job 使用独立的 `CONAN_HOME`，不继承全局 remote 配置。

## Recommended fix

创建隔离 job 后、跑 runner 前，给 job 的 conan-home 补 ohpcd remote 并禁用 conancenter：

```sh
export CONAN_HOME="$JOB/conan-home"
conan remote add ohpcd https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/
conan remote disable conancenter
conan remote list   # 确认 ohpcd enabled、conancenter disabled
```

## Validation evidence

infgen 3.5 shadow CI（真机 10.62.178.77，job `infgen-3.5-shadow-20260920`）：

- r1：zlib/1.3.1 走 conancenter（CMake 配方），`cmake: inaccessible or not found` 失败。
- 补 ohpcd remote 后：zlib 命中 ohpcd 预编译包 `zlib/1.3.1#2ee7c0ee:6b129b06...`（Makefile 配方，`--static`），不再源码构建。
- r3 全绿：`Build Summary: Total 1, Success 1, Failed 0`，exit code 0。

```text
Requirements
    zlib/1.3.1#2ee7c0eeb8f4dfef8982d0c5c1551a61:6b129b068851896169fae42d399fa922d239ce8a#... - Cache
```

## Notes

- 验证依赖预编译包用 `conan download "<dep>/<ver>" -r=ohpcd`（R35 禁 `conan list` 判断 binary）。
- 不同 repo-source（来源 job）的 conan-home 配置不一致：有的含 ohpcd（如 rgbds job），有的只有 conancenter（如 kleidiai/pasmo job）。创建 job 后先 `grep -c ohpcd remotes.json` 自查，不要假设已有配置正确。
