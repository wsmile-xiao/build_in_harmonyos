# DRAFT-20005: GN 项目在 OHOS 自举后仍缺源码树 `bin/gn`；DEPS/depot_tools 依赖树须手工镜像化

> 适用：任何用 **GN（generate-ninja）** 的工程在 OHOS 上构建。本文只覆盖 perfetto 先例**未覆盖**的两处差异：
> ① 自举出来的 gn 还要落到工程约定的 `bin/gn`；② 依赖获取走 `DEPS`+depot_tools 而非脚本化 install-build-deps。

## 症状

1. `gn gen` 成功、大部分目标编译正常，但某一个 action 突然失败：

```
FAILED: gen/skia.h
Command: python ../../gn/find_headers.py <src>/bin/gn <src>/ gen/skia.h <include dirs...>
FileNotFoundError: [Errno 2] No such file or directory: '<src>/bin/gn'
```

2. `source()` 阶段大量 `*.googlesource.com ... Read timed out`（OHOS 侧该域全系不可达）。

## 根因

- **① `bin/gn` 是工程内的「约定路径」**：GN 工程常用一个 wrapper/action 直接调用
  **源码树内**的 `//bin/gn`（上游由 `bin/fetch-gn` 之类脚本下载并放好；tarball 里没有）。
  自举出来的 gn（`out/gn`）不会自动出现在那里 → action 找不到可执行文件。
- **② 依赖树形态不同**：perfetto 把第三方 URL 写在 `tools/install-build-deps` 脚本里；
  skia 写在 **`DEPS`** 里交给 depot_tools 的 `gclient`/`tools/git-sync-deps` 拉取，
  `use_relative_paths = True` 时落点为 `<root>/third_party/externals/<name>`。OHOS 上只能
  逐条换镜像。

## 最小复现

```sh
# A：自举后不拷 bin/gn
$GN gen out/ohos && ninja -C out/ohos <某个依赖 gen/skia.h 的目标>
# → FileNotFoundError: <src>/bin/gn
```

## 最终方案

### A. 把自举 gn 落到 `bin/gn`

```sh
python3 build/gen.py --no-last-commit-position
printf '…LAST_COMMIT_POSITION "0 (unknown)"…' > out/last_commit_position.h
ninja -C out                                   # → out/gn（musl + .codesign）
cp out/gn <src>/bin/gn && chmod +x <src>/bin/gn
```

配方里对应 `shutil.copy2(gn, <src>/bin/gn) + os.chmod(0o755)`。

### B. DEPS → 可达镜像（逐条核对同一 commit SHA）

镜像映射经验（codeload `-I` 返回 200/404 即可探测「该仓库是否含此 SHA」）：

| DEPS 里的源 | 可用镜像 |
|---|---|
| `chromium.googlesource.com/external/github.com/<owner>/<repo>` | GitHub 同名 `<owner>/<repo>` |
| `android.googlesource.com/platform/external/<x>` | `msft-mirror-aosp/platform.external.<x>`（`aosp-mirror` 常无同名仓） |
| `chromium.googlesource.com/chromium/{src,deps}/<x>` | `msft-mirror-aosp/platform.external.<x>`（同名 SHA 命中） |
| `skia.googlesource.com/<x>`（自建仓） | 社区镜像，如 `libgifcodec` → `GoogleDepends/libgifcodec` |

```sh
# 探测：同一 SHA 在哪个镜像里存在
curl -s -o /dev/null -w '%{http_code}\n' -I \
  https://codeload.github.com/<candidate>/tar.gz/<SHA>     # 200 = 命中
```

配方侧：整张表放 `conandata.yml`，`source()` 循环 `get(url, sha256, filename, destination=third_party/externals/<name>, strip_root=True)`。

## 适用边界与坑

- **适用**：GN 工程；依赖获取走 `DEPS`+depot_tools；`*.googlesource.com` 不可达的环境。
- **坑 1**：`DEPS` 的键名（`third_party/externals/<n>`）**不等于**镜像仓库名，落点要按 DEPS 键名。
- **坑 2**：部分依赖只在某个 `skia_use_*` 开关打开时才被引用（如 brotli 仅 freetype woff2 用）。
  显式关掉开关即可省一份依赖，但**不要依赖默认值**（默认可能在 dev build 下是开的）。
- **坑 3**：GN 工程可能带 fork 注入脚本（skia 的 `gn/xamarin_inject_compat.py` 会在 gn gen 期
  **原地改写** externals 源文件）→ 补丁基线要在 gn gen **之前**取。
- **不适用**：CMake/autotools 工程（走各自依赖发现机制）。
- **与 perfetto 草稿的关系**：perfetto 覆盖「上游预编译 gn 是 x86/glibc 且无 `.codesign` → 必须源码自举」；
  本文补其未覆盖的 `bin/gn` 约定与 `DEPS` 依赖树镜像化方法。两者互补，不重复。
