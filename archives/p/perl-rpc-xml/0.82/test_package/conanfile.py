#!/usr/bin/env python3
"""Conan test_package for perl-rpc-xml 0.82 — Perl functional smoke test.

Verifies that RPC::XML can be loaded and core data types, serialization,
and smart_encode functionality work correctly on the target platform.

Tests:
  1. Module loads and version is reported
  2. int data type creation and value retrieval
  3. string data type creation and value retrieval
  4. boolean data type creation and value retrieval
  5. double data type creation and value retrieval
  6. int serialization to XML (as_string)
  7. array data type creation with multiple elements
  8. struct data type creation
  9. nil data type (with $ALLOW_NIL=1)
  10. time2iso8601 time formatting
  11. base64 data type
  12. datetime_iso8601 data type
  13. array serialization to XML
  14. struct serialization to XML
  15. smart_encode for int, string, double, undef
"""
import os

from conan import ConanFile


class PerlRpcXmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a Perl module smoke test

    def test(self):
        # Test 1: Load module and check version
        self.run(
            'perl -MRPC::XML -e '
            '\'print "RPC::XML version: " . RPC::XML->VERSION . "\\n";'
            'die "RPC::XML not loaded" unless RPC::XML->VERSION;\'',
            env="conanrun"
        )

        # Tests 2-15: Comprehensive functional smoke test
        test_script = r'''
use strict;
use warnings;
use RPC::XML;

# T2: int data type
my $int = RPC::XML::int->new(42);
die "T2 FAIL" unless $int->value == 42 && $int->type eq "int";

# T3: string data type
my $str = RPC::XML::string->new("hello world");
die "T3 FAIL" unless $str->value eq "hello world" && $str->type eq "string";

# T4: boolean data type
my $bool = RPC::XML::boolean->new(1);
die "T4 FAIL" unless $bool->value == 1 && $bool->type eq "boolean";

# T5: double data type
my $dbl = RPC::XML::double->new(3.14159);
die "T5 FAIL" unless abs($dbl->value - 3.14159) < 0.00001 && $dbl->type eq "double";

# T6: int serialization
my $xml = $int->as_string();
die "T6 FAIL" unless $xml eq "<int>42</int>";

# T7: array data type
my $arr = RPC::XML::array->new(
    RPC::XML::int->new(1),
    RPC::XML::string->new("two"),
    RPC::XML::boolean->new(0)
);
my $arr_val = $arr->value;
die "T7 FAIL" unless $arr->type eq "array" && scalar(@$arr_val) == 3;

# T8: struct data type
my $struct = RPC::XML::struct->new(
    name => RPC::XML::string->new("test"),
    value => RPC::XML::int->new(123)
);
die "T8 FAIL" unless $struct->type eq "struct";

# T9: nil data type (requires $ALLOW_NIL)
$RPC::XML::ALLOW_NIL = 1;
my $nil = RPC::XML::nil->new();
die "T9 FAIL" unless $nil->type eq "nil" && $nil->as_string eq "<nil/>";

# T10: time2iso8601
my $iso = RPC::XML::time2iso8601(time());
die "T10 FAIL" unless $iso =~ /^\d{8}T\d{2}:\d{2}:\d{2}Z$/;

# T11: base64 data type
my $b64 = RPC::XML::base64->new("binary data here");
die "T11 FAIL" unless $b64->type eq "base64" && $b64->value eq "binary data here";

# T12: datetime_iso8601 data type
my $dt = RPC::XML::datetime_iso8601->new("2026-06-29T12:00:00Z");
die "T12 FAIL" unless $dt->type eq "dateTime.iso8601";

# T13: array serialization
my $arr_xml = $arr->as_string();
die "T13 FAIL" unless $arr_xml =~ /<array>/ && $arr_xml =~ /<data>/;

# T14: struct serialization
my $struct_xml = $struct->as_string();
die "T14 FAIL" unless $struct_xml =~ /<struct>/ && $struct_xml =~ /<member>/;

# T15: smart_encode
my $se_int = RPC::XML::smart_encode(42);
die "T15a FAIL" unless $se_int->type eq "int" && $se_int->value == 42;
my $se_str = RPC::XML::smart_encode("hello");
die "T15b FAIL" unless $se_str->type eq "string" && $se_str->value eq "hello";
my $se_dbl = RPC::XML::smart_encode(3.14);
die "T15c FAIL" unless $se_dbl->type eq "double";
my $se_nil = RPC::XML::smart_encode(undef);
die "T15d FAIL" unless defined($se_nil) && $se_nil->type eq "nil";

print "All functional smoke tests PASSED\n";
'''
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pl', delete=False) as f:
            f.write(test_script)
            script_path = f.name
        try:
            self.run(f'perl {script_path}', env="conanrun")
        finally:
            os.unlink(script_path)

        self.output.info("RPC::XML smoke test PASSED (version + 14 functional tests + smart_encode)")
