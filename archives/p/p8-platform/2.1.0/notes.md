# p8-platform 2.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-08
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

1. 克隆源码
   ```bash
   git clone https://github.com/Pulse-Eight/platform.git ~/builds/p8-platform-2.1.0
   ```

2. 创建构建目录
   ```bash
   mkdir -p ~/builds/p8-platform-2.1.0/build && cd ~/builds/p8-platform-2.1.0/build
   ```

3. 配置
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
   ```

4. 编译
   ```bash
   make -j1
   ```

5. 安装（staging）
   ```bash
   make install DESTDIR=$HOME/tmp/test-install-p8-platform-2.1.0
   ```

6. 本地安装
   ```bash
   make install
   ```

## 验证结果

```bash
ls -lh ~/usr/local/lib/libp8-platform.a
# -rw-rw---- 1 file_manager 288K 2026-06-08 18:00 libp8-platform.a

ls ~/usr/local/include/p8-platform/
# os.h  posix/  sockets/  threads/  util/
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libp8-platform.a | 288KB | 静态库 |
| include/p8-platform/ | - | 头文件目录 |
| lib/pkgconfig/p8-platform.pc | - | pkg-config 配置 |

## 注意事项

1. **静态库**：编译为静态库，无运行时依赖
2. **CMake 自动识别平台**：无需特殊配置
3. **需要 Threads 支持**：系统 pthread 已满足