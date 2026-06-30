# xmlsec1

XML 安全库，提供 XML 签名和加密功能。

## 版本
- 1.3.11 (2026-05-20)

## 依赖
- libxml2 >= 2.9.0
- libxslt >= 1.1.0
- openssl >= 1.0.0

## 用法
```bash
# 设置库路径（musl 不支持 RUNPATH）
export LD_LIBRARY_PATH="$HOME/usr/local/lib:/data/service/hnp/libxslt.org/libxslt_1.1.39/lib:$LD_LIBRARY_PATH"

# 验证安装
xmlsec1 --version
```

## 平台限制
- musl 动态链接器不支持 RUNPATH，需手动设置 LD_LIBRARY_PATH
- HarmonyOS 平台识别通过 config.guess/config.sub 补丁实现

## 相关链接
- 官网: https://www.aleksey.com/xmlsec/