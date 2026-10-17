<?php
// test_package/test.php — R34: substantive simplepie source layout test
// (Invoked by test_package/conanfile.py build() copy step; the actual
// assertions run in conanfile.py test() since PHP may not be on PATH
// in the OHOS CI worker.)
require __DIR__ . '/autoloader.php';
if (!class_exists('SimplePie')) {
    fwrite(STDERR, "FAIL: SimplePie class not loaded by autoloader\n");
    exit(1);
}
$sp = new SimplePie();
assert($sp instanceof SimplePie);
echo "simplepie SimplePie class instantiation OK\n";
