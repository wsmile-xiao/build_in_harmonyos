# sqlmap 1.10 适配笔记

## 编译环境
- 构建系统: python（纯Python项目，无传统构建系统）
- 编译日期: 2026-06-09
- 编译器: 无（Python项目）
- 状态: published

## 编译步骤
sqlmap是纯Python项目，没有configure/Makefile等传统构建系统。
安装方式：
1. 复制源码到 $DEFAULT_PREFIX/share/sqlmap/
2. 创建wrapper脚本在 $DEFAULT_PREFIX/bin/sqlmap 和 $DEFAULT_PREFIX/bin/sqlmapapi
3. wrapper脚本通过 `exec python3 "$SELF_DIR/../share/sqlmap/sqlmap.py"` 调用主程序

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build自动检测BUILD_SYSTEM=autotools | 脚本未识别Python项目 | 手动安装，更新manifest.yaml system=python |
| 2 | init-build下载URL SSL验证失败 | 本地SSL证书链不完整 | 使用curl手动下载后传入file://URL |

## 源码修改
无源码修改。sqlmap是纯Python项目，无需任何源码适配即可在鸿蒙上运行。

## 依赖版本
- python3/3.12.8（系统自带）

## 验证结果
```bash
$DEFAULT_PREFIX/bin/sqlmap --version
→ 输出: 1.10#stable
```

## 交付物
| 文件 | 说明 |
|------|------|
| sqlmap-1.10-ohos-aarch64.tar.gz | Release包（纯Python脚本+wrapper） |
| sqlmap-1.10-ohos-aarch64-debug.tar.gz | Debug包（Python项目无ELF，debug包为空或符号） |

## 注意事项
- sqlmap依赖系统Python 3.12运行，不需要额外编译
- 所有第三方依赖（thirdparty/）已内嵌在源码中
- sqlmap.conf为默认配置文件，随源码一起打包
---

**编译结束**: 2026-06-09 22:36
**最终状态**: published
