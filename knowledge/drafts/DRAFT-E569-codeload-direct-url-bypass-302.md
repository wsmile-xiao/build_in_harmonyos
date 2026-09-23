# E569（草稿）：CI Worker 缺 curl 时 GitHub archive 302 重定向链死——codeload 直链规避

**状态**: pending-editor-review（随 mmkv PR !9693 提交，最终编号由主编确认）

## 一、错误特征（可机器匹配）

CI 失败评论「类别: 未知/网络问题」，完整日志里下载段呈现三段式死链：

```console
# ① CI Pre-download 步骤（外部 curl）——curl 二进制不存在
[step] Pre-download: extracting source URLs from conandata.yml...
  [try 1/2.1/3] v2.4.2.tar.gz ← https://gh-proxy.com/https://github.com/Tencent/MMKV/archive/refs/tags/v2.4.2.tar.gz
  [fail] [Errno 2] No such file or directory: 'curl'
  ...
[WARN] Failed to pre-download v2.4.2.tar.gz, will rely on conan's download

# ② conan source() 直连（Python requests）——302 重定向链超时
mmkv/2.4.2: WARN: network: Error downloading file https://github.com/Tencent/MMKV/archive/refs/tags/v2.4.2.tar.gz:
  'HTTPSConnectionPool(host='github.com', port=443): Max retries exceeded with url:
  /Tencent/MMKV/archive/refs/tags/v2.4.2.tar.gz (Caused by ConnectTimeoutError(...,
  'Connection to github.com timed out. (connect timeout=30)'))'
ERROR: mmkv/2.4.2: Error in source() method

# ③ 退化 git clone 通道——git 缺 libz.so 连 --version 都跑不了
--- git-clone ---
eError loading shared library libz.so: (needed by /data/service/hnp/bin/git)
program finished with exit code 127
```

（① 中镜像 URL 被 CI 剥成官方 URL 再试也同死——Pre-download 只认 conandata.yml 官方 URL，手动加 gh-proxy/ghfast 前缀无效。）

## 二、根因链

```
worker 池部分机器：无 curl + git 缺 libz（4 worker 实证：CI-017/018/021/032 缺 curl；CI-017 git 缺 libz）
        │
        ├─ CI Pre-download：外部 curl 下载 → curl 不存在 → [Errno 2] 直接失败
        │   （且手动镜像前缀被剥除，R39——镜像兜底这条路走不通）
        │
        ├─ conan source()：Python requests 直连 github.com
        │   github.com/{owner}/{repo}/archive/refs/tags/{tag}.tar.gz
        │   = 302 重定向（Location: codeload.github.com/...）
        │   worker 出口到 github.com 连接超时 → Max retries exceeded → 死
        │
        └─ 退化通道 git clone：git 缺 libz.so → exit 127 → 死
```

**关键差异**：`https://codeload.github.com/{owner}/{repo}/tar.gz/refs/tags/{tag}`
是**终端 URL**——本机 curl 实测 HTTP 200 无跳转，tarball 字节与 archive 形态
**完全一致**（sha256 相同：`e77d81da...c685`）。worker 出口只要可达
codeload 域名（CI Pre-download 剥前缀后的可达性判断+conan requests 都能直下），
整链即通。

## 三、判别法（同类失败的定性决策）

1. **同期其他 PR 绿 ≠ 你的能绿**：同窗口 qrcodegen（!9691）/xhook（!9692）
   同用 github archive 形态但 CI 绿——它们撞中的是健康 worker
   （CI-007/CI-020/CI-037，Pre-download 有 curl 或出口通畅）。
   「别人绿」只证明 worker 池不是全坏，不证明你的下载路径在病机上可达。
2. **多轮失败 = 确定性根因**：同一 PR 连续 4+ 轮死在下载段（17:42→21:00
   缺 curl×4）→ 是配方下载路径踩了重定向链，不是单轮可赖 worker 的随机抖动；
   单轮失败才优先怀疑病机网络（rebuild 撞健康机即可）。
3. **失败步骤定位**：死在 `[conan-build-test]` 且日志有 Pre-download
   `[Errno 2] 'curl'` + conan `ConnectTimeoutError` → 下载通道问题；
   死在 `[git-clone, cleanup]` 且 `libz.so`/exit 127 → worker 整机病
   （checkout 都过不去，与配方无关，纯重试）。

## 四、解决方案（代码级）

`archives/m/mmkv/2.4.2/conandata.yml`（commit 5f2826d321）：

```yaml
# codeload 直链（无 302 重定向）：worker 缺 curl 时 github archive 重定向链不可达；
# codeload.tar.gz 直链 200 无跳转，sha256 与官方一致。
sources:
  url:
    - "https://codeload.github.com/Tencent/MMKV/tar.gz/refs/tags/v2.4.2"
  sha256: "e77d81daab0c905c06cad6bceb6ad01ca606a428987e2f1f41a2aa162592c685"
```

**连带修法（必做，E276/E483）**：codeload URL 末段无 `.tar.gz` 后缀，
conan get() 按 basename 误判 zip 报 `BadZipFile`，source() 必须显式
`filename`（commit 7a27efe6d5）：

```python
def source(self):
    get(self, **self.conan_data["sources"],
        filename="mmkv-2.4.2.tar.gz", strip_root=True)
```

## 五、降级方案

codeload 域名也不可达时：① 重试撞健康 worker（git-clone 步骤能过即健康）；
② 上游有 GitCode/Gitee 官方镜像换权威镜像 URL（R39）；③ 都不行按环境故障
上报，禁止塞个人 fork/不明 CDN（R39 红线）。

## 六、红线

- 禁止用「手动镜像前缀」试图绕过（gh-proxy/ghfast 会被 CI Pre-download 剥除——mmkv 9b7d128724 实证）
- 禁止跳过 sha256 校验或用「本地缓存预放」冒充官方源
- 改 URL 前必须实测两种形态 sha256 一致，避免换 URL 换了字节
- 多轮下载段失败时禁止无限 rebuild 赌运气（R41 外部阻塞止损口径）

## 七、验证证据

- 失败实录：#45043/#45076/#45127/#45160/#45233/#45255/#45277/#45278
  （2026-09-12 17:42–23:22，4+ worker：CI-017/018/021/032/003/011）
- 修复后 CI 绿：#45438（CI-020）/ #45604（CI-032）全 7 步 + L0/L1 门禁 + test_package 通过
- 对照组：!9691（qrcodegen，archive 形态，CI-007/020/037 绿）、!9692（xhook，archive 形态，CI-037 绿）
- 本机实测：`curl -fsSL` codeload 直链 200 无 302；sha256 与 archive 形态一致
