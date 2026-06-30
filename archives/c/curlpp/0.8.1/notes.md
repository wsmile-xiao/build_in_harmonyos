# curlpp 0.8.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-17
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 1. 安装依赖 curl (预编译包)
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- curl 8.19.0

# 2. cmake configure
export PKG_CONFIG_PATH="/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
cd build && cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release

# 3. make
make -j1

# 4. make install DESTDIR (staging)
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-curlpp-0.8.1

# 5. package
python3 $SKILL_ROOT/scripts/ohc-run.py package curlpp 0.8.1

# 6. make install (本地部署)
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CURLOPT_CLOSEPOLICY (int 9999) 无法隐式转换为 CURLoption 枚举 | curl 8.x 将 CURLOPT_CLOSEPOLICY 标记为 CURLOPT_OBSOLETE72=9999 (int)，不再是枚举值，C++ 不允许 int 隐式转换到 enum | 将 Options.hpp 第281行改为 `static_cast<CURLoption>(CURLOPT_CLOSEPOLICY)` |
| 2 | 多个 curl 废弃 API 警告 | curlpp 0.8.1 使用了 curl 8.x 中已废弃的 API (CURLOPT_PROGRESSFUNCTION, CURLOPT_PUT, CURLOPT_HTTPPOST 等) | 仅产生警告不影响编译，记录为已知兼容性问题 |
| 3 | make check 不可用 | curlpp 0.8.1 无测试套件，CMake 项目未配置 test target | 跳过，用用户验证替代（编译测试程序验证 HTTP 请求） |

## 源码修改

- `include/curlpp/Options.hpp` 第281行: `CURLOPT_CLOSEPOLICY` → `static_cast<CURLoption>(CURLOPT_CLOSEPOLICY)`，修复 curl 8.x 枚举类型兼容性

## 依赖版本

- curl/8.19.0 (预编译包)
- zlib/1.3.1 (系统)
- OpenSSL/3.0.12 (系统)

## 验证结果

```bash
# curlpp-config
/storage/Users/currentUser/usr/local/bin/curlpp-config --version
→ libcurlpp 0.8.1

# pkg-config
pkg-config --modversion curlpp → 0.8.1

# 库文件
ls /storage/Users/currentUser/usr/local/lib/libcurlpp*
→ libcurlpp.a, libcurlpp.so

# 功能验证（编译测试程序执行 HTTP 请求）
./test_curlpp → curlpp library linked successfully + HTTP response received
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| curlpp-0.8.1-ohos-aarch64.tar.gz | 5805KB | 预编译包 |

## 注意事项

- curlpp 0.8.1 与 curl 8.x 存在多处 API 废弃兼容问题，编译时产生大量 deprecation warnings（不影响功能）
- 需设置 PKG_CONFIG_PATH 包含 `$DEFAULT_PREFIX/lib/pkgconfig` 以确保 cmake FindCURL 能找到 libcurl
- 无 make check 测试套件
---

**编译结束**: 2026-06-17 16:58
**最终状态**: published
