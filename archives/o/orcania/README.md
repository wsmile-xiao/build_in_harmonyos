# orcania

## 绠€浠?orcania 鏄?babelouest 缁存姢鐨?C 璇█宸ュ叿闆嗗悎锛屾彁渚涘瓧绗︿覆澶勭悊銆丅ase64 缂栬В鐮併€?閾捐〃绠＄悊銆佸姩鎬佸唴瀛樺垎閰嶅洖璋冩帴鍙ｇ瓑鍙鐢ㄧ殑鍩虹璁炬柦锛岃 Angharad銆乽lfius銆亂der
绛夊涓?babelouest 椤圭洰浣滀负鍩虹渚濊禆浣跨敤銆?
## 涓婃父淇℃伅
- 浠撳簱锛歨ttps://github.com/babelouest/orcania
- 鏍囩锛歚v2.3.3` (commit ffc8b55d09a3488f4f6be38034b33bc64bf8b0ce)
- 鍗忚锛歀GPL-2.1-or-later
- 鏂囨。锛歨ttps://github.com/babelouest/orcania/blob/master/API.md

## OHOS 閫傞厤
- C99 + CMake 3.5锛汬armonyOS PC (aarch64, OHOS 6.0) 鍘熺敓缂栬瘧
- 浠呬緷璧?libc锛屾棤闇€ musl 鍏煎灞?- 闈欐€佸簱浜х墿锛歚liborcania.a`锛汣Make 鐩爣 `Orcania::Orcania-static`
- test_package 鐩存帴璋冪敤 `o_strdup`銆乣o_strnullempty`銆乣o_strcmp`銆乣o_strcasecmp`銆?  `o_base64_encode` 绛夊叕鍏?API 杩涜鐑熼浘娴嬭瘯
- 宸插彂甯冪増鏈細2.3.3

## 宸茬煡闄愬埗
- 涓婃父 test runner 渚濊禆 libcheck + libsubunit锛屾湭鍦?ohpcd 鍒跺搧浠撳彂甯冿紝鍥犳
  Conan 閰嶆柟涓叧闂簡 `BUILD_ORCANIA_TESTING`锛岃繍琛屾椂娴嬭瘯鐢?test_package 鎻愪緵
