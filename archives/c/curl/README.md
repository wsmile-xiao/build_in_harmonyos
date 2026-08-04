# curl

curl provides both the `curl` command-line transfer tool and the libcurl C API.

## HarmonyOS PC adaptation

- Builds shared libcurl and the curl executable from the official 8.15.0 source.
- Requires `openssl/3.5.6.1` and PIC static `zlib/1.3.1.1`; optional
  undeclared protocol dependencies are disabled. Both recipes passed a fresh
  Conan-home download check on HarmonyOS PC on 2026-08-04.
- Avoids the conflicting OHOS Linux UAPI socket header through the upstream
  `HAVE_LINUX_TCP_H` CMake cache variable, without a source patch.
- Builds curl's `testdeps` target. Cross builds compile and link the target
  test programs without claiming that HarmonyOS binaries ran on Windows.
- A native HarmonyOS PC build considered all 1,849 upstream tests: 1,556
  runnable tests passed, 293 were skipped by upstream capability checks, and
  none failed. The Conan consumer and packaged CLI also executed successfully.

## Consumer verification

The Conan consumer links `CURL::libcurl` and checks initialization, easy-handle
options, the exact libcurl version, the OpenSSL backend, and zlib support. When
the target is runnable, the consumer executes without making a network request.
The HarmonyOS PC run completed this consumer test successfully.

## Reference

- https://curl.se/
- https://github.com/curl/curl
