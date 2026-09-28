#!/bin/sh
# test_nuvie.sh — nuvie 0.5 消费者断言（真二进制实跑）
#
# 用法: sh test_nuvie.sh <package_folder>
#
# 上游没有测试套件（Makefile.am 无 TESTS / check 目标），所以这里的断言全部打在
# **打包后的真实二进制**上，而不是编译一个 print-only 的 stub（R34）。
#
# nuvie 的 main() 只做两件事：new Nuvie 然后 nuvie->init(argc, argv)。init() 的
# 前半段是纯 CPU 逻辑（不需要显示设备也不需要游戏数据）：
#
#   Nuvie::init()
#     ├─ get_game_type(argv[1])          argv 解析
#     ├─ initConfig()                    $HOME/.nuvierc → ./nuvie.cfg
#     │                                   → /usr/{local/,}share/nuvie/nuvie.cfg
#     │                                   → initDefaultConfigUnix($HOME)
#     │     成功 → new Screen(config) → screen->init() → SDL_Init(SDL_INIT_VIDEO)
#     │     失败 → DEBUG "No config file found!" → 返回 false
#     └─ ConsoleInit(...) 设置 g_console    nuvie.cpp:138
#
# 关键点：g_console 只有在 ConsoleInit() 之后才非空，而 ConsolePause() 在
# g_console == NULL 时**立即返回**。于是：
#
#   路径 B：不设 HOME 且 cwd 里没有 nuvie.cfg → initConfig() 返回 false，
#           这条在 ConsoleInit() **之前** return，g_console 仍为 NULL →
#           ConsolePause() 立即返回，进程确定性以 rc=1 退出。
#   路径 C：HOME 指向可写空目录（生成 .nuvierc）→ initConfig() 返回 true
#           → new Screen(config) → Screen::init() → set_screen_mode()。
#
# 路径 C 由**实测**而非源码推得（故另叠 run_bounded 30 兜底）：
#   - 实测在 OHOS/sdl12-compat 上，SDL_VIDEODRIVER 指向一个不存在的驱动时
#     SDL_Init(SDL_INIT_VIDEO) **不返回负值**，进程会继续走 set_screen_mode()；
#     CI #62596 的实跑输出是
#         <[E] set_safe_video_settings nuvie.cpp:400>
#         Couldn't initialize SDL_VIDEO!
#     —— 文案是 "Couldn't initialize SDL_VIDEO"（下划线，出自
#     set_safe_video_settings 而不是 Screen::init 的 "Couldn't initialize SDL: %s"），
#     故判据写成不带尾部标点的 "Couldn't initialize SDL" 才能同时覆盖两种写法；
#     该分支既不打印 "Couldn't initialize SDL:"、也不打印 "Initializing screen!"
#     （后者只在 screen->init() 返回 false 时打印）。
#   - 这意味着执行流**越过了 ConsoleInit()**（g_console 非空），后面才由
#     GameSelect/checkGameDir 找不到游戏数据而 return false。此时 ConsolePause()
#     会真的进事件循环——但实测该进程仍在 30 秒内自行以 rc=1 退出。
#   因为这一步依赖平台/驱动行为（不是源码可证），判据写成 check_any「执行到了
#   Screen/SDL 这一段 C++ 代码」而不是某一条特定 SDL 错误文案；一旦将来上游
#   行为变化导致卡在事件循环，run_bounded 只会记一条 FAIL（rc=124），不会拖垮 CI。
#
# 未执行项：真正的游戏循环（SDL 显示 + U6 数据文件加载）。CI 沙箱无显示设备，
# 且 Ultima 6 的原始游戏数据受版权保护、不随本包分发，故不在此执行。
# 也不断言 readelf/file 之类的二进制静态属性——见 MANIFEST.yml 的说明。
#
# 不使用 `set -e`：本脚本会后台起进程再按秒轮询，`set -e` 会让 `wait` 的非零
# 返回直接终止脚本（而不是记一条 FAIL）。所有判定都走 ok/bad 显式记账。
set -u

PKG_ROOT="${1:?usage: test_nuvie.sh <package_folder>}"
BIN="$PKG_ROOT/bin/nuvie"

fail=0
count=0

ok()  { count=$((count + 1)); echo "ok   - $1"; }
bad() { count=$((count + 1)); fail=1; echo "FAIL - $1"; }

# check <描述> <输出文件> <grep 模式>
check() {
    if grep -q -e "$3" "$2" 2>/dev/null; then ok "$1"; else bad "$1"; fi
}

# check_not <描述> <输出文件> <grep 模式>
check_not() {
    if grep -q -e "$3" "$2" 2>/dev/null; then bad "$1"; else ok "$1"; fi
}

# check_any <描述> <输出文件> <模式1> [模式2 ...]
# 命中任一模式即通过；一条都不命中才记 FAIL。（用于「执行到了某段代码」这类
# 判据：同一段代码在不同平台上可能打印不同文案。）
check_any() {
    _d="$1"; _f="$2"; shift 2
    for _p in "$@"; do
        if grep -q -e "$_p" "$_f" 2>/dev/null; then ok "$_d"; return; fi
    done
    bad "$_d"
}

# check_none <描述> <输出文件> <模式1> [模式2 ...]
# 命中任一模式即 FAIL；全部不命中才通过。（「输出里不该出现这些东西」的判据）
check_none() {
    _d="$1"; _f="$2"; shift 2
    for _p in "$@"; do
        if grep -q -e "$_p" "$_f" 2>/dev/null; then bad "$_d"; return; fi
    done
    ok "$_d"
}

# run_bounded <秒上限> <输出文件> <命令...>
# 前台跑会挂死的二进制时用它；自行退出则返回其退出码，超时则 kill 并返回 124。
run_bounded() {
    limit="$1"; out="$2"; shift 2
    "$@" > "$out" 2>&1 &
    run_pid=$!
    n=0
    while [ "$n" -lt "$limit" ]; do
        kill -0 "$run_pid" 2>/dev/null || break
        sleep 1
        n=$((n + 1))
    done
    if kill -0 "$run_pid" 2>/dev/null; then
        kill -9 "$run_pid" 2>/dev/null
        wait "$run_pid" 2>/dev/null
        return 124
    fi
    wait "$run_pid" 2>/dev/null
    return $?
}

# check_rc <描述> <期望退出码> <实际退出码>
check_rc() {
    if [ "$3" -eq "$2" ]; then ok "$1"; else bad "$1（期望 $2，实际 $3）"; fi
}

WORK="${TMPDIR:-/tmp}/nuvie-test-$$"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

# ── A. 产物存在且可执行 ──────────────────────────────────────────────────
if [ -x "$BIN" ]; then
    ok "bin/nuvie 存在且可执行"
else
    bad "bin/nuvie 不存在或不可执行"
fi

# ── B. 实跑「无配置文件」路径（HOME 未设置，cwd 无 nuvie.cfg） ───────────
# 这条路径完全在 SDL 初始化之前，因此能跑通就同时说明：
#   (1) 该 ELF 在 OHOS aarch64 上被加载器接受 —— libSDL-1.2.so 等全部 NEEDED
#       （含 sdl12-compat 的传递依赖）都解析成功；漏一个会在 main() 之前
#       被拒绝，退出码是 127/126 而不是 1；
#   (2) 符号全部解析成功（-lSDL-1.2 的链接期与运行期一致）；
#   (3) main() → Nuvie::init() → initConfig() 的 C++ 代码在 OHOS 上真实执行。
( unset HOME; exec "$BIN" ) > nobin.out 2>&1
rc_b=$?
check_rc "无配置路径：以退出码 1 结束（而非加载器错误 127/126）" 1 "$rc_b"
check "无配置路径：stderr 出现 main() 的启动日志" nobin.out "Debugging enabled"
check "无配置路径：stderr 出现 initConfig() 的失败诊断" nobin.out "No config file found!"
check_not "无配置路径：没有动态加载失败（NEEDED 全部解析）" nobin.out "cannot open shared object"
check_not "无配置路径：没有符号解析失败" nobin.out "undefined symbol"

# ── C. 实跑「配置加载 + 屏幕初始化」路径（HOME 可写） ─────────────────────
# initConfig() 走到 initDefaultConfigUnix($HOME)：写 $HOME/.nuvierc → 读回 →
# 填默认值 → config->write()，返回 true。之后 new Screen(config) →
# screen->init() → set_screen_mode()。断言的是「配置真的被加载、并且执行流进入
# 了 Screen/SDL 这一段 C++ 代码」，而不是某条特定的 SDL 错误文案（见文件头说明）。
mkdir -p "$WORK/home"
HOME="$WORK/home" SDL_VIDEODRIVER=nuvie_no_such_driver \
    run_bounded 30 cinfo.out "$BIN"
rc_c=$?
check_rc "配置加载路径：以退出码 1 结束（进程自行退出，未挂死）" 1 "$rc_c"
check "配置加载路径：stderr 出现配置探测记录" cinfo.out "Loading Config from"
check_any "配置加载路径：Nuvie::init 越过 initConfig()，执行到 Screen/SDL 段" cinfo.out \
    "Attempting to set vid mode:" \
    "Couldn't initialize SDL" \
    "Initializing screen!" \
    "Unable to create surface"
check_none "配置加载路径：没有动态加载/符号解析失败" cinfo.out \
    "cannot open shared object" \
    "Error loading shared library" \
    "Error relocating" \
    "undefined symbol"
if [ -s "$WORK/home/.nuvierc" ]; then
    ok "配置加载路径：initDefaultConfigUnix 写出的 \$HOME/.nuvierc 非空"
else
    bad "配置加载路径：\$HOME/.nuvierc 缺失或为空"
fi

# TAP 诊断（`#` 开头，不参与 ok/not-ok 判定）：把路径 C 的真实输出带进 CI 日志，
# 便于失败时直接看到进程实际打印了什么，无需再补一次 CI。
echo "# --- path C (HOME writable) actual output ---"
while IFS= read -r _line; do echo "# $_line"; done < cinfo.out

# ── D. 安装布局：运行时数据面 + 桌面/图标 ────────────────────────────────
for f in \
    share/nuvie/BorderU6_1.bmp \
    share/nuvie/BorderU6_2.bmp \
    share/nuvie/BorderU6_3.bmp \
    share/nuvie/BorderU6_4.bmp \
    share/nuvie/BorderU6_5.bmp \
    share/nuvie/BorderU6_6.bmp \
    share/nuvie/BorderU6_7.bmp \
    share/nuvie/BorderU6_8.bmp \
    share/nuvie/ScrollBarDown_1.bmp \
    share/nuvie/ScrollBarDown_2.bmp \
    share/nuvie/ScrollBarUp_1.bmp \
    share/nuvie/ScrollBarUp_2.bmp \
    share/nuvie/defaultkeys.txt \
    share/nuvie/u6keys.txt \
    share/nuvie/sekeys.txt \
    share/nuvie/mdkeys.txt \
    share/applications/nuvie.desktop \
    share/icons/nuvie.png ; do
    if [ -s "$PKG_ROOT/$f" ]; then
        ok "已安装 $f"
    else
        bad "缺失或无内容 $f"
    fi
done

if [ "$fail" -ne 0 ]; then
    echo "nuvie test_package: FAILED"
    exit 1
fi
echo "nuvie test_package: all $count checks passed"
