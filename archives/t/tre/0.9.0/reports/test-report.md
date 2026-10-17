# tre 0.9.0 测试报告 (OHOS aarch64)

## conan create
- configure: PASS
- make: PASS
- install: PASS

## test_package (CTest)
- test_tre: 1/1 PASSED

## 上游 make check
- agrep: 1/1 PASSED
- retest: PASS
- test-str-source: PASS
- wretest: 53443/53447 PASSED (4 失败: OHOS locale 限制)

## 知识引用
- E007: config.sub aarch64-linux-ohos triplet 支持
- E097: HMDFS setgid + autoconf umask 077 修复
