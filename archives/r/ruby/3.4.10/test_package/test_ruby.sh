#!/system/bin/sh
# ruby 3.4.10 L1 smoke test (R34: real dependency on the tested package).
# Runs the installed ruby binary and exercises the extensions that require
# the recipe's declared dependencies (openssl/libyaml/libffi).
set -euo pipefail

RUBY_BIN="${RUBY_BIN:-ruby}"

echo "== ruby version =="
"$RUBY_BIN" --version

echo "== core language =="
"$RUBY_BIN" -e 'raise "bad version" unless RUBY_VERSION == "3.4.10"; puts "ruby #{RUBY_VERSION} ok"'

echo "== openssl extension (requires openssl/3.5.6.1.1) =="
"$RUBY_BIN" -e 'require "openssl"; puts "openssl #{OpenSSL::OPENSSL_VERSION} ok"'

echo "== yaml/psych extension (requires libyaml/0.2.5) =="
"$RUBY_BIN" -e 'require "yaml"; d = YAML.load("a: 1\nb: [1,2]\n"); raise "bad yaml" unless d["a"] == 1 && d["b"] == [1,2]; puts "yaml #{YAML::VERSION} ok"'

echo "== fiddle extension (requires libffi/3.5.2) =="
"$RUBY_BIN" -e 'require "fiddle"; raise "no Fiddle" unless defined?(Fiddle); puts "fiddle ok"'

echo "== socket/json stdlib =="
"$RUBY_BIN" -e 'require "socket"; require "json"; puts "socket+json ok"'

echo "ALL RUBY SMOKE TESTS PASSED"
