# ccrtp

GNU ccRTP is an implementation of RTP, the real-time transport protocol
from the IETF (RFC 3550/3551/3555). ccRTP is a C++ library based on
GNU Common C++ which provides a high performance, flexible and extensible
standards-compliant RTP stack with full RTCP support.

## OHOS adaptation
- **构建系统**: Autotools (configure + make)，2003 年旧脚本需 OHOS 适配
- **依赖**: commoncpp2 1.8.1 (需 zlib/openssl，已在 OHOS 发布)
- **补丁**: config.guess/config.sub 识别 linux-ohos，config.status mktemp 沙箱修复，C++98 编译选项
- **测试**: 上游无 make check，test_package 通过 RTPSession API 校验

## 依赖
- commoncpp2/1.8.1
- zlib/1.3.1 (transitive)
- openssl/1.1.1w (transitive)

## 功能验证
```bash
pkg-config --modversion libccrtp1
```

## 参考
- 官网: https://www.gnu.org/software/ccrtp/
- 源码: https://ftp.gnu.org/gnu/ccrtp/
