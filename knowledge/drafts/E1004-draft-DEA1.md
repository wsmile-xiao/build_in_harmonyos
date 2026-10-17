# E1004 — 上游无 git tag 的库：版本映射与官方 commit 归档固定

## 错误特征
- 以 `v3.8`/`3.8`/`v3.8.0` 等猜测 tag 探测 codeload 归档 URL：全部 HTTP 404。
- GitHub API 与 jsdelivr data API 返回空 tags 列表。
- 上游 README 自述"最新版本即 master 单文件"，无 release 流程。

## 触发条件
- 上游仓库不发布 git tag/release（无版本管理流程）
- Conan registry 亦无该版本可解析
- 任务/调度侧给出一个"版本号"，但其语义需从源码内声明反推

## 根因分析
版本号来源与上游版本体系可能脱节。以 lazycsv 为例：任务版本 3.8 实际对应根 CMakeLists.txt
的 `cmake_minimum_required(VERSION 3.8...3.20)`（CMake 最低版本），而上游 `project(... VERSION
1.2.0)` 才是库自身版本。若直接用猜测 tag 拼归档 URL 必然 404；必须固定到官方 commit 归档。

## 解决方案

### 推荐方案
1. 确认上游无 tag：`git ls-remote --tags <upstream>` 为空 + 多个候选 tag 的 codeload 404。
2. 取官方 master/指定 commit SHA（lazycsv=6c36a9d6），conandata sources.url 固定
   `https://github.com/<owner>/<repo>/archive/<sha>.tar.gz`（官方主机，重定向 codeload）。
3. `curl -sSL <URL> | sha256sum` 流式实测 SHA-256 写入 conandata（零落盘亦可核验）。
4. notes.md/manifest 明确记录版本语义来源与版本映射，避免后续误判。

### 禁止做法
- ❌ 不用 file://、本地缓存、.build-cache、predl_cache、执行端绝对路径
- ❌ 不用 ghproxy/ghfast 等代理改写地址作为 conandata 官方源（R39；CI 自带镜像 fallback）

## 验证
```bash
git ls-remote --tags https://github.com/ashtum/lazycsv     # 空输出 → 无 tag
curl -sSL https://codeload.github.com/ashtum/lazycsv/tar.gz/6c36a9d66be1e652b0c06d4e34fb053b93caf0ff | sha256sum
# → 19bc1673d9a60b82ed71f3ae8cfaa36105c15d6f6f2dfa496ca8d2386f9c573f（与 conandata 一致）
```

## 关联条目
- similar_to: DRAFT-E569-codeload-direct-url-bypass-302（同为 codeload/commit 归档下载链路，
  但其焦点是 CI worker 缺 curl 时 302 重定向链；本条焦点是无 tag 版本溯源与官方源固定）、
  E103（bump-cmake-minimum-version，同为 cmake_minimum_required 相关但方向相反）
- 真题佐证: lazycsv 3.8 R02（archives/l/lazycsv/3.8，manifest.yaml version_notes）