# E900: pin-interpreter-script-in-makefile

## 基本信息
- **严重度**: 2
- **类别**: portability, perl, build-system, autotools
- **状态**: draft（待主编审核）

## 错误特征
```
bad interpreter: //bin/perl|Perl lib version .* doesn't match executable|Compilation failed in require at .*pod2man|Can't locate strict.pm in @INC .* //lib
```

## 根因分析
autotools Makefile 裸调 `pod2man` / `pod2html` 生成 man/html 文档。在 OHOS conan 构建环境里会踩两条互斥的死路：

1. PATH 上解析到系统（HNP）pod2man，而 conan perl 包的 buildenv 注入了 PERL5LIB → 系统 perl 加载 conan perl 的 Config.pm 时版本断言失败（5.42.0 vs 5.42.2），`BEGIN failed--compilation aborted`。
2. 反过来用 conan perl 包自带的 pod 工具，其 shebang 是损坏的 `#!//bin/perl`（perl 包重定位缺陷），`bad interpreter` Error 126。

## 推荐方案
**方法**: pin-interpreter-script-in-makefile

**说明**: 在 `bash config.status` 之后、`make` 之前，程序化改写生成的 Makefile，把
`\tpod2man ` → `\t"<perl绝对路径>" "<pod2man脚本绝对路径> "`（pod2html 同理）。
用解释器直接执行脚本，既绕过损坏的 shebang，也不赌 PATH 顺序。实测案例：
rsnapshot 1.5.1（conanfile.py build() 方法）。

**验证**:
```
conan create 后 make 日志应出现 "/…/p/perl…/p/bin/pod2man" 且无版本断言错误
```

## 禁止策略
- 禁止直接执行 conan perl 包的 pod 工具脚本（shebang `#!//bin/perl` 必失败）
- 禁止在系统 perl 上叠加 conan perl 的 PERL5LIB（Config.pm 版本断言中止编译）

## 相关条目
similar_to: E049（shebang 可移植化）、E155（纯 perl 包构建）、E116（automake perl 模块）
