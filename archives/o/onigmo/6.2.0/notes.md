# onigmo 6.2.0 适配笔记

## 编译环境
- 构建系统: cmake（自定义，原 autotools 因版本兼容性问题无法使用）
- 编译日期: 2026-05-19
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

### 1. 源码获取
由于 GitHub 下载超时，使用 git clone 获取源码：
```bash
git clone --depth 1 --branch Onigmo-6.2.0 https://github.com/k-takata/Onigmo.git onigmo-6.2.0
```

### 2. 初始化构建
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build onigmo 6.2.0 --url=file:///storage/Users/currentUser/builds/onigmo-6.2.0.tar.gz
```

### 3. 构建配置与编译
由于 autotools 存在 automake 版本不匹配问题，创建自定义 CMakeLists.txt：
```bash
cd /storage/Users/currentUser/builds/onigmo-6.2.0.work
mkdir -p cmake-build && cd cmake-build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF -DENABLE_POSIX_API=ON -DBUILD_TEST=ON
make -j1
```

### 4. 测试验证
```bash
./testc  # 结果: SUCC: 684, FAIL: 0, ERROR: 0
./testu  # 结果: SUCC: 684, FAIL: 0, ERROR: 0
```

### 5. 安装
```bash
make install DESTDIR=$TEST_PREFIX  # Staging 安装
make install                        # 正式安装到 $DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络连接问题 | 使用 git clone 替代直接下载 |
| 2 | init-build 解压出 tool 目录 | tar.gz 结构问题 | 手动复制正确源码到 .orig/.work |
| 3 | autoreconf 失败 | automake 版本不匹配（1.16.5 vs 1.17） | 改用 CMake 构建，创建自定义 CMakeLists.txt |
| 4 | 编译缺少符号（OnigDefaultSyntax 等） | 缺少 regparse.c | 添加 regparse.c 到源码列表 |
| 5 | enc/*.c 编译找不到头文件 | 头文件路径问题 | 在 enc 目录创建头文件软链接 |

## 源码修改

### 新增文件（构建配置）
- `CMakeLists.txt` - 自定义 CMake 构建配置
- `config.h.in` - CMake 配置模板

### 软链接（编译辅助）
- `enc/regenc.h -> ../regenc.h`
- `enc/regint.h -> ../regint.h`
- `enc/config.h -> ../config.h`
- `enc/onigmo.h -> ../onigmo.h`
- `enc/onigmognu.h -> ../onigmognu.h`
- `enc/onigmoposix.h -> ../onigmoposix.h`

## 依赖版本

无外部依赖，为独立的静态库。

## 验证结果

```bash
# 测试结果
./testc: RESULT SUCC: 684, FAIL: 0, ERROR: 0 (by Onigmo 6.2.0)
./testu: RESULT SUCC: 684, FAIL: 0, ERROR: 0 (by Onigmo 6.2.0)

# 安装验证
ls /storage/Users/currentUser/usr/local/lib/libonigmo.a     # 984KB
ls /storage/Users/currentUser/usr/local/include/onigmo.h    # 44KB
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libonigmo.a | 984KB | 静态库 |
| onigmo.h | 44KB | 主头文件 |
| onigmognu.h | 3KB | GNU API 头文件 |
| onigmoposix.h | 6KB | POSIX API 头文件 |
| onigmo-6.2.0-ohos-aarch64.tar.gz | 1MB | 预编译包 |

## 注意事项

1. **构建系统变更**：由于 autotools 版本兼容性问题，本版本使用自定义 CMakeLists.txt 构建，后续版本需检查 autotools 是否修复。

2. **静态库模式**：编译为纯静态库，无动态库版本。如需动态库，修改 CMakeLists.txt 中 `BUILD_SHARED_LIBS=ON`。

3. **编码支持**：库支持多种编码（UTF-8、UTF-16、UTF-32、EUC-JP、Shift_JIS 等），测试覆盖了主要编码格式。

---

**编译结束**: 2026-05-19 18:00
**最终状态**: built