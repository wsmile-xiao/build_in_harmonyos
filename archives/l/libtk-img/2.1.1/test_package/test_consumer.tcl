# test_consumer.tcl --
#
#	libtk-img 的 R34 消费者可用性测试（OHOS PC / aarch64）。
#
#	由 test_package/conanfile.py 通过 tcl 依赖自带的 tclsh9.0 调用。
#	本脚本把 libtk-img 包当成**外部消费方**看待：只通过 pkgIndex.tcl /
#	`load` / `package require` 的公开机制使用它，不依赖源码树内部路径。
#
#	调用约定:
#	    tclsh9.0 test_consumer.tcl <Img 运行时目录>
#	环境约定:
#	    LD_LIBRARY_PATH 含 tcl/tk/libx11 的 lib 目录（由 conanfile 注入）
#
#	退出码 = 失败断言数（0 表示全部通过）。

if {[llength $argv] >= 1} {
    set imgDir [lindex $argv 0]
    if {![file isdirectory $imgDir]} {
        puts stderr "FATAL: Img 运行时目录不存在: $imgDir"
        exit 90
    }
    lappend ::auto_path $imgDir
}

set ::failures 0

proc assertTrue {desc cond} {
    if {$cond} {
        puts "PASS  $desc"
    } else {
        puts "FAIL  $desc"
        incr ::failures
    }
}

puts "== libtk-img 消费者测试 (tclsh [info patchlevel], os=$::tcl_platform(os), platform=$::tcl_platform(platform), ptr=[expr {$::tcl_platform(pointerSize)*8}]-bit) =="
puts "auto_path = $::auto_path"

# ---------------------------------------------------------------- 1. 主包加载
set rc [catch {package require Img} imgVer]
assertTrue "1.1 package require Img (rc=$rc, ver=$imgVer)" [expr {$rc == 0}]
assertTrue "1.2 Img 版本为 2.1.1 (actual=$imgVer)" [expr {$imgVer eq "2.1.1"}]
assertTrue "1.3 OHOS 共享库后缀为 .so" [expr {[info sharedlibextension] eq ".so"}]
assertTrue "1.4 目标字长 64-bit" [expr {$::tcl_platform(pointerSize) == 8}]

# ------------------------------------------- 2. 逐个格式处理器真实 dlopen 加载
set handlers {base bmp gif ico jpeg pcx pixmap png ppm ps sgi sun tga tiff window xbm xpm dted raw flir}
foreach fmt $handlers {
    set rc [catch {package require img::$fmt} v]
    assertTrue "2.$fmt dlopen img::$fmt (rc=$rc, ver=$v)" [expr {$rc == 0}]
}

# ------------------------------------- 3. 内置 compat 库的 Tcl 包装也可加载
foreach compat {zlibtcl pngtcl tifftcl jpegtcl} {
    set rc [catch {package require $compat} v]
    assertTrue "3.$compat dlopen $compat (rc=$rc, ver=$v)" [expr {$rc == 0}]
}

# ------------------------------------------- 4. 真实消费者往返：生成->写盘->读回
set tmp [file join [pwd] "consumer_roundtrip.bmp"]
if {[catch {
    image create photo src -width 16 -height 8
    set rows {}
    for {set y 0} {$y < 8} {incr y} {
        set row {}
        for {set x 0} {$x < 16} {incr x} {
            lappend row [format "#%02x%02x%02x" [expr {$x * 16}] [expr {$y * 32}] 0x80]
        }
        lappend rows $row
    }
    src put $rows
    src write $tmp -format bmp

    image create photo dst -file $tmp
    set same [expr {[src data -format bmp] eq [dst data -format bmp]}]
    assertTrue "4.1 消费者源图尺寸 16x8 (actual=[image width src]x[image height src])" \
        [expr {[image width src] == 16 && [image height src] == 8}]
    assertTrue "4.2 BMP 写盘->读回 逐像素一致" $same
    assertTrue "4.3 读回图像尺寸 16x8 (actual=[image width dst]x[image height dst])" \
        [expr {[image width dst] == 16 && [image height dst] == 8}]
    image delete src
    image delete dst
} err]} {
    puts "FAIL  4.x 图像往返异常: $err"
    incr ::failures
}
catch {file delete -force $tmp}

puts "== 消费者测试结束: failures=$::failures"
# OHOS 上 Tk 拆除阶段会挂住，用 _exit 绕过 atexit/teardown
flush stdout
exit $::failures
