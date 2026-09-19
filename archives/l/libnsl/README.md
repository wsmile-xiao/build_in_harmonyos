# libnsl

Public client interface for NIS(YP) and NIS+ in an IPv6 ready version.

## 鎻忚堪

libnsl 鎻愪緵 NIS (Yellow Pages) 瀹㈡埛绔?API锛坄yp_*` 绯诲垪锛変互鍙?YP/XDR 鍗忚缂栬В鐮併€?2.x 鐗堟湰鏄函 TI-RPC 瀹炵幇锛屾墍鏈?RPC/XDR 鍘熻鏉ヨ嚜 `libtirpc`锛屼笉渚濊禆 glibc 鍐呴儴瀹炵幇銆?
## 缂栬瘧鐗堟湰

- 2.0.1

## 渚濊禆

- libtirpc/1.3.7 (ohpcd)

## 缂栬瘧璇存槑

浣跨敤 Autotools 鏋勫缓绯荤粺锛堝彂甯冨寘宸插甫鐢熸垚濂界殑 `configure`锛夛細

```
autotools.configure()  # --disable-nls --disable-shared --enable-static
autotools.make()
autotools.install()
```

`--disable-nls`锛歄HOS 鏃犳秷鎭洰褰曪紝ENABLE_NLS 鏈畾涔夋椂 `libintl.h` 灏?`gettext()` 瑙ｆ瀽涓烘亽绛夊畯锛屽洜姝ゆ棤闇€寮曞叆 gettext 渚濊禆銆?
## 骞冲彴閫傞厤

- 鏃犻渶骞冲彴琛ヤ竵锛歚src/libc-lock.h` 鏄潰鍚?pthread 鐨勫彲绉绘閿?shim锛宮usl 鍙洿鎺ョ紪璇戙€?- `src/taddr2host.c` / `taddr2ipstr.c` / `taddr2port.c` 鏁翠綋鐢?`HAVE_TIRPC` 淇濇姢锛?  鍥犳 `libtirpc` 蹇呴』鐢?Conan 渚濊禆鎻愪緵锛坄PkgConfigDeps` 鐢熸垚 `libtirpc.pc`锛夈€?
## 涓婃父娴嬭瘯

涓婃父 2.0.1 **涓嶅寘鍚祴璇曞浠?*锛氭墍鏈?`Makefile.am` 鍧囨棤 `TESTS`/`check_PROGRAMS`锛?鍙戝竷鍖呭唴涔熸病鏈夋祴璇曠洰褰曘€傚洜姝?`upstream_total = 0`锛堟簮鐮佽瘉鎹紝闈炴帹鏂級銆?鏈€傞厤鑷甫娑堣垂鑰呮祴璇曪紙41 鏉℃柇瑷€锛夛紝瑕嗙洊閿欒鐮佽〃銆亀ire鈫扽P 鏄犲皠銆?`yp_get_default_domain` 濂戠害浠ュ強 `xdr_domainname` 鍐呭瓨娴佸線杩旂紪瑙ｇ爜銆?
## 浜х墿

- `lib/libnsl.a`锛堥粯璁ら潤鎬侊級/ `libnsl.so.3`锛坄-o shared=True`锛?- `include/rpcsvc/*.h`
- `lib/pkgconfig/libnsl.pc`
