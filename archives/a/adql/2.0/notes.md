# adql 2 适配笔记

## 编译环境
- 构建系统: custom（waf）
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 平台: OHOS（OpenHarmony PC, aarch64）
- 状态: built

## 编译步骤

```bash
# 下载源码（GitHub API tarball）
wget https://api.github.com/repos/Caltech-IPAC/libadql/tarball/ADQL-20221012

# waf 构建（OHOS 需 python 显式调用）
python waf configure --prefix=<prefix>
python waf build
python waf install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | waf 需 python 解释 | waf 脚本需 python2 兼容 | 用 `python` 显式调用 waf（仓库 CI 使用 python 而非 python3） |
| 2 | 依赖 boost::spirit | libadql 依赖 boost::spirit（1.74+） | 依赖系统预装 boost（仓库无 boost conan 包，R36） |

## 注意事项
- adql 是 C++17 ADQL 解析库，waf 构建
- 版本 tag ADQL-20221012 对应 IVOA ADQL 2.0

---

**编译结束**: 2026-08-09
**最终状态**: built
