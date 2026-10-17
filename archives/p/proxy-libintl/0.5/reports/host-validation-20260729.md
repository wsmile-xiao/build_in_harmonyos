# proxy-libintl 0.5 host validation

## Scope

- Conan: 2.29.1
- Host: Windows x86_64, GCC 15.2.0
- Source archive SHA-256:
  `f7a1cbd7579baaf575c66f9d99fb6295e9b0684a28b095967cfda17857595303`
- Isolated Conan home:
  `E:\HarmonyPC\validation\conan-home-proxy-libintl-0.5-host-20260729`

## Results

- Static package: build/package passed; consumer `1/1` passed.
- Shared package: build/package passed; consumer `1/1` passed.
- Independent consumer test count: `1`; the same flow ran in two variants.
- OHOS `shared=True`: expected rejection passed with Conan exit code 6.
- OHOS target consumer: `NOT_RUN 0/1`.

## Logs

- `conan-create-shared-false.log`:
  `7482f38d54c645d1ae49c241ca783fed144965cf3905616ea88941c19fa3ceed`
- `conan-create-shared-true.log`:
  `11f99f6ad34e1a172d272133599212e03cd1378996d3650b077d3a950fac4ff9`
- `ohos-shared-negative.log`:
  `1d2dce1165cc38f4766cb9192b74ac1c4091e036ebb2e2601a0090bd8355fa29`

The logs are under
`E:\HarmonyPC\validation\proxy-libintl-0.5\host-20260729-r3`.
