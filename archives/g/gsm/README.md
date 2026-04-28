# gsm

## 简介
GSM 06.10 语音编解码库 — 实现欧洲 GSM 全速率语音编解码标准。附带 toast/untoast 压缩工具。

## OHOS 适配
- 使用简单 Makefile，需修改 `CC=gcc` → `CC=clang`
- 需添加 `-fPIC` 到 CCFLAGS
- HMDFS 不支持硬链接，需设置 `LN=ln -s`

## 依赖
- 编译依赖：无

## 功能验证
```bash
toast -h 2>&1 | head
# 压缩测试
echo "test audio data" > test.pcm
toast test.pcm
untoast test.gsm
```

## 参考
- 官方网站：https://www.quut.com/gsm/
