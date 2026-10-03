# E902 — conandata.yml 注释里的 URL 前缀撞车导致 CI Pre-download 报 NotADirectoryError

## 错误特征

本地 `conan create` 直连官方源**完全正常**（rc=0），
但走 CI 门禁（`ci/conan/build_and_test.sh`）时在 `source()` 阶段失败：

```
ERROR: <pkg>/<ver>: Error in source() method
    NotADirectoryError: [Errno 20] Not a directory:
    '/.../.build-cache/predl_cache/<hash>_<something>/archive/refs/tags/<X>.tar.gz'
```

预下载步骤本身却显示成功（`[ok] <X>.tar.gz (8KB) via mirror 1`），
并提示 `Pre-downloaded N files, conandata.yml updated to file:// URLs`。

## 触发条件

- `conandata.yml` 的**注释行**里出现了一个以 `https://` 开头的 URL，
  且该 URL 是 `sources.url` 的**字符串前缀**。
- 典型形态（GitHub tag 归档 URL 天然是多段路径，极易命中）：

```yaml
sources:
  url: "https://github.com/atsb/worklog/archive/refs/tags/Worklog-2.1.tar.gz"
# 注释里写了：
#   upstream : https://github.com/atsb/worklog      ← 前缀！
```

- 走 CI 门禁才复现；本地直连不复现。

## 根因分析

`ci/conan/build_and_test.sh` 的 **Pre-download** 阶段（纯 shell + 内嵌 python）：

1. 用正则 `(?:^|\s)(?:url:?\s*)?["\']?-?\s*(https?://[^\s"\']+)` 扫描 conandata.yml
   里的**所有** http(s) URL —— **注释行一并命中**。
2. 逐个 `curl` 下载到 `predl_cache/{md5前8}_{URL末段文件名}`。
3. 用 **`content.replace(url, f'file://{local_path}')`** 做纯文本整体替换。

第 3 步是致命的：`str.replace` 替换**所有出现位置**。由于注释里的
`https://github.com/atsb/worklog` 是真实 source URL 的前缀，替换后真实 URL 被截断为：

```
file:///.../predl_cache/<hash>_worklog/archive/refs/tags/Worklog-2.1.tar.gz
                ^^^^^^^^^^^^^^^^^^^ 中间目录并不存在 → NotADirectoryError
```

注释里那个 URL 本身还会被误当成一个"源码 URL"去下载（拿到 55KB 的 HTML 仓库页），
日志里出现 `[try 1/2.1/3] worklog ← ...` 这种没有扩展名的条目，可作为识别信号。

## 解决方案

### 推荐方案

**conandata.yml 内只允许出现 `sources` 段那一个以 `https://` 开头的 URL。**
注释里引用仓库地址时**去掉 `https://` 前缀**：

```yaml
#   仓库    : github.com/atsb/worklog        ← 不带 scheme，正则抓不到
sources:
  url: "https://github.com/atsb/worklog/archive/refs/tags/Worklog-2.1.tar.gz"
```

这样正则既抓不到注释 URL，注释 URL 也不可能是 source URL 的可替换前缀。

### 备选方案

无（该行为属框架脚本的既有约定，不应改 `ci/`；本条只约束归档侧写法）。

### 禁止做法

- ❌ 修改 `ci/conan/build_and_test.sh` 的替换逻辑（框架文件，红线）。
- ❌ 把 `file://` 或 `gh-proxy.com` 镜像 URL 提交进 conandata.yml：
  CI 的 mirror-fallback 会在退出时把 conandata.yml 还原成**已被镜像改写**的版本
  （`PREDL_BACKUP` 备份的是镜像改写后的内容），本地跑完门禁后必须
  `cp conandata.yml.orig conandata.yml` 还原再提交，否则官方源丢失。
- ❌ 靠"注释里写完整 URL 显得更规范"——正是这个习惯触发本条。

## 验证

判据是「**能被 Pre-download 正则抓到的** http(s) URL 只有一个」，而不是
「文件里出现 `https://` 的行只有一行」——后者会把解释性注释一并算进去而误报。

```bash
# 权威判据：复刻 CI Pre-download 的抓取正则，命中的 URL 必须恰好 1 个
#           （即 sources.url 本身；注释里的仓库地址因不带 scheme 不会被命中）
grep -oE "(?:^|[[:space:]])(?:url:?[[:space:]]*)?[\"']?-?[[:space:]]*(https?://[^[:space:]\"']+)" \
     archives/<l>/<pkg>/<ver>/conandata.yml | wc -l
# 期望：1

# 辅助确认没有镜像 / 本地路径被提交进来
grep -nE 'file://|gh-proxy' archives/<l>/<pkg>/<ver>/conandata.yml || echo "clean"
```

> 注意：若注释里写成 `（刻意不带 https:// 前缀）` 这类**说明性文字**，
> `grep -cE 'https?://'` 会额外命中该行而给出 >1 的假警报；
> 但因为 `//` 之后紧跟空格/非 URL 字符，CI 的抓取正则（要求 `//` 后至少一个非空白字符）
> 不会命中，故**不影响 CI 行为**，只需用上面的权威判据复核。

## 关联条目

- 实证：worklog 2.1（`archives/w/worklog/2.1/conandata.yml`）——
  首次跑 CI 门禁即命中，改为 `github.com/atsb/worklog` 后门禁 RC=0。
- 相关：CI 门禁 L0i 依赖发布检查（R36）、mirror fallback 行为。
