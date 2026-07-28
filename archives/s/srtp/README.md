# srtp

srtp packages Cisco libSRTP, an implementation of the Secure Real-time
Transport Protocol used to protect RTP and RTCP media streams.

## OHOS adaptation

- Uses the upstream CMake build and its platform feature checks.
- Uses libSRTP's built-in AES and HMAC-SHA1 implementation, so the package has
  no unpublished third-party dependencies.
- Builds a static `libsrtp2` library and runs the complete upstream CTest suite.

## References

- Upstream: https://github.com/cisco/libsrtp
- Homebrew formula: https://formulae.brew.sh/formula/srtp
