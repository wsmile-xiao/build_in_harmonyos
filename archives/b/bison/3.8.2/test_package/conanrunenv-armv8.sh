set -euo pipefail
script_folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "echo Restoring environment" > "$script_folder/deactivate_conanrunenv-armv8.sh"
for v in PATH
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

export PATH="/data/service/hnp/bin:${PATH}"
