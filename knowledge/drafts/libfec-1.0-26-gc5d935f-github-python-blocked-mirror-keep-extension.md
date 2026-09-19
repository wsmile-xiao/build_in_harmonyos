# 设备 Python 连不上 github.com：镜像改写须保留 .tar.gz 扩展名（codeload 直链会 BadZipFile）

- **软件**: libfec 1.0-26-gc5d935f（泛化到 github 托管源码的手工设备验证）
- **阶段**: source（conan create 源码下载）
- **severity**: 3
- **状态**: DRAFT

## 现象

两种失败形态：

```
WARN: network: Error downloading file https://github.com/...tar.gz:
  'HTTPSConnectionPool ... Connection to github.com timed out. (connect timeout=30)'
...
BadZipFile: File is not a zip file        # 换成 codeload 直链后
```

同机 `curl` 对 codeload.github.com / gh-proxy.com 都可达，只有 conan 的
Python 栈连不上 github.com 主站。

## 根因

1. Python（urllib3）与 curl 的连接路径差异（IPv6/解析顺序）导致前者超时，
   重试不收敛。
2. 镜像替换暗坑：`https://codeload.github.com/<o>/<r>/tar.gz/<ref>` **没有
   `.tar.gz` 后缀**，conan 的 `get()` 按文件名后缀选解压器 → 落入 zip 分支 →
   sha256 校验**通过**但解包报 `BadZipFile`。

## 修复（手工设备验证场景）

```sh
# 1) 设备端验证镜像字节等价
curl -sL "https://gh-proxy.com/https://github.com/<o>/<r>/archive/<ref>.tar.gz" -o src.tar.gz
sha256sum src.tar.gz        # 必须与 conandata 的 sha256 一致
# 2) 改写 job 副本 conandata.yml（保留 .tar.gz 扩展名）
sed -i 's|https://github.com/|https://gh-proxy.com/https://github.com/|' conandata.yml
```

- **不要**用 codeload 直链（无扩展名 → BadZipFile）；
- 提交到仓库的 conandata **始终保持官方 URL**（R39/PF7）；CI 有 mirror
  fallback 自动兜底，镜像改写只发生在 job 工作副本上。

## 证据

libfec 1.0-26-gc5d935f 真机（frp-tip.com:56267）：create-1 Python 超时；
create-4 codeload 直链 sha256 过但 BadZipFile；create-8 gh-proxy 前缀（带
扩展名）后源下载与全流程正常，设备端 sha256 与本地一致
（`a2fff6f8…c3bc9`）。
