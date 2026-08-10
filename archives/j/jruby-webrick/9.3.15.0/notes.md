# Notes — jruby-webrick 9.3.15.0

## Software Info
- **Name**: jruby-webrick
- **Version**: 9.3.15.0
- **Description**: JRuby WEBrick HTTP server toolkit (Ruby stdlib library bundled with JRuby)
- **License**: BSD-2-Clause
- **Source URL**: https://github.com/ruby/webrick/archive/refs/tags/v1.7.0.tar.gz
- **SHA256**: 25df35c696301deddec8cc929954284fa3dfaa86ad90c0cce2ecc5740c476545
- **Homepage**: https://github.com/jruby/jruby

## Build Characteristics
- **Type**: Pure Ruby library — no C/C++ compilation needed
- **Build system**: None (copy .rb files from webrick gem source)
- **Package type**: header-library (content package, no compiled binary)
- **Settings**: os, arch (no compiler/build_type — pure Ruby)

## Dependencies
- **None** — WEBrick is part of Ruby stdlib (no external dependencies)

## Source Discovery
The JRuby source tarball (jruby-9.3.15.0.tar.gz) does NOT contain WEBrick .rb
source files. It only contains MRI test files under `test/mri/webrick/`. The
actual WEBrick library source comes from the `ruby/webrick` GitHub repository.

JRuby 9.3.15.0 bundles the webrick gem v1.7.0 (as declared in `lib/pom.rb` and
`lib/pom.xml`). The webrick gem source is downloaded from:
https://github.com/ruby/webrick/archive/refs/tags/v1.7.0.tar.gz

## File Layout in Package
```
lib/ruby/stdlib/
  webrick.rb           # Main entry point (module WEBrick)
  webrick/
    accesslog.rb       # Access logging
    cgi.rb             # CGI handler
    compat.rb          # Compatibility module
    config.rb          # Configuration (module Config)
    cookie.rb          # HTTP cookies
    htmlutils.rb       # HTML utilities
    httpauth.rb        # HTTP authentication
    httpauth/          # Auth sub-modules
    httpproxy.rb       # HTTP proxy server
    httprequest.rb     # HTTP request parser (class HTTPRequest)
    httpresponse.rb    # HTTP response builder (class HTTPResponse)
    https.rb           # HTTPS support
    httpserver.rb      # HTTP server (class HTTPServer)
    httpservlet.rb     # HTTP servlet framework
    httpservlet/       # Servlet sub-modules
    httpstatus.rb      # HTTP status codes
    httputils.rb       # HTTP utilities
    httpversion.rb     # HTTP version handling
    log.rb             # Logging framework
    server.rb          # Base server classes (SimpleServer, GenericServer)
    ssl.rb             # SSL/TLS enhancement
    utils.rb           # Utility functions
    version.rb         # Version constant
```

## Adaptation Process
1. Downloaded JRuby source tarball — discovered WEBrick .rb files are NOT in the JRuby source tree
2. Identified that JRuby 9.3.15.0 bundles webrick gem v1.7.0 (from `lib/pom.rb`)
3. Downloaded webrick gem v1.7.0 source from ruby/webrick GitHub repo
4. Verified 34 .rb files in lib/webrick/ plus main lib/webrick.rb entry point
5. Created Conan recipe (conanfile.py + conandata.yml) to package the .rb files
6. Created test_package with Python validation of module/class declarations
7. Ran `conan create` with --profile=ohos-aarch64 to verify the package builds correctly

## Test Approach
Python validation script (test_webrick.py) that checks:
- File existence and non-emptiness of key .rb files
- Module/class declarations in the .rb files (module WEBrick, class HTTPServer, etc.)
- SSL support file existence (ssl.rb)
- Proxy support file existence (httpproxy.rb)
- Total .rb file count in webrick/ directory (>= 15)

## Key Decisions
1. **Source URL**: Changed from JRuby source URL to ruby/webrick gem URL because the JRuby source tarball doesn't contain WEBrick .rb source files
2. **package_type = header-library**: Pure Ruby content package, no compiled binary
3. **settings = os, arch**: No compiler/build_type needed — pure Ruby
4. **No build() step**: Just file packaging, no compilation
5. **includedirs = ['lib/ruby/stdlib']**: Matches JRuby's stdlib directory structure
