# DRAFT-rjj666-libmysofa-tmp-readonly-test-workdir

## 基本信息
- **严重度**: 2
- **类别**: filesystem | test | portability | ohos
- **作者**: rjj666

## 错误特征
```
fopen("/tmp/...") 返回 NULL，errno 30 (Read-only file system)
依赖该临时文件的测试用例连锁失败
```

## 根因分析
OHOS 真机 /tmp 挂载为只读。libmysofa 上游 tests/easy.c、common.c 以
fopen("/tmp/...") 创建临时 SOFA 文件后再断言读取，OHOS 上创建阶段即失败。

## 推荐方案
**方法**: relative-workdir-tempfile（临时文件改工作目录相对路径）

**说明**: 补丁将测试源码中的 "/tmp/xxx" 字面量替换为工作目录相对路径；
ctest 工作目录（构建目录）可写，Linux CI 与 OHOS 真机行为一致，无跨平台副作用。

## 验证
```bash
touch /tmp/probe   # 真机上报错，证实只读
ctest --output-on-failure   # 修正后 43/43 全绿
```

## 来源
- 草稿: DRAFT-rjj666-libmysofa-tmp-readonly-test-workdir
- 关联: E002, E024, E052, E060
- 提升日期: 待审核
