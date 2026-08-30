# DRAFT-sdl-kitchensink-1.0.13-ohos-elf-sign-sdl-headless-test

OHOS 下 Conan test_package 可执行测试需 ELF 签名 + SDL dummy 无头执行
SDL_kitchensink 1.0.13（CMake/C99，OHOS aarch64，Conan 2.29.1，clang 15）

- **ID**: DRAFT-sdl-kitchensink-1.0.13-ohos-elf-sign-sdl-headless-test
- **配对**: DRAFT-sdl-kitchensink-1.0.13-ohos-elf-sign-sdl-headless-test.kv
- **触发工具**: cmake / conan
- **阶段**: testing / packaging
- **严重度**: 🔴 blocking (3)（门禁会拦截，必须处理）
- **分类**: conan, cmake, testing, ohos, sdl2, elfsign

---

## 问题（Problem）

SDL_kitchensink 1.0.13 的 `test_package` 生成可执行消费者测试 `test_sdl_kitchensink`（调用 `Kit_GetVersion` / `Kit_GetSDLAudioFormatString` / `Kit_Init` / `Kit_Quit`）。在 OHOS aarch64 + Conan 2 下：

1. **ELF 签名缺失**：OHOS 上未经 `binary-sign-tool` 签名的 ELF 可执行文件无法运行（执行即失败）。直接 `self.run(bin)` 会因未签名而失败，W3/L1 门禁判定测试未执行。
2. **SDL 无头环境**：测试调用 SDL 初始化（`Kit_Init` 内部初始化 SDL），CI/无显示环境没有窗口/音频设备，未设 dummy 驱动时 SDL 初始化失败。
3. **L0d 门禁**：`test_package/conanfile.py` 的 `test()` 必须含 `self.run()` 实际执行逻辑，否则 CI 判定 `stub_test_method`（空壳测试）拦截。
4. **头文件路径**：kitchensink 公共头直接 `#include <SDL_*.h>`，而 sdl2 头在 `include/SDL2/`，消费者编译需把该路径透传（R06 已通过 `cpp_info.includedirs` 追加解决，见配对另一面）。

**错误特征**：`test_package ... Error in test() method` | `self.run` 执行失败/无输出 | `stub_test_method` | `SDL_VideoDriver` 初始化失败 | `binary not found`

---

## 根因（Root Cause）

- Conan 在 OHOS 上产出的测试可执行文件是 ELF；OHOS 安全模型要求代码签名（`binary-sign-tool sign -selfSign 1`）后才可加载执行，缺签名时测试无法运行。
- SDL2 应用在无显示/无声卡环境下需显式 `SDL_VIDEODRIVER=dummy` / `SDL_AUDIODRIVER=dummy` 才会走 stub 后端完成初始化。
- CI 的 L0d 门禁以 `test()` 内是否存在 `self.run()` 判断测试真实性，`cmake.test()`/仅打印类写法会被判空壳。

**影响范围**：OHOS/arm64 上任何「test_package 生成可执行测试、且测试程序依赖 SDL（或同类需初始化显示/音频的库）」的 Conan 配方；以及任何未签名 ELF 可执行测试在 OHOS 的运行验证。

---

## 方案（Solution）

在 `test_package/conanfile.py` 中：

1. `build()` 内用 `llvm-objcopy --remove-section .codesign` 清理旧签名（容忍失败），再用 `binary-sign-tool sign -inFile <bin> -outFile <tmp> -selfSign 1` 签名并移回，`chmod 755`。
2. `test()` 内 `os.environ` 设置 `SDL_VIDEODRIVER=dummy`、`SDL_AUDIODRIVER=dummy`，然后 `self.run("'<bin>'", env="conanrun")` 实际执行签名后二进制（真实调用库 API，断言版本/格式字符串/初始化）。
3. 测试源显式 `#include <SDL_audio.h>`（若用到 `AUDIO_S16LSB` 等宏），因为 kitchensink.h 不引入 SDL 头；SDL include 路径由配方 `cpp_info.includedirs` 追加 `sdl2 的 include/SDL2` 透传。

```python
def build(self):
    cmake = CMake(self); cmake.configure(); cmake.build()
    self._sign_elf(os.path.join(self.cpp.build.bindirs[0], "test_sdl_kitchensink"))

def _sign_elf(self, path):
    self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc="/data/service/hnp/bin/llvm-objcopy", f=path), ignore_errors=True)
    tmp = path + ".signed"
    self.run('{sg} sign -inFile "{f}" -outFile "{t}" -selfSign 1'.format(sg="/data/service/hnp/bin/binary-sign-tool", f=path, t=tmp))
    if os.path.exists(tmp):
        shutil.move(tmp, path)
    os.chmod(path, 0o755)

def test(self):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    self.run(f"'{os.path.join(self.cpp.build.bindirs[0], 'test_sdl_kitchensink')}'", env="conanrun")
```

---

## 验证（Validation）

- **R06 实际证据**：`conan create`（含 test_package）G2 通过；test 执行输出 `SDL_kitchensink version: 1.0.13`、`SDL_PIXELFORMAT_RGB24 -> ...`、`AUDIO_S16LSB -> AUDIO_S16`、`test sdl-kitchensink 1.0.13: OK`；断言 4 项 1/1 PASS；W3 build_and_test.sh 隔离下 1/1（日志 `archives/s/sdl-kitchensink/1.0.13/reports/conan-create.log` / `w3-r06-isolated.log`，SHA-256 `85d01a90…` / `ce386a37…`）。
- 签名证据：日志含 `binary-sign-tool sign ... -selfSign 1` + `add codesign section success`。
- 与既有 `DRAFT-cdogs-sdl-sdl2-conan-cmake-bridge`（SDL2 系 CMakeDeps 桥接）查重：本草稿聚焦「test_package 可执行测试的 ELF 签名 + SDL dummy 无头执行 + L0d self.run」子问题，正式图谱/草稿中无等价条目（查重日志 `reports/r08-dedup-search.log`，SHA-256 `3ea5b348…`）。

---

## 适用边界（Applicability & Limitations）

- 适用：OHOS/arm64 Conan 配方中 test_package 产出可执行测试、且测试依赖 SDL（或需显示/音频初始化）的场景；同样适用于任何需要 ELF 签名才能运行测试二进制的 OHOS 包。
- 不适用：纯库测试（无可执行文件）、Linux 主机测试（无需签名）、上游自带 CTest 且无需签名/无头化的场景。
- 局限：签名工具路径为 `/data/service/hnp/bin/`（环境特定，需按实际工具链调整）；dummy 驱动只验证「API 可调用/初始化成功」，不验证真实解码渲染行为（SDL_kitchensink 解码需真实媒体文件与渲染目标，不在 test_package 范围内）。

---

## 来源

- **源库**: SDL_kitchensink 1.0.13（katajakasa/SDL_kitchensink，tag 1.0.13）
- **本草稿**: DRAFT-sdl-kitchensink-1.0.13-ohos-elf-sign-sdl-headless-test
- **配对**: DRAFT-sdl-kitchensink-1.0.13-ohos-elf-sign-sdl-headless-test.kv
