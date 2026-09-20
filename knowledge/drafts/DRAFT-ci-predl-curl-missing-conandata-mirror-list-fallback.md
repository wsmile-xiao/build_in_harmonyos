# DRAFT: CI pre-download 段 curl 硬依赖缺位时单 URL 裸奔——conandata.yml 源改镜像列表形态，conan 原生多源下载兜底

> 配套条目：`DRAFT-ci-predl-curl-missing-conandata-mirror-list-fallback.kv`（本 md 与 kv 成对）
> 状态：pending-editor-review（拟提升编号 E7xx，最终由主编确认）
> 首发实现：keditbookmarks 26.04.0，PR #11112 commit `b282b9c51f`
> 同场景佐证：#10999（kxmlgui）/ #10894（kimageformats5）/ #10967（libportal-gtk3）/ #11147（daw-utf-range）/ #11142（gitpython）

## 1. 错误特征（可机器匹配）

```
  [try 1/1.1/3] keditbookmarks-26.04.0.tar.xz ← https://download.kde.org/stable/release-service/26.04.0/src/keditbookmarks-26.04...
  [fail] [Errno 2] No such file or directory: 'curl'
  [try 1/1.2/3] ...
  [fail] [Errno 2] No such file or directory: 'curl'
  [try 1/1.3/3] ...
  [fail] [Errno 2] No such file or directory: 'curl'
  [WARN] Failed to pre-download keditbookmarks-26.04.0.tar.xz, will rely on conan's download
  [done] No files pre-downloaded
```

- error_signature：`[fail] \[Errno 2\] No such file or directory: 'curl'|\[WARN\] Failed to pre-download .*, will rely on conan's download`
- **识别要点**：失败发生在 conan create **之前**的 `[step] Pre-download` 段；镜像列表（如 gh-proxy+github 双源）会连刷两轮 `[WARN]`；后续 conan create 若上游源恰好可达则绿（制造"随机红绿"假象）、限流/不可达则红（常被归为"网络问题"）。

## 2. 根因

`ci/conan/build_and_test.sh` 的 Pre-download 步骤（设计目的：conan get() 对每个 URL 只试一次，先用 `curl -sL --retry 3` 把 tarball 预拉到本地、改写 conandata 为 `file://`，双保险）：

```python
result = subprocess.run(
    ['curl', '-sL', '--retry', '3', '--retry-delay', '10',
     '--connect-timeout', '30', '--max-time', '300',
     '-o', dest, '-w', '%{http_code}:%{size_download}',
     mirror_url],
    capture_output=True, text=True, timeout=360)
```

- **curl 是外部可执行依赖**：部分 buildbot worker 不装 curl，`subprocess.run(['curl',...])` 直接抛 `FileNotFoundError`；
- try 1/2/3 三轮重试**命中同一异常**（不是网络抖动，重试无意义）；
- pre-download 全败后回退 conan 自带下载器，但 conandata.yml 若是**单条 url**，conan source() 没有镜像回退——上游源 429 限流（download.kde.org 高频）时直接红；
- 与配方质量无关：**同一 PR 撞到有 curl 的 worker 就绿、撞到没有的就靠运气**——六件 PR 同日实测（#11112/#10999/#10894/#10967/#11147/#11142 全部命中 `[Errno 2] No such file or directory: 'curl'`）。

## 3. 解法（配方侧自愈：镜像列表形态）

conandata.yml 的 `sources.url` 从单条字符串改为列表（官方第一 + 镜像第二）：

```yaml
# 修改前（单 URL，conan 下载器无回退）：
sources:
  url: "https://download.kde.org/stable/release-service/26.04.0/src/keditbookmarks-26.04.0.tar.xz"
  sha256: "ebaff000124ea716fe39d7de89049ce5fde0d8da64432c0ec87e9279bf053bd2"

# 修改后（镜像列表，conan 逐源尝试）：
sources:
  url:
    - "https://download.kde.org/stable/release-service/26.04.0/src/keditbookmarks-26.04.0.tar.xz"
    - "https://mirrors.nju.edu.cn/kde/stable/release-service/26.04.0/src/keditbookmarks-26.04.0.tar.xz"
  sha256: "ebaff000124ea716fe39d7de89049ce5fde0d8da64432c0ec87e9279bf053bd2"
```

- conan 2 对 `url` 列表**原生按序尝试**，任一源成功即用（sha256 校验不变）；
- pre-download 段把成功的 URL 改写 `file://` 时列表内其他 URL 不受影响（提取/替换按完整 URL 串）；
- 镜像选择：KDE → `mirrors.nju.edu.cn/kde`（KDE 官方镜像站列表成员）；GitHub → `gh-proxy.com/` 前缀（CI `get_mirror_list()` 同款逻辑）。

**验证链**：#11112 修前 #51089（curl×3 fail → conan 单源 429 红）→ 修后 commit `b282b9c51f` → #51382 全绿（L0 结构/L1 测试执行全过）。

## 4. 降级方案

1. 换 worker 重试：撞到有 curl 的机器 pre-download 成功——治标不治本，随机红绿依旧；
2. 框架级修复：pre-download 段改用 python urllib 实现、或 `shutil.which('curl')` 探测降级——属 CI 基础设施改动，**须走单独框架 PR**（W2 原子性，适配 PR 不得混入 ci/ 改动）；
3. 等待上游限流窗口重试——不可靠。

## 5. 红线

- ❌ 不要为绕过 curl 缺失在 conanfile.py build() 里调 wget/python 下载——L0o 门禁拦截（uses_external_curl）；
- ❌ 不要把镜像源写成第一条（R39：官方源第一、镜像兜底第二）；
- ✅ sha256 保持官方源校验值不变（镜像源文件与官方一致）；
- ✅ 提交前 `grep -A4 "sources:" conandata.yml` 确认列表形态。

## 6. 覆盖判断（查重展开）

| 既有条目 | 覆盖内容 | 本条增量 |
|---|---|---|
| E017（GitHub 下载慢/超时→ghfast 镜像） | 单 URL 场景的镜像**替换**方案 | 本条是**列表形态**（官方+镜像并存），且聚焦 CI pre-download 段 curl 缺失的交互——E017 时代 pre-download 段尚不存在该问题 |
| E299（conan source 失败分层诊断） | source() 失败的分类框架（网络/URL/sha256/403/404） | 本条给出**配方侧可执行修法**（多源列表），并补上"CI pre-download 回退 conan 下载器"这一环境上下文 |
| E333（pre-download 正则截断 PyPI 连字符 URL） | 同 pre-download 段的**正则缺陷**根因 | 本条根因是 **curl 可执行缺失**——正则提取 URL 正常、下载器不存在；触发条件/修法完全不同 |
| DRAFT-8960-raqm/jwt-cpp/ring-span-lite（pre-download URL 提取污染） | 同段第三类坑：注释 URL 被提取后 file:// 替换污染真源码 URL | 本条是第四类：**下载器本体缺失**；四条合起来构成 pre-download 段的完整故障族谱 |

## 7. 复现方法（自含）

- 观测：任一 open PR 评论里 grep `No such file or directory: 'curl'`（六件 PR #11112/#10999/#10894/#10967/#11147/#11142 均有实锤日志）；
- 本机模拟 worker 缺 curl：`PATH=$(echo $PATH | tr ':' '\n' | grep -v curl | paste -sd:) zsh ci/conan/build_and_test.sh` 的 pre-download 段（或直接读 ci/conan/build_and_test.sh 第 1167-1300 行的 subprocess.run(['curl'...) 调用）；
- 验证修法：conandata 改列表形态后 `conan create . -pr ohos-aarch64 --build=missing`——conan 按序尝试官方→镜像，任一成功即过。

## 8. 证据链

- 修前红：#11112 构建 #51089（2026-09-19 13:32，curl×3 fail + conan 单源下载失败 L1 fail）；#10999（14:16/15:08 两轮）、#10894（13:51）、#10967（15:54/16:53/18:51 三轮）、#11147（16:40）、#11142（16:14/17:37）同款；
- 修后绿：#11112 #51382（17:43，全步骤 ✅）；#10999（16:06 绿）、#10894（15:29 绿）、#11147（17:42 绿）、#11142（18:47 绿）先后同款修法/重试转绿；
- 修法 commit：`b282b9c51f`（keditbookmarks conandata.yml 单 URL → 官方+nju 镜像双源列表）。
