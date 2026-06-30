# dssim - RGBA 结构相似度度量工具

## 软件简介

dssim 是用于计算图像间结构相似度的工具，使用多尺度 SSIM 算法变体，逼近人类视觉感知。

**主要功能**:
- 多分辨率加权比较，在线性光 RGB 中进行缩放
- 使用 L\*a\*b\* 色彩空间进行 SSIM 计算
- 支持 alpha 通道
- 支持带色彩配置文件的图像
- 多核 CPU 并行计算
- 可作为 C、Rust 和 WASM 库使用

## 已编译版本

| 版本 | 状态 | 构建系统 | 补丁数 | 日期 |
|------|------|----------|--------|------|
| 3.4.0 | ✅ success | cargo | 0 | 2026-05-30 |

## 快速安装

```bash
# 下载预编译包
tar xzf dssim-3.4.0-ohos-aarch64.tar.gz -C ~/usr/local

# 运行安装脚本
cd ~/usr/local/dssim-3.4.0-ohos-aarch64
sh install-dssim-3.4.0.sh
```

## 使用示例

### 基本比较
```bash
dssim original.png modified.png
# 输出: 0.02341 filename (越小越相似，0 = 完全相同)
```

### 多文件比较
```bash
dssim original.png modified1.png modified2.png modified3.png
```

### 生成差异可视化
```bash
dssim -o difference.png original.png modified.png
```

## 编译指导

### 构建系统说明

本软件使用 Rust Cargo 构建，在 OHOS 上无需修改源码即可编译。

```bash
# Cargo 构建（OHOS target）
cargo build --release --target aarch64-unknown-linux-ohos
```

### 补丁应用

无需补丁，源码在 OHOS 上原生编译成功。

## 依赖关系

- **运行依赖**: musl libc (已预装)
- **编译依赖**: Rust >= 1.72 (OHOS Rust 1.95.0 已验证)
- **Cargo 依赖**: imgref, lodepng, load_image, rayon, rgb, crossbeam-channel 等（自动下载）

## 参考资料

- 官方网站: https://kornel.ski/dssim
- 源码仓库: https://github.com/kornelski/dssim