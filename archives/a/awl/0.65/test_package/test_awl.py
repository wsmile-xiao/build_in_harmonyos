#!/usr/bin/env python3
"""awl consumer test (L0c + R34): standalone test source executed via
self.run from conanfile.py test().

R34: actually use the packaged awl PHP library — instantiate
vComponent/vProperty, parse a minimal iCalendar component, render and
verify output.

Usage: test_awl.py <php_bin> <awl_inc_dir>
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <php_bin> <awl_inc_dir>",
              file=sys.stderr)
        return 2
    php_bin, awl_inc = sys.argv[1], sys.argv[2]
    if not os.path.isfile(php_bin):
        raise AssertionError(f"php binary missing: {php_bin}")
    if not os.path.isdir(os.path.join(awl_inc, "awl")):
        raise AssertionError(f"awl package missing in {awl_inc}")
    # R34 脚本：真实调用 awl API（vComponent 解析 + vProperty 渲染）
    # 注意：php -r 模式不接受 <?php 标签开头（Parse error: unexpected
    # token "<" 实测）——代码直接以 PHP 语句开始
    php_code = r'''
// iconv polyfill — conan php (--disable-all) build lacks iconv ext;
// awl AWLUtilities.php uses iconv('ISO-8859-1','UTF-8',$ch) once.
if (!function_exists('iconv')) {
    function iconv($from, $to, $s) {
        if ($from === 'ISO-8859-1' && $to === 'UTF-8') {
            $out = '';
            for ($i = 0, $n = strlen($s); $i < $n; $i++) {
                $o = ord($s[$i]);
                if ($o < 0x80) { $out .= chr($o); }
                elseif ($o < 0xC0) { $out .= chr(0xC0 | ($o >> 6)) . chr(0x80 | ($o & 0x3F)); }
                else { $out .= chr(0xE0 | ($o >> 12)) . chr(0x80 | (($o >> 6) & 0x3F)) . chr(0x80 | ($o & 0x3F)); }
            }
            return $out;
        }
        return $s;
    }
}
$awldir = $argv[1];
set_include_path($awldir . PATH_SEPARATOR . get_include_path());
require_once 'awl/vComponent.php';
require_once 'awl/vProperty.php';
$comp = new vComponent("BEGIN:VEVENT\r\nUID:abc123\r\nSUMMARY:Test\r\nEND:VEVENT\r\n");
$props = $comp->GetProperties('SUMMARY');
if (count($props) != 1) { fwrite(STDERR, "expected 1 SUMMARY property\n"); exit(1); }
$sum = $props[0];
if ($sum->Value() !== 'Test') { fwrite(STDERR, "unexpected SUMMARY value\n"); exit(1); }
$rendered = $sum->Render();
if (strpos($rendered, 'SUMMARY:Test') === false) { fwrite(STDERR, "render mismatch\n"); exit(1); }
$p = new vProperty('UID');
$p->Value('xyz789');
$r = $p->Render();
if (strpos($r, 'UID:xyz789') === false) { fwrite(STDERR, "vProperty render mismatch\n"); exit(1); }
echo "OK: awl 0.65 (vComponent parse + vProperty render)\n";
exit(0);
'''
    r = subprocess.run([php_bin, "-r", php_code, awl_inc],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(f"awl API test failed: {r.stderr[:500]}")
    print(r.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
