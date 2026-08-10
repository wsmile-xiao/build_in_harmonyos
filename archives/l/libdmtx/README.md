# libdmtx

## 简介
libdmtx 是 Data Matrix 二维条码的读写库。

## OHOS 适配
- 0.7.5: autotools 不可用（缺少 automake/libtool），使用 CMake 构建（conanfile.py 中生成 CMakeLists.txt）
- 0.7.8: autotools 不可用，使用 CMake 构建（源码自带 CMakeLists.txt）

## 依赖
- 无编译依赖
- 运行时依赖: libm (math library)

## 功能验证
```bash
# 通过 conan install 使用
conan install --requires=libdmtx/0.7.5
```

## 参考
- 主页: https://github.com/dmtx/libdmtx
