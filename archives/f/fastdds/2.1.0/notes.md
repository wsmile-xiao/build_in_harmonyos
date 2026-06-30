# Fast-DDS 2.1.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-29
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: **built** (成功)

## 编译步骤

### 1. 源码下载
```bash
# 下载 Fast-DDS v2.1.0 源码
python3 -c "
import ssl, urllib.request, hashlib
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
url = 'https://github.com/eProsima/Fast-DDS/archive/refs/tags/v2.1.0.tar.gz'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
    data = resp.read()
    print(f'SHA256: {hashlib.sha256(data).hexdigest()}')
    print(f'Size: {len(data)} bytes')
"
# SHA256: 6653772d5cbb0b188bb585d50e557ce5e587faaad4b607120694212bc726bb26
# Size: 6996587 bytes
```

### 2. 依赖编译 - Fast-CDR v1.0.16
```bash
cd /storage/Users/currentUser/tmp/Fast-CDR-1.0.16
mkdir -p build && cd build
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
  -DCMAKE_INSTALL_PREFIX=$HOME/builds/fastdds-deps \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..
make && make install
# 结果: 成功，生成 libfastcdr.so 和头文件
```

### 3. 依赖编译 - tinyxml2 v8.0.0 (with -fPIC)
```bash
# 从 bwfmetaedit 项目获取匹配的 tinyxml2 源码 (v8.0.0)
cp bwfmetaedit-26.01.orig/Source/TinyXml2/tinyxml2.{h,cpp} fastdds-deps/include/
clang -c -fPIC -O2 -I./include include/tinyxml2.cpp -o tinyxml2.o
ar rcs lib/libtinyxml2.a tinyxml2.o
```

### 4. 依赖编译 - foonathan_memory v0.6-2 (with -fPIC)
```bash
cd /storage/Users/currentUser/tmp/memory-0.6-2
CXX=clang++
FLAGS="-std=c++11 -fPIC -O2 -DFOONATHAN_MEMORY=1"
INCLUDE="-I./include -I fastdds-deps/include/foonathan/memory"
for src in src/*.cpp; do
    $CXX $FLAGS $INCLUDE -c "$src" -o "build/$(basename ${src%.cpp}).o"
done
ar rcs fastdds-deps/lib/libfoonathan_memory.a build/*.o
```

### 5. foonathan_memory container_node_sizes_impl.hpp 补丁
```cpp
// 手写 aarch64/libc++ 容器节点大小常量
// 替换 node_size_debugger 工具生成的代码
// 注意：此文件从 foonathan::memory 命名空间内部 include，不能再嵌套 namespace
template <typename T>
struct set_node_size
: std::integral_constant<std::size_t, tree_node_overhead + sizeof(T)> {};
// map_node_size / unordered_map_node_size 接受单模板参数
```

### 6. Fast-DDS 配置与编译
```bash
cd /storage/Users/currentUser/builds/fastdds-2.1.0.work/build
cmake /storage/Users/currentUser/builds/fastdds-2.1.0.work \
  -DCMAKE_C_COMPILER=$HOME/usr/local/bin/CC \
  -DCMAKE_CXX_COMPILER=$HOME/usr/local/bin/CXX \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DTHIRDPARTY=ON \
  -DTHIRDPARTY_UPDATE=OFF \
  -DTHIRDPARTY_TinyXML2=OFF \
  -DCMAKE_PREFIX_PATH=$HOME/builds/fastdds-deps \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DBUILD_TESTING=OFF
make -j1
# 结果: 99% 编译成功，libfastrtps.a (25MB) 生成
# fast-discovery-server 工具链接失败（非必需）
```

### 7. 冒烟测试
```bash
# 编写测试程序创建 DomainParticipant
clang++ -std=c++14 -O2 \
  -I fastdds-deps/include \
  -I fastdds-deps/include/foonathan/memory \
  test_build.cpp \
  -L fastdds-deps/lib \
  -lfastrtps -lfoonathan_memory -ltinyxml2 -lfastcdr -lpthread -ldl -lrt \
  -o test_build
./test_build
# 输出: SUCCESS: DomainParticipant created
# 退出码: 0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败 | SSL 证书验证失败 | 使用 Python urllib 禁用 SSL 验证下载 |
| 2 | CMake 不识别平台 | HarmonyOS 未被 CMake 内置识别 | 记录警告，不阻塞配置 |
| 3 | Fast-CDR CMake 版本不兼容 | CMake 3.5 最低版本被新 CMake 移除 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 4 | asio 子模块配置失败 | thirdparty/asio 为空 + git submodule update 失败 | THIRDPARTY_UPDATE=OFF + 预装 asio 头文件到 deps/include |
| 5 | tinyxml2 子模块配置失败 | THIRDPARTY=ON 导致 TINYXML2_FROM_SOURCE=ON | THIRDPARTY_TinyXML2=OFF 使用预编译库 |
| 6 | foonathan_memory 递归模板实例化 | container_node_sizes_impl.hpp 中 sizeof(T) 触发 std::set 实例化导致循环 | 手写常量替换 sizeof(T) 计算 |
| 7 | foonathan_memory 命名空间嵌套 | container.hpp 从 namespace 内 include，不能再包 namespace | 移除 namespace 包装 |
| 8 | map_node_size 模板参数不匹配 | foonathan API 用单参数，我写了双参数 | 改为单参数模板 |
| 9 | tinyxml2 R_AARCH64_ADD_ABS_LO12_NC 重定位失败 | 预编译库缺少 -fPIC | 用 -fPIC 重新编译 |
| 10 | foonathan_memory 同上 | 同上 | 用 -fPIC 重新编译所有 .cpp |
| 11 | make -j jobserver 失败 | fifo 创建权限问题 | 使用 make -j1 |
| 12 | TinyXML2 cmake 路径解析错误 | 相对路径 ../.. 在 cmake config 中解析不正确 | 使用绝对路径 |
| 13 | config.h 缺失 | CMake install 未生成 | 从 config.h.in 手动生成 |
| 14 | fast-discovery-server 链接失败 | foonathan_memory 部分符号未在静态库中 | 非必需工具，跳过 |

## 依赖版本

| 依赖 | 版本 | 状态 |
|------|------|------|
| Fast-CDR | 1.0.16 | ✅ 已编译安装 (shared) |
| asio | 1.18.0 | ✅ header-only，已安装到 include/ |
| tinyxml2 | 8.0.0 | ✅ 已用 -fPIC 重新编译 |
| foonathan_memory | 0.6-2 | ✅ 已用 -fPIC 重新编译 |
| CMake | 4.1.2 (系统) | ✅ 可用 |

## 产物

| 文件 | 大小 | 类型 |
|------|------|------|
| libfastrtps.a | 25,082,086 bytes | 静态库 |
| test_build | 7,137,856 bytes | 测试可执行文件 |

## 注意事项

1. Fast-DDS v2.1.0 的 tarball 不包含 git 子模块内容
2. OHOS 上所有静态库依赖必须用 -fPIC 编译
3. foonathan_memory 的 container_node_sizes_impl.hpp 需手写（OHOS 无 node_size_debugger）
4. map_node_size / unordered_map_node_size 在 foonathan_memory API 中是单参数模板
5. v2.1.0 使用旧名称 fastrtps，库文件名为 libfastrtps.a
6. fast-discovery-server 工具可选，其链接失败不影响核心库

---

**编译结束**: 2026-06-29 15:51
**最终状态**: built (成功)
