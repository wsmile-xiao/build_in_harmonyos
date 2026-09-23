# E2180 — Conan 自定义 env 脚本命名 conanbuild 与聚合启动器自引用导致 SIGSEGV(Error -11)

## 错误特征
conan create 在 build() 阶段报 `ERROR: ... Error -11 while executing`,无任何编译输出;
在构建目录手动 `source conanbuild.sh` 后 shell 立即被信号杀死。

## 触发条件
- 构建系统: conanfile.py(任意),build() 依赖 env 脚本注入编译器
- 阶段: generate/build(conanbuild.sh 生成与执行)

## 根因分析
conanfile.generate() 中 `env.vars(self).save_script("conanbuild")` 生成的脚本与 Conan
自身聚合启动脚本同名。Conan 聚合器写出的 conanbuild.sh 内容为
`. conanbuild.sh && . conanbuildenv-<cfg>.sh` —— 脚本 source 自身,无限递归栈溢出,
build 子进程以信号 11 死亡。

## 解决方案

### 推荐方案
不要把自定义 env 脚本命名为 conanbuild。向裸 Makefile 传编译器/标志时,在 build() 里
从 `self.conf.get("tools.build:compiler_executables")` 读出后直接拼进 `self.run()` 命令行,
跳过 env 脚本层。

### 禁止做法
- ❌ save_script("conanbuild") / 其他与 Conan 内建聚合脚本同名("conanrun" 同理需核查)

## 实证
chiark-utils/8.0.1 适配:5 次 Error -11 定位为自引用;改为 conf 直读拼命令行后构建通过
(.ci_logs/chiark-utils-8.0.1-conan-create.log)。
