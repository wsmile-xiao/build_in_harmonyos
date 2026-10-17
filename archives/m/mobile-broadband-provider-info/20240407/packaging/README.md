# mobile-broadband-provider-info 20240407 packaging

mobile-broadband-provider-info 20240407 构建产物打包（本地验证用，Conan 体系以
`conan create` 替代手动 tar.gz 发布）：

- 纯数据包，无 bin/ 产物；制品内容为
  `share/mobile-broadband-provider-info/{serviceproviders.xml,serviceproviders.2.dtd,apns-conf.xml}`
  与 `share/pkgconfig/mobile-broadband-provider-info.pc`
- 正式发布路径：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64` →
  `conan upload mobile-broadband-provider-info/20240407@ohpcd/stable -r ohpcd`
