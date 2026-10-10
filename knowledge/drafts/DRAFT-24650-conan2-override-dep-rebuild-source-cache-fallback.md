# DRAFT-24650：conan 2 override 会改掉被覆盖依赖的 package_id（制品仓 binary 失配→源码重建），其官源不可达时用 conan 源缓存按 sha256 预取官方镜像兜底

> Contributor: Rz114514 | Status: Draft | Updated: 2026-10-08
> Source: pangomm 2.46.5 适配 HarmonyOS PC（本 PR）
> 对应：`knowledge/drafts/DRAFT-24650-conan2-override-dep-rebuild-source-cache-fallback.kv`
> 关联：`DRAFT-13572-pangomm-2.46-legacy-mm-abi-line-matching`（上游相邻环节）

## 问题

在同一 conan 2 图里，当两个依赖各自**精确钉死**同一包名的不同版本时，conan 2 不会自动归一化，必须由上层 recipe 显式 `override`。例如 GNOME mm 家族：

| 依赖 | 钉死的 libsigc |
|------|----------------|
| `glibmm/2.66.9`（glibmm-2.4 旧 ABI 线） | `libsigc/2.10.8` |
| `cairomm/1.14.5.1`（cairomm-1.0 旧 ABI 线） | `libsigc/2.12.1` |

不 override 时 conan 直接报：

```
ERROR: Version conflict: Conflict between libsigc/2.10.8 and libsigc/2.12.1 in the graph.
```

**关键认知（本条目增量）**：`override` 不只是"选一个版本"。被覆盖侧依赖（glibmm）的 `package_id` 里嵌着 libsigc 的 `package_id`，所以 override 会**改变 glibmm 的 package_id**。此时：

- `conan download glibmm/2.66.9` 成功（recipe 与某个 binary 都拿得到）；
- 但 `conan graph info … --format=json` 里该节点 `binary: Missing`；
- `conan create --build=missing` 于是**回落源码构建**；
- 若该依赖的 conandata 只写了官方源（glibmm 只有 `download.gnome.org`）而本机不可达：
  `Error in source() method … Connection reset by peer`（`Max retries exceeded`）。

即"依赖已发布" ≠ "该 package_id 有可用 binary"。这是把 `--build=missing` 从"正常兜底"变成"真实阻塞"的分界线。

## 诊断

```sh
conan graph info . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --format=json | python3 -c "
import json,sys
for v in json.load(sys.stdin)['graph']['nodes'].values():
    print((v.get('binary') or '?').ljust(10), v.get('ref') or v.get('name'))"
```

pangomm 2.46.5 实测输出（节选）：

```
?          pangomm/2.46.5
Missing    glibmm/2.66.9        ← override 导致 binary 失配，需源码重建
Cache      glib/2.84.0.1
Download   libsigc/2.12.1
Download   cairomm/1.14.5.1
Cache      cairo/1.18.4
Cache      pango/1.50.14.1.1
...
```

`Missing` 的节点就是"必须重建、且其源码必须拿得到"的依赖。

## 适配口径

1. **先判是否真需重建**：graph 看 `binary` 字段；`Missing` 才谈源码获取。
2. **不改依赖的 recipe/conandata**（越权 + R39/PF7 黑名单风险），改用 conan 自带的源码下载缓存：

```sh
sha=5a026e5602085307c7dcb72b71b07261c40f80914277bef5f8d7f2ecab739bec   # 依赖 conandata 里的 pin
curl -L "https://mirror.nju.edu.cn/gnome/sources/glibmm/2.66/glibmm-2.66.9.tar.xz" -o /tmp/dep.tar.xz
echo "$sha  /tmp/dep.tar.xz" | sha256sum -c -          # 逐字节校验等于 recipe pin
cache="$(conan config get core.sources:download_cache)"; mkdir -p "$cache/s"; cp /tmp/dep.tar.xz "$cache/s/$sha"
conan create <pkg-dir> -pr:h=<p> -pr:b=<p> --build=missing
```

   命中后 conan 日志出现 `Source ... retrieved from local download cache`，source() 不再触网。
   （`core.sources:download_cache` 未配置时用默认 backup sources 目录；镜像必须是**官方镜像**
   —— GNOME 项目用 `mirror.nju.edu.cn/gnome/...`，不得用 gh-proxy/ghfast/cnb.cool 等平台黑名单域。）

3. **兜底**：官方镜像也不可达时，反向 override 到另一侧（让可获取源码的那个依赖被重建）；
   两侧都拿不到且联网窗口内无解 → 按 R36/R41 如实上报 `dependency_missing` / `env_unsupported`，
   **禁止**用 dummy 包、伪造 `.ci-result.json`、`--build=*` 全量重建来掩盖。

## 与已有知识的关系

- `DRAFT-13572-pangomm-2.46-legacy-mm-abi-line-matching` 解决"override **到哪个版本**"（按 pc 名反查 ABI 线）；
- 本草稿解决"override **之后**被覆盖依赖要重建、源码怎么合法拿到"。
- 官方相似度工具（`ohc-run.py draft-review`）对正式条目比对：最高相似 E538 = 0.20，建议 `create`；
  E538 只覆盖"依赖链解析/发布 binary 一致性"，未覆盖"override → package_id 变化 → 依赖源码重建 → 源缓存兜底"这一组合环节。

## 实证（本 PR）

- 平台：HarmonyOS PC aarch64（clang 15 / libc++ / meson）
- 现象：override 后 `glibmm/2.66.9` binary Missing → `--build=missing` 触发源码重建 →
  `download.gnome.org` `Connection reset by peer`，`conan create` 首次失败；
- 处置：官方 GNOME 镜像预取同 sha256 tarball 入源缓存；
- 结果：`conan create … --build=missing --build="pangomm/*"` **exit=0**（glibmm 重建 + pangomm
  干净重建 27s，meson compile 30/30），test_package 消费者 4/4 + 鸿蒙特有 14/14 全过。
