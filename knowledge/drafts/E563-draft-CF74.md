# E563（draft）— ohpcd 发行 libcurl 为无 TLS 变体：测试专用 TLS curl 源码自建到任务私有 prefix

- **来源**: coeurl 0.3.2 HarmonyOS PC 适配
- **状态**: draft（待审，勿自行 promote）
- **关联**: E091/E119（linux/socket.h 与 sys/socket.h 冲突，本次以 CMake feature-test 形态命中）；E216（CMakeDeps 传递依赖数据缺口）；workflow §7.3（测试依赖私有 prefix 自建口径）

## 1. 现象

coeurl 0.3.2 上游 doctest 套件（flask testserver :5443 TLS）在设备上
16/17 用例失败，第一条真实错误：

```
../tests/requests_tls.cpp:22: ERROR: CHECK( r.error_code() == CURLE_OK ) is NOT correct!
  values: CHECK( 1 == 0 )        ← 1 = CURLE_UNSUPPORTED_PROTOCOL
```

同进程纯 http 套件（:5000）17/17 全过。而设备系统 `curl` CLI 对同一
TLS 服务器返回 200 —— 排除服务器/证书问题。

## 2. 根因（发行包能力边界）

对 conan 发行 libcurl/8.5.0 的三层取证：

| 检查 | 结果 |
| --- | --- |
| `strings libcurl.so \| grep 'OpenSSL/[0-9]'` | 0（无 TLS 后端版本串） |
| `nm -D libcurl.so \| grep SSL_` | 0（无 SSL 符号） |
| `readelf -d libcurl.so \| grep NEEDED` | 仅 `libc.so`（无 libssl） |
| `-o "libcurl/*:with_openssl=True" --build=never` | 解析到同一 package_id（options 无该开关） |
| `conan list "libcurl/*" -r=ohpcd` | 仅 libcurl/8.5.0 一个 ref |

结论：发行变体无 TLS 后端，`https://` 一律 `CURLE_UNSUPPORTED_PROTOCOL(1)`。
设备系统 curl 静态链接自带 TLS（`curl 8.8.0-DEV ... OpenSSL/3.0.12`），
但设备无共享 libcurl.so 与开发头文件，不能直接复用。

## 3. 修法（测试专用自建，不进包依赖链）

按 workflow §7.3「从源码构建该依赖到任务私有 prefix（仅测试用、不进包
依赖链）」：

1. 下载与发行版本一致的 `curl-8.5.0.tar.gz`（curl.se，SHA-256
   `05fc17ff…47e0cab8c3475add` 核对官方校验值）；
2. **autotools 不可行**（实测两连败，勿再走）：`config.sub` 不识别 ohos
   三元组；改用 gnu 三元组后 `config.status` 写 `$ac_tmp/subs1.awk` 报
   Permission denied（HMDFS 对 awk 临时文件的写入怪癖）；
3. **CMake 可行**（curl 官方支持）：

```sh
cmake -S . -B build-cmake -G Ninja \
  -DCMAKE_INSTALL_PREFIX="$TASK_DIR/test-prefix" \
  -DBUILD_CURL_EXE=OFF -DBUILD_TESTING=OFF \
  -DCURL_USE_OPENSSL=ON -DOPENSSL_ROOT_DIR="$HOME/.harmonybrew" \
  -DHAVE_LINUX_TCP_H=OFF \
  -DCURL_USE_LIBPSL=OFF -DUSE_LIBIDN2=OFF -DUSE_NGHTTP2=OFF -DCURL_ZLIB=OFF \
  -DCURL_DISABLE_LDAP=ON -DCURL_DISABLE_LDAPS=ON
ninja -C build-cmake -j1 && cmake --install build-cmake
```

   关键点：
   - `-DHAVE_LINUX_TCP_H=OFF`：绕开 `linux/tcp.h` → `linux/socket.h` 的
     `sockaddr_storage` 重定义（E091/E119 同根因；CMake feature-test
     形态的解法，非源码补丁）；
   - `-DOPENSSL_ROOT_DIR=$HOME/.harmonybrew`：设备 harmonybrew 自带的
     OpenSSL 3.6.4（含头文件与 libssl.so.3/libcrypto.so.3），零构建；
4. 消费侧把私有 prefix 的 `lib/pkgconfig` 前置到 `PKG_CONFIG_PATH`，
   meson `dependency('libcurl')` 命中 TLS 版（pkg-config --modversion
   仍报 8.5.0，与发行变体同版本）。

结果：TLS 套件 17/17 通过、55/55 断言。

### 禁止做法
- ❌ 用发行 curl 包自带 `curl-config`/`lib/pkgconfig` 探测——prefix 固化
  打包机死路径（实测 `--prefix` → `p/b/libcu8e3caef60472e/p` 不存在）；
  一律用消费方 PkgConfigDeps 再生成的 .pc（workflow §5.1）；
- ❌ 把测试专用 curl/openssl 写进包的 `requires()`——它们不属于包依赖链，
  会把依赖图指向 remote 不存在的 ref。

## 4. 验证证据（coeurl 0.3.2 实测）

- 自建 curl `readelf -d` NEEDED = libssl.so.3/libcrypto.so.3/libc
  （TLS 后端在位）；
- TLS 套件修复前 16/17 失败（error_code=1）→ 修复后 17/17 通过；
- junit 报告 failures=0 errors=0（https.xml 17 testcase）。

## 5. 适用面与边界

- **适用**: 任何需要 https 的上游测试套件且依赖 ohpcd 发行 libcurl 的包；
  任何需要 TLS 的设备端临时构建。
- **不适用**: 交付包本身的 TLS 能力——交付物 TLS 能力由包依赖链中的
  curl 变体决定（当前发行变体无 TLS，须在 notes/manifest 如实声明）；
  该缺口长期方案是推动 ohpcd 发布带 TLS 后端的 curl 变体（配方暴露
  with_openssl 选项并区分 package_id）。
- **顺带发现**: 本机 musl 加载器不读 DT_RUNPATH，运行期依赖一律经环境
  `LD_LIBRARY_PATH` 解析（详见 E560 附录）。
