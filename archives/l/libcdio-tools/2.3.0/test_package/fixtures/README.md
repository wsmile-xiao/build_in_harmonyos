# Upstream fixtures

These files are copied unchanged from the official `libcdio-2.3.0.tar.gz`
test-data directory. They let the consumer test exercise installed executables
without a physical optical drive.

The two binary fixtures are committed as gzip+base64 text (`copying.iso.b64`,
`isofs-m1.bin.b64`) instead of raw bytes: CI applies every pull request as a
unified diff, and GitCode's `.diff` endpoint omits binary patch data, so a
committed `.iso`/`.bin` would make the CI `checkout-pr` step fail with
`missing binary patch data`. The consumer test decodes them back to the exact
upstream bytes and verifies the SHA256 values below before running.

SHA256 values:

```text
5bb4ab6b1c8941d3aa2ada6cd93557facf314ffd9194b771a21655012ef95f1e  copying.iso
231f7edcc7352d7734a96eef0b8030f77982678c516876fcb81e25b32d68564c  copying.gpl
2c913a89ed26072d4b2e82f38964b2984720649285eba748381f461773d92908  copying.right
df3a421e25089b3cfd04cf0d402261386a7c299f5cb2d194a187a50800e2a8c0  isofs-m1.bin
d5174989629421858fc3777e8f9baf9fcfee2008346cb34de16ec5697814da66  isofs-m1.cue
2fc68a0840fb035c8065069630203a2416826ee0e6e38cdf7e5fc9edb25e728d  isofs-m1-read.right
a04fd485fcbe8d33e3a8ad8bb70d07365c82732b2c72167116401ca6d762b9e9  check_opts0.right
```

`copying.iso`/`copying.gpl` and their expected listing are used for ISO-9660
listing and extraction. `isofs-m1.bin`/`.cue` and the two `.right` files are
used for CD image analysis and sector-read assertions.
