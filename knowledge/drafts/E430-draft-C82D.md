# E430 — application 包 test_package 臆测 stdin 管道用法导致 conan create 必炸

## 错误特征
```
main() is not defined
ERROR: picoc/2.1 (test package): Error in test() method ...
```
或泛化形态：test() 以 `echo '...' | <binary> -` 冒烟，被测 CLI 立即以非零退出，
`self.run` 抛错，conan create 在 [test package] 阶段失败。

## 触发条件
- 构建系统: 任意（application / package_type="application" 包）
- 阶段: conan create 的 test_package test()
- 场景: 为解释器/REPL 类工具编写 L1 测试时，未读上游入口即假设存在"从 stdin 读程序"模式

## 根因分析
很多 CLI 的 `-` 只是**程序参数分隔符**而非 stdin 开关：picoc 的 usage（picoc.c）仅有
`picoc <file.c>... [- <args>]`、`picoc -s <file.c>`（脚本模式）、`picoc -i`（交互）三种，
`picoc -` 文件列表为空时直接走 PicocCallMain → "main() is not defined" 退出 1。
管道内容根本不会被消费。作者连续改 test_package 而不下钻上游 usage，形成调参螺旋
（实测 6 个重复 fix 提交）。

## 解决方案

### 推荐方案
1. 先读上游 main/usage 文案确定合法调用形态；
2. 提交**真实输入文件**（如 `test_package/smoke.c`）——同时满足 L0e 测试源文件要求；
3. test() 用 `self.run(f'"{bin}" "{input}" | grep -q "<断言串>"', env="conanrun")`：
   管道退出码取最后命令，输出不符即非零被 conan 拦截（R34 实质执行被测二进制 + PF3 合规）；
4. 注意 OHPCD conan 2.29.1 fork 的 `ConanFile.run()` 无 `output=`/`capture_output=`
   关键字（签名：command/stdout/cwd/ignore_errors/env/quiet/shell/scope/stderr），
   需要断言输出时走管道 grep 或重定向文件 + `conan.tools.files.load`。

### 禁止做法
- ❌ 臆测 `echo | binary -` / `binary --version` 等未经源码证实的用法
- ❌ test() 只 print 不执行二进制（PF3/R34 空壳拦截）
- ❌ 连续改测不动手读上游入口（R43 调参螺旋）

## 验证
```bash
# 上游合法形态确认（以 picoc 为例）：
grep -n "Format:" picoc.c   # 打印 usage；无 stdin 模式即为命中本模式
# 修复后：conan create 全绿且 RUN 行含管道断言
```

## 关联
- 软件/版本: picoc 2.1（test_package 重做，notes.md §8）
- 规则: R34 / PF3 / L0e / R43
