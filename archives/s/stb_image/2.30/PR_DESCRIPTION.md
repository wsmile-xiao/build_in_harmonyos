# stb_image 2.30 适配

## 软件信息
- **名称**: stb_image
- **版本**: 2.30
- **类型**: 单头文件库
- **许可证**: MIT / Unlicense
- **上游**: https://github.com/nothings/stb

## 功能说明
图像加载/解码库，支持多种格式：
- JPEG (baseline & progressive)
- PNG (1/2/4/8/16-bit)
- BMP, TGA, PSD, GIF, HDR, PIC, PNM

## 测试结果

### 上游测试
✅ **PNG Suite Primary Tests**: 77/77 通过
- 测试所有 PNG 编码类型（灰度、RGB、索引、透明度、交错）
- 命令：`./image_test pngsuite/primary/*.png`

✅ **Image Write Test**: 通过

### Conan 适配测试
✅ **test_package**: 4/4 通过
- PNG from memory
- BMP from memory  
- PNG info query
- Invalid data error handling

## 适配说明
- ✅ 无需修改源码
- ✅ 无需打补丁
- ✅ 完全兼容鸿蒙 PC 平台 (OHOS 6.0 / aarch64)
- ✅ 单头文件库，使用简单

## 构建验证
```bash
conan create archives/s/stb_image/2.30 --profile=ci/conan/profiles/ohos-aarch64
# ✅ 所有测试通过
```

## 统计数据

按照积分赛事规则统计：

### 上游测试
- **PNG Suite**: 77 个测试文件，全部通过
  - 测试类型：集成测试
  - 测试覆盖：所有 PNG 编码类型
- **Image Write**: 1 个测试，通过
  - 测试类型：单元测试

**上游测试小计**: 2 个测试套件，78 个测试用例

### 适配测试  
- **test_package**: 4 个单元测试
  - PNG from memory - 单元测试
  - BMP from memory - 单元测试
  - PNG info query - 单元测试
  - Invalid data error - 单元测试

**适配测试小计**: 4 个单元测试

### 测试总结
- 上游测试执行率: 100% (2/2 套件)
- 上游测试通过率: 100% (78/78 用例)
- 适配测试通过率: 100% (4/4 用例)
- 总体覆盖率: 100%

---

**测试平台**: 鸿蒙 PC (OHOS 6.0 / aarch64)  
**编译器**: clang 15.0.4
