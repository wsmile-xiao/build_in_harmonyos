# DRAFT-ohos-git-clone-source-download — conan source() 用 git clone 替代 get() 下载

> Contributor: ohpcd / AtomCode | Status: DRAFT | Updated: 2026-09-05 | Severity: 🔴 blocking
> Source: libapparmor 5.0.0（PR #8292）CI conan create 下载阶段失败

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|----------|---------|--------|--------------------------|
| E372 | 已收录 | 同族：worker 无 curl + Python SSL 不可用；修法为**权威 HTTP 镜像 fallback**（官方 HTTPS 优先 + distfiles.* HTTP 镜像在后） | 本 skill 是 **git clone 替代**（git 自带独立 ssl）：当上游无 distfiles 权威 HTTP 镜像（如 gitlab.com 源）时，E372 镜像方案不可用，git clone 是唯一直接解法；且本 skill 记录 target 子目录、--branch 免 checkout、源码路径同步、sha256 保留等**实操细节**（E372 未覆盖） |
| DRAFT-ohos-autotools-maintainer-noregen | draft（姊妹条目） | 同 PR 的 maintainer 再生成禁用（构建阶段） | 本 skill 是**下载阶段**前置问题；两者构成 libapparmor CI 适配链的两段 |

**撞车判定**：全库查证 `git clone.*替代.*get()`（0 命中）、`Git.clone.*source()`（0 命中）。E372 覆盖 HTTP 镜像路径，本 skill 覆盖 git clone 路径，问题层相同但**修法不同**（git clone 无镜像可用时的直接替代），作为 E372 姊妹条目申报。

## Scope（何时用）

- CI worker 的 Python **无 SSL 模块**（`SSL module is not available`）且 **无 curl**（`[Errno 2] No such file or directory: 'curl'`）
- conan `source()` 的 `get()`（走 Python urllib）下载 https tarball 失败
- 上游源码在 gitlab.com 等**无权威 HTTP 镜像**的托管平台（E372 的 distfiles 镜像方案不可用）

## Symptom

```
WARN: network: Error downloading file https://gitlab.com/...:
  'Can't connect to HTTPS URL because the SSL module is not available.'
ERROR: libapparmor/5.0.0: Error in source() method, line 45
  get(self, **self.conan_data["sources"], strip_root=True)
  ConanException: Error downloading file ...: 'Can't connect to HTTPS URL because the SSL module is not available.'
```

前置 pre-download 失败（curl 不存在）：
```
[try 1/1.1/3] apparmor-v5.0.0.tar.gz ← https://gitlab.com/...
[fail] [Errno 2] No such file or directory: 'curl'
```

## Root Cause

1. **Python 无 ssl 模块**：CI worker 的 Python 编译时未带 ssl，`urllib` 无法发起任何 https 请求——conan 的 `get()` 依赖 urllib，下载 https tarball 必然失败（与 URL/sha256 正确性无关）。
2. **curl 也不存在**：CI pre-download 阶段（用 curl 预下载到本地 file:// 并改写 conandata）因 curl 缺失而失败，无法绕开 conan 的下载。
3. **E372 镜像方案对 gitlab 源不可用**：权威 HTTP 镜像（distfiles.* 域）多为 GNU/GNOME/kernel 等传统镜像站，gitlab.com 项目 archive 无此类镜像。
4. **git 自带独立 ssl**：`git clone` 的 https 走 git 自身的 ssl 实现（libcurl/openssl），不依赖 Python ssl 模块——是绕过该环境限制的直接途径。

## Recommended Solution

### 主方案：source() 用 Git.clone 替代 get()

```python
from conan.tools.scm import Git

def source(self):
    git = Git(self)
    git.clone(url="https://gitlab.com/apparmor/apparmor.git",
              target="apparmor",                    # 子目录：source_folder 根已有 exports_sources 非空
              args=["--depth", "1", "--branch", "v5.0.0"])
    # --branch 已切到 tag，无需再 checkout
```

关键点：
- **target 必须指向子目录**：`source_folder` 根已有 `exports_sources` 的 patches/（非空），clone 到 `"."` 报 `fatal: destination path '.' already exists and is not an empty directory`。
- **`--branch` 免 checkout**：clone 时已 checkout 到该 tag，后续 `git.checkout(tag)` 会因工作目录/HEAD 状态报错（`fatal: not a git repository` 或重复切换），直接省略。
- **源码路径同步**：build()/package() 中 `libdir = os.path.join(self.source_folder, "apparmor", "libraries", "libapparmor")`。
- **sha256 保留**：conandata.yml 的 sha256 仍保留作源码身份校验（CI L0j 归一化比对用），不因换 git clone 而删除。

### 回退方案

- 按 E372 加权威 HTTP 镜像（官方 HTTPS 优先 + distfiles.* 镜像在后）——仅当上游存在权威 HTTP 镜像时可用。
- 若两者都不可行：报告 CI worker 基础设施阻塞（补装 curl 或修复 Python ssl），不弱化源码完整性。

### 禁止

- `verify_ssl=False` / 非权威 HTTP 镜像 / 移除 sha256——移除完整性保证，可能引入不可信源（E372 同款禁令）。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| libapparmor 5.0.0 | 本 skill 来源 | 覆盖前：CI conan create 下载阶段失败（SSL module not available，curl 缺失）；覆盖后：git clone 拉取成功，conan-verify 全门禁 PASS（G0-G5/L2/L4/L5） |

## 测试覆盖边界

- 通过率口径：source()（git clone）+ build()/make/make install/test_package 全链通过；test_package 1/1。
- 未覆盖：无 git 的 CI 环境（本方案依赖 git 二进制）；gitlab/github 网络不可达的场景。
