# E545 — PMIx 5.x 端到端测试必须走 simptest server 模式（PMIx_Init 无服务器返回 UNREACH）

## 错误特征
- test_package 里 `PMIx_Init()` 返回 `-25 (PMIX_ERR_UNREACH)` 而非 PMIX_SUCCESS
- 误判为适配失败/链接错误的排障时间浪费
- test() 中跑 pmix 工具无超时控制、拿不到输出（适配版 conan run() 限制）

## 触发条件
- 构建系统: autotools（库本体）+ Conan test_package
- 阶段: testing（conan create 的 test 阶段）
- 软件: PMIx / openpmix 5.x（PMIx Standard 5.x API）

## 根因分析
PMIx 是 client/server 架构。客户端 PMIx_Init 依赖父进程（资源管理器/RM）注入的
PMIX_* 环境变量。test_package 独立进程里没有 server，PMIx_Init 按设计返回
PMIX_ERR_UNREACH(-25)。上游 `test/simple/simptest.c` 给出了标准测法。

关键 API 事实：
- `PMIx_server_init(NULL, NULL, 0)` —— **5.x 是 3 参数**（attrs, proc_map, ninfo），
  4.x 的 2 参数写法在 5.x 编译报错
- `PMIx_server_register_client(&proc, uid, gid, NULL)` → 0
- `PMIx_server_setup_fork(pid, &env)` → 生成子进程环境数组
- 子进程 `putenv(env[i])` 后 `PMIx_Init()` → PMIX_SUCCESS，nspace/rank 合法
- 版本冒烟：`pmix_info --version` 只打印帮助文本（src/util/pmix_cmd_line.c:175 上游设计），
  断言用无参数输出的 `PMIX: 5.0.11` 行或 `PMIx_Get_version()` 返回串

另：OHOS 适配版 conan 2.29.1 的 `ConanFile.run()` 签名为
`run(command, stdout=None, cwd=None, ignore_errors=False, env="", quiet=False, shell=True, scope="build", stderr=None)`
——**无 timeout 参数、只返回 retcode**，但 `stdout` 参数可接 `open()` 的文件对象捕获输出
（`stderr=subprocess.STDOUT` 合并）。且 CI L0d 门禁以 `grep "self\.run"` 判 stub_test_method——
test() 纯 subprocess.run 会被拦。正确写法：
`self.run(cmd, env="conanrun", stdout=f, stderr=subprocess.STDOUT, ignore_errors=True)`
后读文件解析断言行，配合 try/finally shutil.rmtree 与
`HMBS_TEST_PACKAGE_RESULT: total=N passed=N` 输出行（pmix 实测 5/5）。

## 解决方案

### 推荐方案（simptest 范式，8 断言全过）
```
parent: PMIx_server_init(NULL,NULL,0)==PMIX_SUCCESS
        PMIx_server_register_client(...)==0
        PMIx_server_setup_fork(pid,&env)==0 → fork
child:  putenv(env) → PMIx_Init==PMIX_SUCCESS (nspace/rank 合法)
        PMIx_Finalize==PMIX_SUCCESS → exit(0)
parent: waitpid==0 → PMIx_server_finalize==0
```

### 回退方案
符号/布局/版本冒烟（nm + pmix_info "PMIX:" 行 + 布局断言），notes.md 声明降级原因。

### 禁止做法
- ❌ 无 server 直接断言 PMIx_Init==SUCCESS（恒 UNREACH，会演变成空壳测试，R34 红线）

## 验证
```bash
grep -n "PMIx_server_init" test_package/test_pmix.c   # 3 参数
grep -n "subprocess" test_package/conanfile.py        # timeout 控制
conan create archives/p/pmix/5.0.11 -pr:h=... --build=missing  # HMBS_TEST_PACKAGE_RESULT: total=8 passed=8
```

## 关联条目
- 参考: 上游 test/simple/simptest.c；R34（test 必须实质依赖被测包）
