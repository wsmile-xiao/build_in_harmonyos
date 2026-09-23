# netsurf-buildsystem

## 绠€浠?NetSurf shared makefile build system 鏄?NetSurf 椤圭洰缁勪负鏃椾笅 C 搴擄紙libcss銆乴ibhubbub銆?libdom銆乴ibnsbmp 绛夛級鎻愪緵鐨勭粺涓€ Makefile 鐗囨闆嗕笌璺ㄥ钩鍙板伐鍏疯剼鏈紝閫氳繃
`NSSHARED` 鐜鍙橀噺鎸囧悜宸插畨瑁呯殑 makefile 鏍圭洰褰曞嵆鍙浠绘剰涓嬫父 make 宸ョ▼澶嶇敤銆?
## 涓婃父淇℃伅
- 浠撳簱锛歨ttps://git.netsurf-browser.org/buildsystem.git
- 闀滃儚涓嬭浇锛歨ttps://download.netsurf-browser.org/libs/releases/buildsystem-1.10.tar.gz
- 鍗忚锛歁IT (COPYING 鏂囦欢)
- 鏂囨。锛歨ttps://www.netsurf-browser.org/projects/netsurfbuildsystem/

## OHOS 閫傞厤
- 绾?GNU Make 椤圭洰锛汬armonyOS PC (aarch64, OHOS 6.0) 鍘熺敓鏋勫缓
- `package_type = "build-scripts"`锛氫笉浜у嚭浠讳綍 .a / .so锛屼粎瀹夎 makefile 鐗囨涓?  `testtools/`銆乣citools/` 鐩綍
- 閫氳繃 `buildenv_info.NSSHARED` 鍜?`runenv_info.NSSHARED` 鏆撮湶鏍硅矾寰勭粰娑堣垂鑰?- test_package 鍐欏叆涓€涓渶灏忔秷璐硅€?make 宸ョ▼锛岃皟鐢?`make all` 楠岃瘉
  `makefiles/Makefile.tools` 鍜?`makefiles/Makefile.top` 鍦?OHOS aarch64 clang 宸ュ叿閾?  涓嬭兘姝ｅ父椹卞姩 `lib-static` 浜х墿
- 宸插彂甯冪増鏈細1.10

## 宸茬煡闄愬埗
- 涓婃父 `make test` 鏄?no-op锛涜繍琛屾椂楠岃瘉瀹屽叏鐢?test_package 鎵挎媴
- 涓嶅甫 `make install` 鑴氭湰鏀寔 PREFIX 涔嬪鐨?DESTDIR锛圕onan 閫氳繃 manual
  `copy()` 瀹炵幇鏍囧噯鍖栧畨瑁咃級
