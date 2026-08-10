script_folder="/storage/Users/currentUser/opt/ai-worker/repo/archives/l/lua-resty-http/0.17.2/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanrunenv-armv8.sh"
for v in 
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanrunenv-armv8.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanrunenv-armv8.sh"
   fi
done
