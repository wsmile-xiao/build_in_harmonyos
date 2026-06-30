# bottom 0.12.3 适配笔记

## 编译环境
- 构建系统: cargo (Rust项目)
- 编译日期: 2026-05-26
- 编译器: rustc 1.95.0 (aarch64-unknown-linux-musl)
- 状态: built

## 编译步骤
1. init-build下载源码
2. 修复cargo/rustc的RPATH问题（patchelf + sign-elf）
3. cargo build --release --bin btm
4. 安装到staging并设置RPATH
5. package生成预编译包
6. 本地安装验证成功

## 遇到的问题与解决方案
- cargo/rustc在OHOS上需要RPATH修复和ELF签名才能运行

## 验证结果
```bash
$ btm --version
bottom 0.12.3
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| bottom-0.12.3-ohos-aarch64.tar.gz | 4.1M | Release制品 |
| bottom-0.12.3-ohos-aarch64-debug.tar.gz | 36K | Debug符号包 |
