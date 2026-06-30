# wxWidgets 3.2.6 编译笔记

## 编译信息
- **软件**: wxWidgets 3.2.6
- **日期**: 2026-05-20
- **构建系统**: CMake
- **状态**: published

## 编译步骤

### 1. 源码获取
```bash
git clone https://github.com/wxWidgets/wxWidgets.git --depth 1 --branch v3.2.6
```

### 2. 平台适配
修改 `build/cmake/toolkit.cmake`，添加 HarmonyOS 平台检测：
```cmake
elseif(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OpenHarmony")
    set(wxDEFAULT_TOOLKIT gtk3)
    set(wxTOOLKIT_OPTIONS gtk2 gtk3 gtk4 motif qt)
    set(wxPLATFORM UNIX)
    add_definitions(-D__OHOS__)
```

### 3. CMake 配置
```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DwxBUILD_SHARED=OFF \
  -DwxBUILD_TESTS=OFF \
  -DwxUSE_GUI=OFF \
  -DwxUSE_XLOCALE=OFF \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++
```

### 4. 源码修改（解决 musl libc 兼容性）

#### 文件1: src/common/sckaddr.cpp
添加宏定义，使用 musl libc 提供的标准 POSIX 函数：
```cpp
#ifdef __OHOS__
    #define HAVE_INET_ATON
    #define HAVE_GETHOSTBYNAME
    #define HAVE_GETSERVBYNAME
    #define HAVE_GETHOSTBYADDR
#endif
```

#### 文件2: include/wx/private/socket.h
定义正确的类型：
```cpp
#ifdef __OHOS__
    #define WX_SOCKLEN_T socklen_t
    #define SOCKOPTLEN_T socklen_t
#else
    #define WX_SOCKLEN_T int
    #define SOCKOPTLEN_T int
#endif
```

#### 文件3: src/unix/sockunix.cpp
```cpp
#elif defined(__OHOS__)
#    define WX_SOCKLEN_T socklen_t
```

### 5. 编译与安装
```bash
cmake --build . -j2
cmake --install . --DESTDIR=$TEST_PREFIX
```

---

**编译结束**: 2026-05-20

**最终状态**: published

**产物**:
- libwx_baseu-3.2.a (核心库)
- libwx_baseu_net-3.2.a (网络库)
- libwxregexu-3.2.a (正则库)
- libwxzlib-3.2.a (压缩库)

**补丁**: 0001-harmonyos-socket-fix.patch