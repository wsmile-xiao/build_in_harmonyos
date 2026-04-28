# libaio

## 简介
libaio 是 Linux 原生异步 I/O 访问库，提供内核级异步 I/O 操作接口。

## OHOS 适配
- 使用自定义 Makefile 构建（非 autotools）
- 测试用例需要补丁适配 HarmonyOS

## 依赖
- 无编译依赖

## 功能验证
```bash
ls -la $HOME/usr/local/lib/libaio*
```

## 参考
- 主页: https://pagure.io/libaio
