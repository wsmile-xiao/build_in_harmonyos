script_folder="/storage/Users/currentUser/runner002/build_in_harmonyos/archives/a/arduino-mk/1.6.0/test_package"
echo "echo Restoring environment" > "$script_folder/deactivate_conanrunenv.sh"
for v in PATH
do
   is_defined="true"
   value=$(printenv $v) || is_defined="" || true
   if [ -n "$value" ] || [ -n "$is_defined" ]
   then
       echo export "$v='$value'" >> "$script_folder/deactivate_conanrunenv.sh"
   else
       echo unset $v >> "$script_folder/deactivate_conanrunenv.sh"
   fi
done

export PATH="/storage/Users/currentUser/.conan2/p/b/arduia15dfd5c2cd04/p/bin${PATH:+:$PATH}"