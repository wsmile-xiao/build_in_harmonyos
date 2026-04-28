# gzip

## 简介
GNU gzip — 文件压缩/解压工具，实现 deflate 压缩算法。是 Linux/Unix 系统最基础的压缩工具之一。

## OHOS 适配
- 需 config.guess/config.sub 补丁支持 HarmonyOS
- config.sub 需在 `linux-gnu*` 行加入 `linux-ohos*`
- shell 脚本因 shebang 限制无法直接执行，需通过 `sh` 调用（如 `sh zless`）
- 核心压缩解压功能正常，gzip/gunzip/zcat 二进制完全可用

## 依赖
- 编译依赖：无必须依赖

## 功能验证
```bash
gzip --version
echo "test" | gzip | gunzip
```

## 参考
- 官方网站：https://www.gnu.org/software/gzip/
