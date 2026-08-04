# jpeg-archive

JPEG 优化与归档工具集，使用 mozjpeg 提供高质量压缩。

## 工具列表

| 工具 | 功能 |
|------|------|
| `jpeg-recompress` | 重新编码 JPEG，在保持视觉质量前提下最小化文件大小 |
| `jpeg-compare` | 比较两张 JPEG 的视觉相似度（SSIM/MS-SSIM/SmallFry/MPE） |
| `jpeg-hash` | 基于像素数据计算哈希（跨重编码稳定） |
| `jpeg-archive` | 批量并行重压缩封装脚本（使用 Ladon 或 GNU Parallel） |

## 技术特点

- **视觉质量保持**：使用 SSIM/MS-SSIM 算法评估，确保压缩后视觉无损
- **mozjpeg 驱动**：利用 Mozilla mozjpeg 编码器，比标准 libjpeg 节省 30-70% 空间
- **批量并行处理**：jpeg-archive 脚本自动调用 Ladon/GNU Parallel 多核并行压缩

## 上游仓库

https://github.com/danielgtaylor/jpeg-archive

## 许可证

MIT License

## 状态

| 版本 | 状态 | 平台 | 备注 |
|------|------|------|------|
| 2.2.0 | built | OHOS aarch64 | 依赖 mozjpeg/4.1.1 |
