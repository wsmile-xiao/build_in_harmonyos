# checkit-tiff

TIFF 文件合规性校验工具，基于 policy-oriented 规则集快速检查 baseline TIFF 文件。

## 简介

checkit-tiff 是一个 C 语言编写的 TIFF 合规性校验器（基于 libtiff），支持多种校验规则集（example_configs/），可对 TIFF 文件进行快速风险分析和合规检查。

## OHOS 适配

- CMakeLists.txt 位于 src/ 子目录，install 规则引用 repo 根的 `../example_configs` 和 `../tiffs_should_*`，需整库 clone
- PCRE2 探测走显式变量分支（PCRE2_INCLUDE_DIR/PCRE2_LIBRARY/PCRE2_POSIX_LIBRARY），可直接传 Conan 依赖路径
- 上游仓库位于 git.fsfe.org，Web UI 受 Anubis 反爬保护，git 协议可用
- Windows 交叉编译时需强制 Ninja generator（MinGW Makefiles 需要 sh.exe）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| pcre2 | 10.47 | 正则表达式库（静态链接） |

## 功能验证

```bash
checkit_tiff -h
# 打印帮助信息并退出 0
```

## 参考

- 上游仓库: https://git.fsfe.org/art1pirat/checkit_tiff
