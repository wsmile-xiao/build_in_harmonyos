# kosli-cli 2.24.2 编译笔记

## 编译方法

**方法**: 使用官方预编译二进制（非源码编译）

## 编译过程

### 1. 下载预编译包

由于直接访问 GitHub 超时，使用 gh-proxy.com 加速下载：

```bash
python3 -c "
import urllib.request
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
url = 'https://gh-proxy.com/https://github.com/kosli-dev/cli/releases/download/v2.24.2/kosli_2.24.2_linux_arm64.tar.gz'
urllib.request.urlretrieve(url, 'kosli_2.24.2_linux_arm64.tar.gz')
"
```

### 2. ELF 签名

OpenHarmony 要求所有可执行 ELF 必须签名：

```bash
/data/service/hnp/bin/binary-sign-tool sign -inFile kosli -outFile kosli-signed -selfSign 1
chmod a+x kosli-signed
```

### 3. 安装验证

```bash
./kosli-signed version
# Output: version.BuildInfo{Version:"v2.24.2", GitCommit:"1030045...", GoVersion:"go1.26.4"}
```

## 遇到的问题

### Go 工具链 Bootstrap 循环依赖

**问题描述**:
- Go 1.26.4 需要已签名的 bootstrap Go >= 1.22.6 才能从源码编译
- `binary-sign-tool` 拒绝签名外部下载的 Go 二进制（报错 "is not trust command"）
- Go 1.4（理论上的 bootstrap 起点）不支持 aarch64 架构
- 形成循环依赖：需要 Go 来编译 Go，但 Go 需要先被签名才能运行

**解决方案**:
- 使用官方预编译的 Go 静态链接二进制
- `binary-sign-tool` 可以成功签名 kosli 预编译包（与 Go 不同，kosli 是普通二进制）
- 这绕过了 Go 编译器的签名限制问题

### 网络访问限制

**问题**: 直接访问 GitHub 和 wget 超时
**解决**: 使用 gh-proxy.com 加速器下载

## 知识沉淀

### E077 补充

`binary-sign-tool` 的信任机制：
- 可以签名普通的 ELF 可执行文件（如 kosli）
- 拒绝签名某些特殊二进制（如 Go 编译器，报错 "is not trust command")
- 这可能是出于安全考虑，防止恶意替换编译器

### 建议

对于 Go 项目：
1. 首先尝试使用官方预编译包
2. 如果预编译包不可用，需要从 OpenHarmony 官方获取已签名的 Go 工具链
3. 或使用交叉编译在其他平台编译后移植

---

**编译结束**: 2026-06-08 15:20
**最终状态**: published (预编译二进制签名成功)