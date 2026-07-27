# mongoose 7.21 适配笔记

## 编译环境
- 构建系统: direct compilation (single-file library)
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤
```bash
# 1. 下载源码
curl -fsSL https://github.com/cesanta/mongoose/archive/refs/tags/7.21.tar.gz -o mongoose-7.21.tar.gz
tar -xzf mongoose-7.21.tar.gz
cd mongoose-7.21

# 2. 编译静态库 (mongoose.c is single-file amalgamated source)
clang -O2 -fPIC -c mongoose.c -o mongoose.o
llvm-ar rcs libmongoose.a mongoose.o
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 共享库运行 ELF 签名问题 | OHOS 安全机制 | 推荐使用静态库替代 |
| 2 | Makefile 在 test/ 子目录，结构复杂 | 上游 Makefile 设计 | 直接编译 mongoose.c 单文件 |

## 依赖版本
- 无必须依赖
- 可选：OpenSSL（SSL/TLS支持）

## 验证结果
### conan create 验证
- ✅ 编译通过
- ✅ 测试通过 (test_mongoose: MG_VERSION, mg_str, mg_match)

### CI 模拟 (W3)
- L0 (quality gate): ✅ pass
- L1 (test execution): ✅ pass
- L4 (security scan): ✅ pass
- L5 (artifact baseline): ✅ pass

## 注意事项
- 推荐使用静态库（libmongoose.a）部署，功能完整且稳定
- 共享库 ELF 签名问题为平台限制，非编译问题
- mongoose.h 头文件包含完整 API 定义
- mongoose.c 是合并后的单文件源码，包含所有功能模块
---

**编译结束**: 2026-07-15 23:05
**最终状态**: built
