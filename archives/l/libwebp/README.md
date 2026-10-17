# libwebp

## 简介
WebP图像编码、解码及容器处理库，包含无损/有损RGBA编解码、mux/demux与SharpYUV颜色转换接口。

## OHOS 适配
- 构建系统: cmake
- 详见各版本 notes.md 获取适配详情

## 依赖
生产Conan库包无新增外部第三方运行依赖，包内WebP组件关系由Conan组件及真实ELF闭包声明。
原上游测试使用官方固定FuzzTest提交及其Abseil、RE2、GoogleTest和ANTLR源码，不把测试vendor源码下载冒充已发布provider。

## 功能验证
各版本真实运行结果与边界见其`reports/test-report.md`和`notes.md`。
1.6.0.2已分别在正式Conan和官方本地CI独立事务运行完整原测试76/76、消费者4/4与鸿蒙专项1/1。
鸿蒙专项验证AArch64签名、实际SONAME/NEEDED和加载命名空间，并真实调用codec；不是只打印平台字符串。
`built`不代表上传、发布、平台CI或提审通过，准确状态以对应版本和当前HEAD平台回读为准。

## 参考
- https://chromium.googlesource.com/webm/libwebp
