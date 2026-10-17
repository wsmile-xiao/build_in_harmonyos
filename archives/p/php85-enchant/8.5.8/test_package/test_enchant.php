<?php
function check(bool $condition, string $message): void {
    if (!$condition) {
        fwrite(STDERR, "FAIL: $message\n");
        exit(1);
    }
    echo "PASS: $message\n";
}
check(extension_loaded('enchant'), 'packaged module loads');
check(phpversion('enchant') === '8.5.8', 'extension version matches PHP 8.5.8');
$broker = enchant_broker_init();
check($broker instanceof EnchantBroker, 'broker object created');
check(is_array(enchant_broker_list_dicts($broker)), 'dictionary discovery returns an array');
try {
    enchant_broker_request_dict($broker, '');
    check(false, 'empty tag rejected');
} catch (ValueError $error) {
    check(str_contains($error->getMessage(), 'must not be empty'), 'empty tag rejected');
}
$directory = getenv('TMPDIR') ?: sys_get_temp_dir();
$file = tempnam($directory, 'php85-enchant-');
if ($file === false || file_put_contents($file, "harmony\nopenharmony\n") === false) {
    throw new RuntimeException('Cannot create personal word list');
}
try {
    $dict = enchant_broker_request_pwl_dict($broker, $file);
    check($dict instanceof EnchantDictionary, 'personal word list opens without a provider');
    check(enchant_dict_check($dict, 'harmony'), 'word in personal dictionary accepted');
    check(!enchant_dict_check($dict, 'definitelynotinthewordlist'), 'unknown word rejected');
    enchant_dict_add_to_session($dict, 'ohosconsumer');
    check(enchant_dict_is_added($dict, 'ohosconsumer'), 'session word recorded');
    check(enchant_dict_check($dict, 'ohosconsumer'), 'session word accepted');
    enchant_dict_remove_from_session($dict, 'ohosconsumer');
    check(!enchant_dict_check($dict, 'ohosconsumer'), 'removed session word rejected');
    check(enchant_dict_describe($dict)['file'] === $file, 'personal dictionary path preserved');
} finally {
    unset($dict, $broker);
    unlink($file);
}
echo "CONSUMER_ASSERTIONS=12 PASS\n";
