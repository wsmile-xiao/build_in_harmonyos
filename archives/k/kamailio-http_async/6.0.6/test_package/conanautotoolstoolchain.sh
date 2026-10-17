script_folder="/storage/Users/currentUser/.atomcode/skills/build_in_harmonyos/archives/k/kamailio-http_async/6.0.6/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanautotoolstoolchain.sh"
for v in CC CXX CPPFLAGS CXXFLAGS CFLAGS LDFLAGS PKG_CONFIG_PATH
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanautotoolstoolchain.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanautotoolstoolchain.sh"
   fi
done

export CC="/data/service/hnp/bin/clang"
export CXX="/data/service/hnp/bin/clang++"
export CPPFLAGS="${CPPFLAGS:-}${CPPFLAGS:+ }-DNDEBUG"
export CXXFLAGS="${CXXFLAGS:-}${CXXFLAGS:+ }-stdlib=libc++ -std=c++17 -O3"
export CFLAGS="${CFLAGS:-}${CFLAGS:+ }-O3"
export LDFLAGS="$LDFLAGS"
export PKG_CONFIG_PATH="/storage/Users/currentUser/.atomcode/skills/build_in_harmonyos/archives/k/kamailio-http_async/6.0.6/test_package${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"