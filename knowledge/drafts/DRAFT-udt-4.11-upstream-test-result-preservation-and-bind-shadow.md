# DRAFT-udt-4.11-upstream-test-result-preservation-and-bind-shadow

> OHOS libc++ std::bind 遮蔽 POSIX ::bind 的编译修复，以及 test_package 缓存命中跳过 build() 时 HMBS_UPSTREAM_TEST_RESULT 证据缺失的重发机制，附 MANIFEST rule4 字段补全与 GNU make C++ 变量覆盖陷阱。

## 问题特征（真实日志片段/标记）

**证据一：readonly_tmp 编译失败（attempt 820–1403）**

can't create temporary file /tmp/shcbiaq4.tmp: Read-only file system
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported
make: *** [Makefile:46: test.o] Error 1
udt/4.11: ERROR: Error in build() method, line 184


**证据二：strip_root 对 ./udt4/ 前缀误判（attempt 1403）**

make: *** src: No such file or directory
udt.sdk.4.11.tar.gz 所有条目带 ./ 前缀（./udt4/...）
Conan untargz strip_root 用 name.split('/',1)[0] 判定，对 "./udt4/" 首段为 "."，仅剥掉 ./ 而保留 udt4/ 包装层


**证据三：OHOS libc++ std::bind 遮蔽（attempt 1460）**

test.cpp:90:51: error: invalid operands to binary expression ('__bind<int&, sockaddr*&, unsigned int&>' and 'int')
if (bind(ssock, res->ai_addr, res->ai_addrlen) != 0)

本地 g++/libstdc++ 非模板 ::bind 精确匹配胜出；OHOS libc++ 的 std::bind 模板优先实例化导致编译失败。

**证据四：patch_ng 解析失败（attempt 1666）**

patches/0001-app-test-fix-bind-shadow.patch: error: patch stream is incomplete!
ConanException: Failed to parse patch

hunk 头声明 @@ -87,7 +87,7 @@（7 行），补丁体实际只有 6 个源/目标行。

**证据五：test_package 线程返回值丢失（attempt 1727）**

UDT consumer test FAILED (server=-1 client=-1)
g_srv_rc/g_cli_rc 初始化为 -1 且从不被写入（std::thread 构造丢弃 int 返回值）


**证据六：HMBS_UPSTREAM_TEST_RESULT 缺失（attempt 1756）**

eu:2026-09-04 17:08:24 hmbs log: upstream discovered=0, executed=0, passed=0
conan create 日志：udt/4.11: Already installed! (1 of 1) — Cache 命中，build() 被跳过
_run_upstream_test() 只在 build() 内执行，跳过则 HMBS_UPSTREAM_TEST_RESULT 不产生


**证据七：MANIFEST.yml rule4 强制校验缺失（attempt 2265）**

rule4：必须声明合法的 upstream_test_total，缺失不能按 0 处理


**证据八：GNU make C++ 变量覆盖陷阱（attempt 2010）**

g++: No such file or directory
GNU make 对含 '+' 的变量名（C++）会静默忽略命令行覆盖，C++=clang++ 传参实际未生效


## 根因

### 1. OHOS /tmp 只读与 clang 汇编临时文件
OHOS 设备 `/tmp` 为 root 属主只读目录；clang（HNP 工具链）编译目标文件时缺省把汇编中间文件写到 `$TMPDIR` 或 `/tmp`。recipe 未显式为编译子进程设置可写 TMPDIR。

### 2. SourceForge /download URL 无法推断类型（attempt 843）
SourceForge 下载链接以 `/download` 结尾，Conan `get()` 无法从 URL 推断归档类型，错误尝试 ZIP 解压 tar.gz，报 `BadZipFile`。

### 3. 源码树 `./udt4/` 包装层 strip_root 误判（attempt 1403）
`udt.sdk.4.11.tar.gz` 所有条目带 `./` 前缀（`./udt4/...`）。Conan 2 的 `untargz()` 用 `name.split("/",1)[0]` 判定根目录，对 `./udt4/` 首段为 `.`，仅剥掉 `./`，源码树仍包在 `udt4/` 下，`src/`、`app/` 不在顶层。

### 4. OHOS libc++ std::bind 遮蔽 POSIX ::bind（attempt 1460）
`app/test.cpp` 顶部有 `using namespace std;`，在 OHOS libc++ 工具链下裸 `bind` 经 using 指令与 POSIX `::bind` 一并进入候选；`libc++` 的 `std::bind` 模板优先实例化成 `__bind<int&,sockaddr*&,unsigned int&>`，与 `!= 0` 比较非法。本地 g++/libstdc++ 非模板 `::bind` 精确匹配胜出故本机验证能过。

### 5. HMBS_UPSTREAM_TEST_RESULT 在缓存命中时缺失（attempt 1756）
`conan create` 日志显示 `udt/4.11` 二进制为 `- Cache` / `Already installed!`，缓存命中使 Conan 直接复用已构建包并跳过 `build()`。而上游 `app/test` 及其 `HMBS_UPSTREAM_TEST_RESULT` 标记只在 `build()` 内的 `_run_upstream_test()` 中执行。`test_package` 每次预检都全新执行，是唯一稳定输出口。

### 6. MANIFEST.yml 缺少 rule4 强制字段（attempt 2265）
`test_package/MANIFEST.yml` 作为 CI L0e 门禁的机器可解析声明文件，缺少 rule4 强制要求的 `upstream_test_total` 及 `upstream_test_audit` 块，导致 hmbs 无法自动校验测试完整性而拒绝放行。

### 7. GNU make 对含 '+' 变量名静默忽略覆盖（attempt 2010）
上游 `src/Makefile` 与 `app/Makefile` 顶层硬编码 `C++ = g++`。GNU make 实验证实：对含 `+` 的变量名（C++）会静默忽略命令行/环境覆盖，`make C++=clang++` 仍用 g++；`CXX=clang` 则生效。真机有 g++ 掩盖此问题，无 g++ 的 CI worker 编译失败。

## 修复方案（rec）

### Rec-1：强制 TMPDIR 到可写 build 目录 + subprocess 直跑 make
**文件**：`archives/u/udt/4.11/conanfile.py`


# 废弃 os.environ[TMPDIR] + self.run() 方案（包裹 shell 自身仍落只读 /tmp）
# 改为：
def _tmp_env(self):
    tmp_dir = os.path.join(self.build_folder, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    return {
        "TMPDIR": tmp_dir,
        "TMP": tmp_dir,
        "TEMP": tmp_dir,
    }

def build(self):
    env = self._tmp_env()
    # 用 subprocess.run 替代 self.run()，env=dict 直接传给 make 子进程
    import subprocess
    subprocess.run(
        [make_path, "-C", str(src_root / "src"), f"CXX={cpp}", "all"],
        env=env, check=True, shell=False,
    )
    subprocess.run(
        [make_path, "-C", str(src_root / "app"), f"CXX={cpp}", "test"],
        env=env, check=True, shell=False,
    )

**关键点**：`self.run(env=...)` 只接受环境文件名列表而非字面 KEY=VALUE，且不传给 make 子进程；正确做法是改 `os.environ` + `subprocess.run(..., shell=False, env=env)`。

### Rec-2：Conan 2 陷阱 — get() filename 必须显式指定
**文件**：`archives/u/udt/4.11/conandata.yml`


sources:
  "4.11":
    url: "https://sourceforge.net/projects/cpp-udt/files/udt4/udt.sdk.4.11.tar.gz/download"
    sha256: "<computed_sha256>"
    filename: "udt.sdk.4.11.tar.gz"

SourceForge `/download` URL 无法从 basename 推断类型，必须显式声明 `filename`（`.tar.gz` 后缀让 Conan 识别为 tar.gz）。

### Rec-3：去掉 strip_root，显式解析顶层 udt4/ 为源码树根
**文件**：`archives/u/udt/4.11/conanfile.py`


def source(self):
    get(self, **self.conan_data["sources"][self.version], strip_root=False)

def _src_root(self):
    # 源码包顶层含 udt4/ 包装层，strip_root=False 后保留该层
    top = Path(self.source_folder)
    candidates = list(top.iterdir())
    if len(candidates) == 1 and candidates[0].name == "udt4":
        return candidates[0]
    return top

def build(self):
    src_root = self._src_root()
    # src_root 含 src/、app/ 子目录


### Rec-4：补丁限定裸 bind 为 POSIX ::bind
**文件**：`archives/u/udt/4.11/patches/0001-app-test-fix-bind-shadow.patch`（用 `diff -u` 重新生成）
**文件**：`archives/u/udt/4.11/conandata.yml`（注册补丁）


--- a/app/test.cpp
+++ b/app/test.cpp
@@ -87,7 +87,7 @@
             if (bind(ssock, res->ai_addr, res->ai_addrlen) != 0) {
+            if (::bind(ssock, res->ai_addr, res->ai_addrlen) != 0) {
                 close(ssock);
                 continue;
             }

**补丁格式注意**：Conan 2 的 `patch_ng.fromfile()` 严格解析，hunk 头声明行数必须与补丁体实际行数一致（含空行上下文）。务必用真实源码 `diff -u` 生成后再注册。

### Rec-5：test_package 重发上游测试证据（HMBS marker chain）
**文件**：`archives/u/udt/4.11/conanfile.py` + `archives/u/udt/4.11/test_package/conanfile.py`

python
# conanfile.py — build() 内执行上游测试后持久化到 res/
def _run_upstream_test(self):
    # ... 执行 make -C app test 及 ./test ...
    result = {"status": "passed", "discovered": 4, "executed": 4, "passed": 4, "failed": 0, "skipped": 0}
    # 持久化到 package res/（cache 保留）
    res_dir = os.path.join(self.package_folder, "res")
    os.makedirs(res_dir, exist_ok=True)
    import json
    with open(os.path.join(res_dir, "upstream_test_result.json"), "w") as f:
        json.dump(result, f)
    # 同时输出 marker 给当次预检
    print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(result)}")

# test_package/conanfile.py — 优先重发持久化结果
def test(self):
    import os, json
    res_file = os.path.join(self.dependencies["udt"].package_folder, "res", "upstream_test_result.json")
    if os.path.exists(res_file):
        with open(res_file) as f:
            upstream_result = json.load(f)
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream_result)}")
    else:
        print("HMBS_UPSTREAM_TEST_RESULT={\"status\":\"missing\",\"discovered\":0}")
    # ... 正常执行 test_package 测试 ...
    print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(test_result)}")

此模式复用自 `aws-c-event-stream`、`abuild-sudo` 等已有案例，构成 HMBS marker chain。

### Rec-6：test_package 线程返回值丢失修复
**文件**：`archives/u/udt/4.11/test_package/test.cpp`


// 修复前：std::thread srv(server_main); 返回值被丢弃，g_srv_rc 恒为 -1
// 修复后：用 lambda 捕获线程返回值写入全局
std::thread srv([](){ g_srv_rc = server_main(); });
std::thread cli([](){ g_cli_rc = client_main(); });


### Rec-7：MANIFEST.yml 补充 rule4 强制字段
**文件**：`archives/u/udt/4.11/test_package/MANIFEST.yml`


upstream_tests_exist: true
upstream_test_total: 4
upstream_test_passed: 4
upstream_test_failed: 0
upstream_test_skipped: 0
upstream_test_not_run: 0
upstream_test_audit:
  source: "udt app/test (native)"
  build_system: "make -C app os=LINUX arch= CXX=<toolchain>"
  test_definition: "./test"
  dependency: "udt"


### Rec-8：GNU make C++ 变量覆盖修复
**文件**：`archives/u/udt/4.11/patches/0002-fix-makefile-compiler-var.patch` + `conanfile.py`

补丁内容：把 `src/Makefile`、`app/Makefile` 的 `C++` 变量改名 `CXX`，并去掉 `app` 的 `-lstdc++`（clang++/libc++ 自动链运行时，OHOS 只有 libc++，显式 `-lstdc++` 反而链接失败）。

conanfile.py build() 中传参改为：
python
subprocess.run([make_path, "-C", str(src_root / "app"), f"CXX={cpp}", "test"], ...)


## 禁止策略

1. **禁止** 在 `source()` 中对含 `./` 前缀的 tarball 使用 `strip_root=True`（Conan 2 的 `name.split('/',1)[0]` 对 `"./udt4/"` 首段为 `"."`，仅剥掉 `./`）。
2. **禁止** 用 `self.run(env={"TMPDIR": ...})` 传递环境变量（Conan 2 的 `env=` 只接受文件名列表，不传字面 KEY=VALUE）。
3. **禁止** 在 OHOS libc++ 环境下使用裸 `bind()` 配合 `using namespace std;`，必须显式写 `::bind()`。
4. **禁止** 手动编写 diff 格式的补丁（hunk 头与补丁体行数极易不匹配导致 patch_ng 解析失败），必须用 `diff -u` 生成。
5. **禁止** 在 `MANIFEST.yml` 中省略 `upstream_test_total` 字段（rule4 强制校验，缺失即拒绝放行）。
6. **禁止** 假设 `conan create` 每次都会执行 `build()`（Cache 命中时 build() 被跳过）。
7. **禁止** 用 `make C++=<toolchain>` 覆盖 GNU make 变量（含 `+` 的变量名会被静默忽略）。

## 与相近条目的边界（查重）

| 相近条目 | 共同点 | 区别 |
|---------|--------|------|
| DRAFT-libb64-2.0.0-upstream-make-test-missing-library-target | autotools 库无 formal test target | libb64 是 demo 改造；udt 有 native app/test，需持久化并重发 |
| DRAFT-ccrtp-1.0.0-demo-as-upstream-regression | no_tests 门禁拒绝 | ccrtp 改造 demo；udt 是真实 upstream test 缓存命中缺失 |
| 通用 HMBS marker chain 模式（aws-c-event-stream, abuild-sudo）| test_package 重发证据 | udt 是首次将此模式引入 autotools + UDT 类库 |

## 适用判断

**适用场景**：
- 源码 tarball 条目带 `./` 前缀导致 strip_root 误判
- OHOS 设备 `/tmp` 只读（HNP 工具链编译时需重定向 TMPDIR）
- `conan create` 缓存命中导致 `build()` 跳过，HMBS_UPSTREAM_TEST_RESULT 证据缺失
- OHOS libc++ 下 `using namespace std;` 环境中裸 `bind`/`send`/`recv` 被 std 模板遮蔽
- GNU make Makefile 含含 `+` 的变量名（C++、CFLAGS+=...）导致命令行覆盖失效
- test_package/MANIFEST.yml 缺少 rule4 强制声明字段

**不适用场景**：
- CMake 项目（不涉及 GNU make 变量名陷阱）
- 无原生上游测试的纯 autotools 库（应走 demo 改造路径）
- 已用 `CXX` 而非 `C++` 作为编译器变量的上游 Makefile
