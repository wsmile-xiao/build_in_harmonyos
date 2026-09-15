# test_combat.tcl — Combat test_package：真实 IIOP 回环验证
#
# 验证打包产物（而非源码树）：加载包内 lib/combat（orb）与 lib/tclkill，
# 启动本脚本的 server 模式子进程（tclsh8.6），客户端经 corba::string_to_object
# 建立 GIOP/IIOP 连接并做 long 属性读写往返。
#
# usage: tclsh8.6 test_combat.tcl <orb_dir> <tclkill_dir> [server]
# server.ior 写入本脚本所在目录（test_package 的 conan 缓存目录，可写）。

set orbDir  [lindex $argv 0]
set killDir [lindex $argv 1]
set here    [file dirname [file normalize [info script]]]

lappend auto_path $orbDir $killDir
package require combat

proc fail {msg} {
    puts "FAIL: $msg"
    exit 1
}

# 与上游 test/1 的 idl2tcl 生成物同构的接口仓库描述：
# interface Echo { attribute long n; }  （客户端与服务端都需要 IR 数据）
proc add_ir {} {
    combat::ir add \
{{interface {IDL:demo/Echo:1.0 demo/Echo 1.0} {} {{attribute {IDL:demo/Echo/n:1.0 n\
1.0} long}}}}
}

proc server_main {} {
    itcl::class Echo_impl {
        public method _Interface {} {
            return "IDL:demo/Echo:1.0"
        }
        public variable n 0
    }
    add_ir
    # -ORBHostName 127.0.0.1：IOR 内嵌回环地址，规避设备主机名解析差异
    corba::init -ORBHostName 127.0.0.1
    set poa [corba::resolve_initial_references RootPOA]
    set mgr [$poa the_POAManager]
    set srv [Echo_impl #auto]
    set oid [$poa activate_object $srv]
    set ref [$poa id_to_reference $oid]
    set f [open [file join $::here server.ior] w]
    puts -nonewline $f [corba::object_to_string $ref]
    close $f
    $mgr activate
    vwait forever
    exit 0
}

proc client_main {} {
    package require kill
    set iorFile [file join $::here server.ior]
    file delete -force $iorFile

    set tclsh [info nameofexecutable]
    set server [eval exec $tclsh [list [info script]] \
            [list $::orbDir] [list $::killDir] server &]

    # 等待服务端写出 IOR（最多 10s）
    set ok 0
    for {set i 0} {$i < 40} {incr i} {
        if {[file exists $iorFile]} {
            set ok 1
            break
        }
        after 250
    }
    if {!$ok} {
        catch {kill $server}
        fail "server did not write server.ior"
    }
    after 500 ; # 留出 POAManager activate 时间

    set f [open $iorFile r]
    set ior [string trim [read $f]]
    close $f

    add_ir
    corba::init
    if {[catch {set obj [corba::string_to_object $ior]} err]} {
        catch {kill $server}
        fail "string_to_object: $err"
    }

    # IIOP 属性写读往返
    if {[catch {$obj n 42} err]} {
        catch {kill $server}
        fail "attribute write 42: $err"
    }
    if {[catch {set got [$obj n]} err]} {
        catch {kill $server}
        fail "attribute read: $err"
    }
    if {$got != 42} {
        catch {kill $server}
        fail "attribute roundtrip 42: got $got"
    }
    if {[catch {$obj n -1234567} err]} {
        catch {kill $server}
        fail "attribute write -1234567: $err"
    }
    if {[catch {set got [$obj n]} err]} {
        catch {kill $server}
        fail "attribute read 2: $err"
    }
    if {$got != -1234567} {
        catch {kill $server}
        fail "attribute roundtrip -1234567: got $got"
    }

    if {[catch {kill $server} err]} {
        fail "kill extension: $err"
    }

    puts "PASS combat package loaded ([package present combat])"
    puts "PASS Itcl support ([package present Itcl])"
    puts "PASS kill extension loaded ([package present kill])"
    puts "PASS IIOP loopback long-attribute roundtrip (42 / -1234567)"
    puts "ALL_TESTS_PASSED"
}

if {[lindex $argv 2] eq "server"} {
    server_main
} else {
    client_main
}
