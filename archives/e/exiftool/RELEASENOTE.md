# exiftool — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf exiftool-13.50-ohos-aarch64.tar.gz -C ~/usr/local

cd exiftool-13.50-ohos-aarch64 && sh install-exiftool-13.50.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 | 测试结果 |
|------|------|--------|----------|
| 13.50 | ✅ partial | 0 | 113/113 PASS |

## 最新版本 (13.50) 详情

### 包内容
- 二进制: bin/exiftool (Perl 脚本)
- 模块: bin/lib/Image/ExifTool/ (200+ Perl 模块)
- 包大小: 38.8 MB

### 编译信息
- 构建系统: Perl MakeMaker
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 0

### 测试结果
- 测试文件: 113
- 测试断言: 600
- 结果: All tests successful

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- Perl 5.42.0+ (已预装)
- 无其他依赖

## 功能验证
```bash
$ exiftool -ver
13.50

$ exiftool image.jpg
（显示图片 EXIF 元数据）
```

## 版本历史

| 版本 | 发布日期 | 说明 |
|------|----------|------|
| 13.50 | 2026-02-07 | Security update (MacOS), 新增 Canon/Sony 镜头支持 |

---

**维护者**: openharmony-compile-agent