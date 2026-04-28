# gawk

## 简介
GNU Awk — POSIX 标准 awk 的 GNU 实现，功能强大的文本处理工具。支持正则表达式、字段处理、关联数组、用户自定义函数等。

## OHOS 适配
- 需修改 `config.guess` 和 `config.sub` 添加 HarmonyOS 检测
- HarmonyOS 对管道/终端/套接字的 `fstat()` 返回 EACCES，需用 `__OHOS__` 宏条件编译处理
- 扩展模块中 `_BSD_SOURCE` 需改为 `_GNU_SOURCE`，确保 dirent.h 正确包含
- pma.h 包含路径需修正为 `support/pma.h`
- 替代 toybox awk，功能更完整

## 依赖
- 编译依赖：无必须依赖
- 可选依赖：mpfr, gmp

## 功能验证
```bash
gawk --version
echo "hello world" | gawk '{print $1}'
echo "1 2 3 4 5" | gawk '{sum=0; for(i=1;i<=NF;i++) sum+=$i; print "Sum:", sum}'
```

## 参考
- 官方文档：https://www.gnu.org/software/gawk/manual/
