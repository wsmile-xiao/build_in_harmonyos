# commands.json 补标清单（2026-09 hicmd 真机验证）—— ✅ 已由 hicmd 团队批量补标

> 由 hicmd 团队反向扫描 Conan 制品仓生成。**本清单中的 188 个包已全部由
> hicmd 团队批量补写 `commands.json`**（提交见 git 历史，description 采用
> 真机验证通过的命令列表，homepage 取自 manifest.yaml）。清单保留供核对。

配套的制品仓侧问题（51 个有标记无制品等）见 hicmd 仓
`docs/09-registry-quality-report.md`。

## 补标方法

在 `archives/<首字母>/<包名>/commands.json` 写入（version/ref/binary 为必填）：

```json
{
  "name": "<包名>",
  "description": "<一句话描述>",
  "homepage": "<上游主页>",
  "type": "tool",
  "versions": {
    "<版本>": {"ref": "<包名>/<版本>", "binary": true}
  }
}
```

`<包名>/<版本>` 为真机验证通过的版本（下表 ref 列）。`真机命令` 列为验证时
实际运行的 bin 入口，可作为该包提供命令行的依据。

## 待补标清单（188 包）

### A（30）

| ref（已验证版本） | 真机命令 |
|---|---|
| a52dec/0.7.4 | a52dec, extract_a52 |
| aalib/1.4p5 | aafire, aainfo, aasavefont, aatest |
| abpoa/1.5.6 | abpoa |
| acct/6.6.4 | ac, accton, dump-acct, dump-utmp, last, lastcomm |
| acpid/2.0.34 | acpi_listen |
| addrwatch-mysql/1.0.2 | addrwatch, addrwatch_mysql, addrwatch_stdout, addrwatch_syslog |
| addrwatch/1.0.2 | addrwatch, addrwatch_stdout, addrwatch_syslog |
| adql/2.0 | parse_adql |
| aegean/0.16.0 | canon-gff3, gaeval, locuspocus, parseval, pmrna, tidygff3 |
| aida/1.1.0 | AIDA-X |
| airspy/1.0.10 | airspy_gpio, airspy_gpiodir, airspy_info, airspy_lib_version, airspy_r820t, airspy_rx |
| aj/0.9.9 | aj-snapshot |
| algobox/1.1.1 | algobox |
| algolia/1.14.0 | algolia |
| allegro4.4/4.4.3.1 | colormap, dat, dat2c, dat2s, exedat, grabber |
| allelecount/4.3.0 | alleleCounter |
| ansifilter/2.22 | ansifilter |
| at-spi2-core/2.60.5 | at-spi2-registryd |
| atf/0.23 | atf-sh |
| atftp/0.8.1 | atftp |
| atlas-ecmwf/0.46.0 | atlas, atlas-atest-mgrids, atlas-gaussian-latitudes, atlas-grid-points, atlas-grids, atlas-interpolations |
| atlc/4.6.1 | atlc |
| audacious/4.5.1 | audacious |
| audiofile/0.3.6 | sfconvert, sfinfo |
| avahi-compat-howl/0.9_rc5 | avahi-browse, avahi-browse-domains, avahi-publish, avahi-publish-address, avahi-publish-service, avahi-resolve |
| avarice/2.14-svn427 | avarice |
| avr-evtd/1.7.7 | avr-evtd |
| avra/1.4.2 | avra |
| avro-cpp/1.12.1 | avrogencpp |
| avrp/1.0beta3 | avrp |

### B（5）

| ref（已验证版本） | 真机命令 |
|---|---|
| baloo/6.28.0 | balooctl6, baloosearch6, balooshow6 |
| base16384/2.3.2 | base16384 |
| basis_universal/2.1.0 | basisu |
| bsdtar/3.7.7 | bsdcat, bsdcpio, bsdtar, bsdunzip |
| btor2tools/1.0.2-git20250918.d33c73f | btorsim, btorsplit, catbtor |

### C（13）

| ref（已验证版本） | 真机命令 |
|---|---|
| clblas/2.12 | clBLAS-tune |
| clblast/1.7.0 | clblast_test_xamax, clblast_test_xasum, clblast_test_xaxpy, clblast_test_xaxpybatched, clblast_test_xcol2im, clblast_test_xconvgemm |
| clearsilver/0.10.5 | cs, cs_static.cgi, cstest |
| clip/0.7 | clip |
| cliquer/1.23 | cl |
| cloog/0.21.1 | cloog |
| clp/1.17.11 | clp |
| cmigemo/1.2-gh0.20220623 | cmigemo |
| corrade/2020.06 | corrade-rc |
| cppunit/1.15.1 | DllPlugInTester |
| cpu_features/0.9.0 | list_cpu_features |
| cpuinfo/0.0-git20250905.877328f | cache-info, cpu-info, isa-info |
| cpulimit/0.2 | cpulimit |

### D（8）

| ref（已验证版本） | 真机命令 |
|---|---|
| dbus/1.14.10.1 | dbus-daemon, dbus-run-session |
| dbustest/19.04.0 | dbus-test-runner |
| dhcpd-pools/3.2 | dhcpd-pools |
| discount/2.2.7 | markdown |
| disomaster/5.0.8 | xorriso |
| djstub/0.7 | djelfextract, djlink, djstrip, djstubify |
| dnsperf/2.15.1 | dnsperf, resperf |
| duckdb/1.2.0 | duckdb |

### E（7）

| ref（已验证版本） | 真机命令 |
|---|---|
| e2fsprogs/1.47.4 | badblocks, blkid, chattr, debugfs, dumpe2fs, e2freefrag |
| eckit/2.0.7 | eckit-version |
| ecl/24.5.10 | ecl |
| elfutils/0.195 | debuginfod-find, eu-addr2line, eu-ar, eu-elfclassify, eu-elfcmp, eu-elfcompress |
| epeg/0.9.3 | epeg |
| espeak-ng/1.51 | espeak, espeak-ng, speak, speak-ng |
| exempi/2.6.6 | exempi |

### F（5）

| ref（已验证版本） | 真机命令 |
|---|---|
| fftw/3.3.10.3 | fftw-wisdom |
| file/5.48.1 | file |
| flang-ohos/20.1.0 | flang, flang-20, flang-new |
| freetds/1.4.23 | bsqldb, datacopy, defncopy, fisql, freebcp, tdspool |
| fribidi/1.0.16 | fribidi |

### G（8）

| ref（已验证版本） | 真机命令 |
|---|---|
| gadap/2.0 | test |
| gbdk-2020/4.5.0 | bankpack, gbcompress, ihxcheck, lcc, makebin, makecom |
| glib/2.88.3 | (见制品 bin/) |
| globus-common/18.15 | globus-libc-hostname, globus-redia |
| glpk/5.0 | glpsol |
| gnutls/3.8.10 | certtool, gnutls-cli, gnutls-serv |
| gobject-introspection/1.78.1.1 | g-ir-compiler, g-ir-generate, g-ir-inspect |
| gsl/2.8 | gsl-histogram, gsl-randist |

### H（6）

| ref（已验证版本） | 真机命令 |
|---|---|
| heimdal/7.8.0 | afslog, bsearch, gsstool, heimtools, hxtool, idn-lookup |
| highs/1.13.1 | highs |
| hogweed/3.9.1 | nettle-hash, nettle-lfib-stream, nettle-pbkdf2, pkcs1-conv, sexp-conv |
| htmldoc/1.9.21 | htmldoc |
| hunspell/1.7.3 | analyze, chmorph, hunspell, hunzip, hzip, munch |
| hypre/3.1.0 | ams_driver, ij, ij_assembly, sstructmat, struct, struct_migrate |

### I（1）

| ref（已验证版本） | 真机命令 |
|---|---|
| itk/5.4.6 | itkTestDriver |

### J（2）

| ref（已验证版本） | 真机命令 |
|---|---|
| jasper/4.2.9 | imgcmp, imginfo, jasper |
| jbig2dec/0.20.1 | jbig2dec |

### K（9）

| ref（已验证版本） | 真机命令 |
|---|---|
| kallisto/0.52.0 | kallisto |
| kconfig/6.26.0 | kreadconfig6, kwriteconfig6 |
| kdbusaddons/6.29.0 | kquitapp6 |
| kfilemetadata/6.28.0 | kfilemetadata_dump6 |
| kguiaddons/6.14.0 | kde-geo-uri-handler |
| kiconthemes/6.26.0 | kiconfinder6 |
| kor/0.6.8 | kor |
| kservice/6.26.0 | kbuildsycoca6 |
| ksyntaxhighlighting/6.18.0 | ksyntaxhighlighter6 |

### L（35）

| ref（已验证版本） | 真机命令 |
|---|---|
| libde265/1.0.18 | dec265 |
| libdisplay-info/0.3.0 | di-edid-decode |
| libdnet/1.12 | dnet |
| libfstconst/1.8.4 | fstarcsort, fstclosure, fstcompile, fstcompose, fstconcat, fstconnect |
| libfuse/2.9.9 | fusermount, ulockmgr_server |
| libfyaml/0.9.6 | fy-compose, fy-dump, fy-filter, fy-join, fy-testsuite, fy-tool |
| libgd/2.3.3 | gd2copypal, gd2togif, gd2topng, gdcmpgif, gdparttopng, gdtopng |
| libgpg-error/1.55 | gpg-error |
| libgsm/1.0.18 | toast |
| libidn2/2.3.8 | idn2 |
| libimobiledevice/1.3.0 | idevice_id, idevicebackup, idevicebackup2, idevicecrashreport, idevicedate, idevicedebug |
| libiptcdata/1.0.5 | iptc |
| libkate/0.4.3 | katalyzer, katedec, kateenc |
| liblockfile/1.17.1 | dotlockfile |
| liblzma/5.8.1 | lzcat, lzma, lzmadec, lzmainfo, unlzma, unxz |
| libnfc/1.8.0 | nfc-anticol, nfc-barcode, nfc-dep-initiator, nfc-dep-target, nfc-emulate-forum-tag2, nfc-emulate-forum-tag4 |
| liboggz/1.1.1 | oggz, oggz-chop, oggz-codecs, oggz-comment, oggz-dump, oggz-info |
| libplist/2.3.0 | plistutil |
| libpsl/0.21.5.1 | psl |
| librasterlite2/1.1.0-beta1 | rl2sniff, rl2tool, wmslite |
| librsync/2.3.4 | rdiff |
| libseccomp/2.5.4 | scmp_sys_resolver |
| libselinux/3.10.1 | avcstat, compute_av, compute_create, compute_member, compute_relabel, getconlist |
| libshout/2.4.6 | shout |
| libslax/3.1.6 | slaxproc |
| libstatgrab/0.92.1 | statgrab |
| libtasn1/4.21.0 | asn1Coding, asn1Decoding, asn1Parser |
| libtelnet/0.23 | telnet-client, telnet-proxy |
| libusbmuxd/2.0.2 | inetcat, iproxy |
| libvterm/0.3.3 | unterm, vterm-ctrl, vterm-dump |
| libxcvt/0.1.3 | cvt |
| libxpm/3.5.17 | cxpm |
| libzmf/0.0.2 | zmf2raw, zmf2svg |
| libzzip/0.13.80 | unzip-mem, unzzip, unzzip-big, unzzip-mem, unzzip-mix, zzcat |
| lua-pty/1.1 | lua |

### M（9）

| ref（已验证版本） | 真机命令 |
|---|---|
| mac/12.60 | mac |
| mariadb-connector-c/3.4.8 | mariadb_config |
| memory/0.7-4 | nodesize_dbg |
| milkytracker/1.06 | milkycli, milkytracker |
| minisign/0.12 | minisign |
| mlt/7.34.0 | melt |
| mozjpeg/4.1.1 | cjpeg, djpeg, jpegtran, rdjpgcom, tjbench, wrjpgcom |
| mtbl/1.7.1 | mtbl_dump, mtbl_info, mtbl_merge, mtbl_verify |
| mtdev/1.1.7 | mtdev-test |

### N（5）

| ref（已验证版本） | 真机命令 |
|---|---|
| nasm/2.16.03 | nasm, ndisasm |
| ncdu2/2.9.2 | ncdu |
| netcdf/4.9.3 | nccopy, ncdump, ncgen, ncgen3 |
| nettle-3/3.10.2 | nettle-hash, nettle-lfib-stream, nettle-pbkdf2, pkcs1-conv, sexp-conv |
| nettle/4.0 | nettle-hash, nettle-lfib-stream, nettle-pbkdf2, pkcs1-conv, sexp-conv |

### O（4）

| ref（已验证版本） | 真机命令 |
|---|---|
| octomap/1.10.0 | binvox2bt, bt2vrml, compare_octrees, convert_octree, edit_octree, eval_octree_accuracy |
| openexr/3.3.4 | exr2aces, exrenvmap, exrheader, exrinfo, exrmakepreview, exrmaketiled |
| openssl-4/4.0.1 | (见制品 bin/) |
| ophcrack/3.8.0 | ophcrack |

### P（10）

| ref（已验证版本） | 真机命令 |
|---|---|
| p11-kit-server/0.26.2 | p11-kit-remote, p11-kit-server |
| p11-kit/0.26.2 | p11-kit |
| pari/2.17.4.1 | gp, gp-2.17 |
| pcre/8.45 | pcregrep, pcretest |
| physfs/3.2.0.1 | test_physfs |
| plplot/5.15.0 | pltek |
| poco/1.15.3 | cpspc, f2cpsp, poco-arc |
| ppl/1.2 | ppl-config, ppl_lcdd, ppl_pips |
| premake/5.0.0-beta8 | premake5 |
| pwgen/2.08 | pwgen |

### Q（8）

| ref（已验证版本） | 真机命令 |
|---|---|
| qaccessibilityclient/0.6.0 | dumper |
| qdbm/1.8.78 | cbcodec, cbtest, crmgr, crtest, crtsv, dpmgr |
| qhull/2020.2.1 | qconvex, qdelaunay, qhalf, qhull, qvoronoi, rbox |
| qpdf/12.3.2.1 | fix-qdf, qpdf, zlib-flate |
| qt/5.15.19.1 | moc, qdbuscpp2xml, qdbusxml2cpp, qlalr, qmake, qvkgen |
| qt6linguisttools/6.11.1 | lcheck, lconvert, lrelease, lrelease-pro, ltext2id, lupdate |
| qtbase-gui/6.11.1 | androiddeployqt, androiddeployqt6, androidtestrunner, qmake, qmake6, qtpaths |
| qtdeclarative/6.11.1 | qml, qmlcontextpropertydump, qmldom, qmleasing, qmlformat, qmllint |

### R（2）

| ref（已验证版本） | 真机命令 |
|---|---|
| rdma-core/56.1 | bitmap_test, cmtime, ibv_asyncwatch, ibv_devices, ibv_devinfo, ibv_rc_pingpong |
| readsb/3.16.15 | readsb |

### S（9）

| ref（已验证版本） | 真机命令 |
|---|---|
| scdoc/1.11.0 | scdoc |
| scotch/7.0.12 | acpl, amk_ccc, amk_fft2, amk_grf, amk_hy, amk_m2 |
| siege/4.1.7 | siege |
| singular/4.4.1 | ESingular, Singular, TSingular |
| smallerc/1.0.2 | n2f, smlrc, smlrcc, smlrl, smlrpp |
| smpeg2/2_0_0 | plaympeg |
| solid/6.18.0 | solid-hardware6 |
| sonnet/6.26.0 | parsetrigrams6 |
| spirv-tools/vulkan-sdk-1.3.290.0 | spirv-as, spirv-cfg, spirv-dis, spirv-link, spirv-lint, spirv-objdump |

### T（2）

| ref（已验证版本） | 真机命令 |
|---|---|
| tidy-html5/5.8.0 | tidy |
| tio/3.9 | tio |

### U（1）

| ref（已验证版本） | 真机命令 |
|---|---|
| urdfdom/6.0.0 | check_urdf, urdf_mem_test, urdf_to_graphviz |

### V（1）

| ref（已验证版本） | 真机命令 |
|---|---|
| vte/0.74.2 | vte-2.91, vte-urlencode-cwd |

### W（3）

| ref（已验证版本） | 真机命令 |
|---|---|
| watcher/0.14.5 | tw, wtr.watcher |
| wcslib/8.4 | fitshdr, sundazel, tofits |
| wego/2.4 | wego |

### X（2）

| ref（已验证版本） | 真机命令 |
|---|---|
| xidle/20200802 | xidle |
| xmlsec1/1.3.11 | xmlsec1 |

### Y（1）

| ref（已验证版本） | 真机命令 |
|---|---|
| yaz/5.37.3 | yaz-client, yaz-iconv, yaz-icu, yaz-illclient, yaz-json-parse, yaz-marcdump |

### Z（2）

| ref（已验证版本） | 真机命令 |
|---|---|
| zeitgeist/1.0.4 | zeitgeist-daemon |
| zeromq/4.3.5 | inproc_lat, inproc_thr, local_lat, local_thr, proxy_thr, remote_lat |

## 其他 commands.json 数据问题（✅ 均已随本次批量修复）

1. ~~JSON 语法损坏~~ `archives/a/ansifilter/commands.json` —— 已重写
2. ~~versions 为版本号数组/缺失~~ 12 个包
   （barcode, base91, chaos-marmosets, ldns, libicns, libwbxml, mawk,
   munge, openscap, potrace, qrencode, toml）—— 已统一为标准对象 schema，
   binary 标志取自 hicmd 0.2.0 真机验证结果
3. **name 字段与制品包名不一致**（hicmd 无法关联，已修正）：
   `basis_universal`（原 name=basisu）、`watcher`（原 name=wtr.watcher）
   —— 请后续新配方保持 name 与制品仓包名一致

## 验证环境说明

- 验证执行: hicmd-c（纯 C 单二进制），每包全新 prefix，完整
  install → 命令冒烟（--version/--help，20s 超时）→ uninstall → 残留校验
- 29 个包因验证沙箱 exec 策略受限未通过（gtk4/vtk/pulseaudio 等，真实环境
  大概率可用），待制品仓真机复验后另行通知补标
