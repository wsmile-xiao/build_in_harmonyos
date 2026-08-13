<?php
/**
 * PHP smoke test script for conan test_package.
 * Tests basic PHP functionality: arithmetic, arrays, strings.
 */
$arr = array(1, 2, 3);
$sum = array_sum($arr);
var_dump($sum);
var_dump(count($arr));
var_dump(strlen("HarmonyOS"));
