# 补丁目录 - pod2man 6.0.2

此目录用于存放源码补丁文件。

## 当前状态

**补丁数量**: 0

pod2man 6.0.2 无需源码修改，直接使用 ExtUtils::MakeMaker 构建系统即可成功编译。

## 补丁命名规范

如果有补丁，应遵循以下命名格式：

```
NNNN-描述.patch
```

例如：
- `0001-fix-build-error.patch`
- `0002-add-ohos-support.patch`

## 补丁生成方式

使用 ohc-run.py 工具自动生成：

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py refresh-patch --auto pod2man 6.0.2
```

## 说明

- Perl 模块通常不需要补丁
- ExtUtils::MakeMaker 构建系统兼容性良好
- 如有构建问题，优先通过构建参数解决