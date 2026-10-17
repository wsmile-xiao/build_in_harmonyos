script_folder="/storage/Users/currentUser/opt/ai-worker/repo/archives/w/wireguard-tools/1.0.20250521/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanrunenv-release-armv8.sh"
for v in PATH
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanrunenv-release-armv8.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanrunenv-release-armv8.sh"
   fi
done

export PATH="/storage/Users/currentUser/.conan2/p/b/wiregfb79f7136d9fa/p/bin${PATH:+:$PATH}"