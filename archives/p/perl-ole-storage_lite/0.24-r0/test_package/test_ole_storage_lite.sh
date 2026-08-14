#!/bin/sh
# L0c test source — verifies OLE::Storage_Lite Perl module loads and reports version
# Called by test_package/conanfile.py test() method
# Environment: conanrun (PERL5LIB set by package_info)

perl -e "use OLE::Storage_Lite; print OLE::Storage_Lite->VERSION, qq(\n)" || exit 1
