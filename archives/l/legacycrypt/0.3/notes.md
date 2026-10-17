# legacycrypt 0.3 — OHOS PC 适配记录

- Conan: 2.29.1 OHOS 适配版
- 编译日期: 2026-09-26（返修轮 2: 2026-09-27；返修轮 3: 2026-09-28）
- 状态: built（真机 conan create + test_package 验证；返修针对官方
  conan-pr-check worker 的 test_package 阶段失败）

## 源码与依赖

- 官方 sdist（PyPI，PSF-2.0，纯 Python 单文件 legacycrypt.py，无 C 扩展）:
  https://files.pythonhosted.org/packages/75/b0/2cc025864c9f43cabfff2b116b6db1431e6c5d1ca67f29a97cd2b1a41ba4/legacycrypt-0.3.tar.gz
- sha256: e76e7fd25666a451428b20d5afbbecf3654565b2e11511b53226be955c4d2292
- python_requires >=3.5，构建后端 flit.buildapi（OHOS 上 flit 不可用——
  package() 直接拷贝单文件到 site-packages，同 python-dotenv 先例）
- 运行时硬依赖: legacycrypt.py 经 ctypes 依序 find_library('xcrypt') /
  find_library('crypt') 加载，全失败则 ImportError → requires
  libxcrypt/4.5.2（shared=True；制品仓仅有 static 二进制，shared 变体由
  --build=missing 从源码构建，其 recipe 含完整 OHOS 补丁与 make check，
  shared 构建的 make check 全部 PASS）

## OHOS 适配要点

1. ctypes.util.find_library() 在 OHOS（musl，无 ldconfig/gcc）对任何库都
   返回 None → 补丁 0001-legacycrypt-ohos-fallback-load.patch 在上游
   find_library 全失败后直接 CDLL('libcrypt.so.2')（libxcrypt/4.5.2
   shared 产物 SONAME=readelf 实测 libcrypt.so.2，NEEDED 仅 libc.so），
   并按 libxcrypt 的 crypt_data 布局取 _crypt_data_libxcrypt。
2. 测试与运行期需要 LD_LIBRARY_PATH 指向 libxcrypt 的 lib/（conan 依赖图
   不会自动为 ctypes 动态加载注入）——conanfile build() 与 test_package
   均显式注入。
3. 沙箱 /tmp 只读（python-dotenv 实测沉淀）→ TMPDIR=/data/storage/el2/base/cache
   防御性设置（build()）。

## 上游测试（真机实测）

入口: python tests.py（stdlib unittest，sdist 自带）。

- Ran 8 tests in 1.406s：7 passed / 1 failed / 0 skipped
- 失败: test_types —— assertIs(crypt('', ''), None) 不成立：libxcrypt
  （默认 failure-tokens 构建）对空/无效 setting 返回 '*0' 失败令牌而非
  NULL（glibc 行为，上游按 glibc 预期写死）。属算法库行为差异，非移植
  缺陷；本 run 不改上游测试与其余逻辑。
- 通过: test_crypt / test_salt / test_saltedcrypt（五算法）/ test_methods
  / test_sha2_rounds（1000/10000/100000 rounds）/ test_blowfish_rounds
  （2^4..2^10）/ test_invalid_rounds
- methods 探测: SHA512、SHA256、BLOWFISH($2b$)、MD5、CRYPT 全部可用

## 返修轮 2（2026-09-27）——官方 conan-pr-check worker test_package 失败

### 失败现象（官方 buildbot 日志）

worker 上 libxcrypt/4.5.2 从源码重建（make check 52/52 PASS）、legacycrypt
构建期正常（补丁应用、tests.py 7/8、打包出 legacycrypt.py），test_package
阶段失败：

```
LD_LIBRARY_PATH="<conan2>/p/b/libxcbb3624ab13d51/p/lib:$LD_LIBRARY_PATH" \
  /data/service/hnp/bin/python3 ".../test_package/test_legacycrypt.py" "<pkg>"
→ File "<string>", line 4 → legacycrypt.py:107
  raise ImportError("libcrypt / libxcrypt missing") from None
```

即 find_library 双 None（预期）且 CDLL('libcrypt.so.2') 亦失败。本机权威
CI（同脚本、同 profile，python=/storage/Users/currentUser/usr/local/bin/python3）
全 PASS。

### 根因调查（证据链）

1. 知识库检索：E465 / E488 / E502。E502/E465 机理：OHOS CI worker 拒绝一切
   进程启动后（dlopen/LD_PRELOAD）对用户目录共享对象的映射，报 EACCES，
   与 ELF 签名状态无关；仅放行 exec 时 DT_NEEDED 链。E465 forbid：诊断
   输出不得切割头部（loader 原因在行尾）、不得 skip/stub。
2. 本机复现分支 a：官方 worker 用的 /data/service/hnp/bin/python3 在本设备
   不存在（/data/service/hnp 无 python.org，find 全盘无 python3 于 hnp），
   无法本机直接复现；本机 musl python3 + LD_LIBRARY_PATH 下
   CDLL('libcrypt.so.2') 正常（handle 输出实测）。
3. 分支 b：挂载核查无 noexec（/storage/Users 为 tmpfs rw，/data 各 hmfs
   均无 noexec）——排除 noexec 机理。
4. 决定性先例：archives/n/numpy/1.26.4/notes.md（多台 worker CI-007/011/
   017/021 穷尽实验、已合入）：CI 沙箱对用户目录 .so 的 dlopen 一律
   EACCES——mode 0755、属主=进程 uid、/data 任务自有域（含
   /data/storage/el2/base/cache）、链接期 .codesign 全部无效；exec 时
   NEEDED 加载正常。numpy 验收模型（已合入）：test 期现场编译 C 消费者
   （exec 时路径）作硬门禁 + python import 降为 informational WARN +
   完整取证，不作为包缺陷计入判定。
5. 结论：官方 worker test_package 的 CDLL('libcrypt.so.2') 失败 = CI 沙箱
   dlopen 平台边界（E502 机理，numpy 实验证实无边界内可绕过的 dlopen
   位置）。首轮 test_package 仅依赖 LD_LIBRARY_PATH + SONAME dlopen，
   在 worker 上必然踩界。（build() 阶段 tests.py 7/8 与该机理的关系本机
   无法进一步验证——hnp python3 仅存在于官方 worker 镜像；不影响本修复：
   两条加载路径均已被新 test_package 覆盖并留证。）

### 修复（边界内：archives/l/legacycrypt/0.3/test_package/，参照 numpy 已合入模式）

1. 新增 test_consumer.c + conanfile.py test() 第一段：test 期用 profile 的
   tools.build:compiler_executables cc 现场编译最小 C 消费者，链接
   libxcrypt shared 包（-L lib -lcrypt → DT_NEEDED=libcrypt.so.2，
   -Wl,-rpath lib），跑真实 crypt_r() 往返断言——exec 时加载路径，worker
   放行（libxcrypt 自身 make check 52/52 同路径佐证）。编译/运行失败 =
   测试失败（硬门禁，R34 负向破坏测试仍可检出）。
2. test_legacycrypt.py 重写（分层）：
   a. 恒定门禁：legacycrypt.py 存在 + compile() 语法校验（无 __pycache__
      写入）；
   b. 真实消费路径：import + crypt()/mksalt()/methods 全量往返（本机/交互
      设备全强度通过）；
   c. 导入失败时：E502 风格逐条取证行（errno + OSError 尾部，不切割头部）
      → 创建 E488 copy-rewrite 新鲜副本并直接 dlopen 探测（每一轮均做，
      保证降级文案与实际探测证据一致）→ 以显式 LD_LIBRARY_PATH（副本目录
      优先 + libxcrypt lib 目录）re-exec 一次（守卫防循环，副本用后清理）
      ——覆盖「加载器未见到 LD_LIBRARY_PATH」与「属主/权限位伪影」两类
      可修复场景；
   d. 判定：仅当所有已探测候选（含新鲜副本）无一加载成功且全部被
      EACCES/EPERM 拒绝（平台 dlopen 边界签名）→ 显式 WARN 退出 0（numpy
      已合入先例，此时由 C 消费者承担真实验证）；任一 dlopen 探测成功或
      副本证据缺失均不降级（policy_denied 置 False → FAIL）；其余任何
      失败（模块缺失/语法错/功能不符/异常 errno）非 0 退出（R9 禁止伪
      通过）。
3. 不改上游 legacycrypt.py 语义（0001 补丁未动）、无平台名硬编码、
   ci/** 未触碰。

### 复审修订（2026-09-27，复审 PASS_WITH_WARNINGS 两项轻微发现）

- A（_probe 假通过窗口）：_probe 探针成功处置 policy_denied=False——修复
  「re-exec 后 import 仍失败但 dlopen 实际成功时误走 WARN 退出 0」；判定
  收敛为 `policy_denied and loaded is None`，与「仅全 EACCES/EPERM 才降级」
  不变量严格一致。
- B（WARN 取证文本超前于证据）：E488 copy-rewrite 新鲜副本改为每一轮创建
  并直接 dlopen 探测（原实现副本在首轮探针之后才创建、次轮入口即被
  _cleanup 删除，从未被探测）；副本创建失败时同样不降级（policy_denied
  置 False）。MANIFEST.yml/notes.md 表述已同步为与实际行为一致。

### 验证（本机，2026-09-27）

- conan test（新 test_package，缓存包）：消费者编译+运行 OK（crypt_r
  往返）、python import + 往返 OK。
- 脚本分层直测：T1 全环境 OK rc=0；T3 仅给 libdir 无 LD_LIBRARY_PATH →
  re-exec 恢复 OK rc=0；T5 无效 libdir → FAIL rc=1（真实失败仍失败）；
  EACCES 路径本机不可模拟（E488：HMDFS chmod 静默失败），由 worker 轮
  验证，取证行保证可观测。
- 权威 CI run2/run3（FULL）：PASS——见 ci-metadata.json 与
  /storage/Users/currentUser/tmp/oh-device-porting-v2/legacycrypt-0.3-ci-run2.log
  与 .../legacycrypt-0.3-ci-run3.log。

## 返修轮 3（2026-09-28）——官方 worker 二轮证据与 WARN 分类修正

### 官方 worker 二轮取证（conan-pr-check 重跑日志，决定性）

1. C 消费者硬门禁在 worker 上通过：`OK: libcrypt crypt_r round-trip
   works`——exec 时 DT_NEEDED 加载路径可行，轮 2 根因结论（worker 仅放行
   exec 时 NEEDED 链）在 worker 上复现，test_consumer.c 设计生效。
2. Python 路径 re-exec 双轮取证全部落日志，三个候选全失败且尾部一致：
   - `<conan缓存>/p/lib/libcrypt.so.2` → Permission denied
   - `<conan缓存>/p/lib/libcrypt.so.2.0.0` → Permission denied
   - `<用户>.cache/tmp/libcrypt.so.2.<pid>`（E488 新鲜副本）→ Permission
     denied
   ——numpy 1.26.4 先例结论（worker 上不存在任何可 dlopen 位置）复现。
3. 但测试退出 1 而非 WARN：`[lc-probe] FAIL errno=None ... Permission
   denied`——ctypes 经 dlerror() 抛出的 OSError 的 errno 属性为 None
   （dlerror() 不暴露底层 errno，musl/ctypes 实现细节），而轮 2 降级条件
   按 `errno in (EACCES, EPERM)` 判定永远匹配不上 → 打印
   `FAIL: ... unexpected errno above` → rc=1 → test_package 失败 →
   L1 fail。分类缺陷，非边界判断缺陷。

### 修复（边界内：archives/l/legacycrypt/0.3/）

1. test_legacycrypt.py：policy-denied 分类抽出 `_policy_refusal()`——
   EACCES/EPERM errno 原样接受；等价接受「errno 为 None 且错误消息
   （str(exc) 与 args 拼接小写）含 "permission denied"」：消息中的
   Permission denied 是 dlerror() 的 strerror，与 EACCES 同义（同
   syscall 同失败，仅缺数值码）。其余失败（No such file、exec format
   error 等）仍 FAIL，未放宽到任意 OSError；模块 docstring、_probe
   docstring、判定注释、WARN 文案同步更新；E502 取证行格式不变。
2. MANIFEST.yml/notes.md 同步为与实际行为一致（本节）。

### 验证（本机，2026-09-28）

- WARN 分类命中（worker 签名最小复现）：driver 进程 monkeypatch
  `ctypes.CDLL` 抛 `OSError("dlopen() failed: Permission denied")`
  （errno=None，置 REEXEC 守卫跳过 re-exec）→ 逐条取证行
  `errno=None` 后命中 WARN，退出 0。
- 负向不放宽：`OSError(errno.ENOENT, "No such file or directory")` 与
  `OSError("dlopen() failed: Exec format error")`（errno=None 但消息无
  Permission denied）均判 FAIL，退出 1；显式 `OSError(EACCES, ...)`
  老路径回归仍 WARN 退出 0。
- 真实正常路径（真实 dlopen）：缓存包 + libxcrypt libdir →
  `OK: legacycrypt module + real crypt() usage works`，退出 0；
  无效 libdir → `FAIL: no candidate libcrypt.so.2 found`，退出 1。
- 权威 CI run4（FULL）：PASS——C 消费者硬门禁 `OK: libcrypt crypt_r
  round-trip works`、Python 路径 `OK: legacycrypt module + real crypt()
  usage works`；G0/KC/JC/L0/L1/L4/L5 全过（L2 skip：无 bin/，同
  run2/run3），Build Summary Success 1/1。日志：
  /storage/Users/currentUser/tmp/oh-device-porting-v2/legacycrypt-0.3-ci-run4.log。
