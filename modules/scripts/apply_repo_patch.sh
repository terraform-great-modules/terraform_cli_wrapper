#!usr/bin/env bash
#
# LICENSE: GPLv3+
# Author: risca (Riccardo Scartozzi)
# Version: 0.0.1
#
#
# patches format:
# - list of patches:
#   - as text
#   - as dict: {"name": "...", "content": "..."}
# - directory path
#
# Commands:
# - import
# - apply all
# - default to import and apply all

set -e
ROOT="$1"  # working directory
CONF="$2"  # repository configuration (as json)
QUILTPC="patches"


conf() {
  printf '%s' "${CONF}" | jq -r "$1"
}
readvar() {
  printf '%s' "$(conf ". | select(.$1) | .$1")"
}

echo "Checking patch for $(conf .name)"

dest=$(readvar destination)
cd $dest
echo "Working on $(pwd)"

# backend
is_bklist() {
  [ "$(conf "if (.patches | type==\"string\") then \"folder\" else \"list\" end")" = "list" ] && return 0 || return 1
}
backend () {
  backend="$(conf "if (.patches | type==\"string\") then \"folder\" else \"list\" end")"
  cmd="$1"
  nth="$2"
  if is_bklist ; then
    :
  else
    folder_path="${dest}/$(conf ".patches")"
    name_list=($(ls "${folder_path}/*.patch" | sort))
  fi
  case "$cmd" in
    "")         echo "Missing command" && return 1;;
    "length")   is_bklist && \
                  (echo "$(conf ".patches | length - 1")"; return 0) || \
                  (echo "${#name_list[*]}"; return 0) ;;
    "name")     if is_bklist; then
                  if [ "$(conf "if (.patches[$nth] | type==\"object\") then \"dict\" else \"str\" end")" = "str" ]; then
                    echo "patch_$nth.patch"
                  else
                    echo "$(conf ".patches[$nth].name")"
                  fi
                else 
                  echo "${name_list[$nth]}"
                fi ;;
    "content")  if is_bklist; then
                  if [ "$(conf "if (.patches[$nth] | type==\"object\") then \"dict\" else \"str\" end")" = "str" ]; then
                    echo "$(conf ".patches[$nth]")"
                  else
                    echo "$(conf ".patches[$nth].content")"
                  fi
                else
                  cat "${folder_path}/${name_list[$nth]}"
                fi ;;
    "import")   if is_bklist; then
                  quilt import -P "$(backend name $nth)" <(backend content $nth) || (echo "Error importing patch..."; exit 10)
                else
                  quilt import -P "$(backend name $nth)" "${folder_path}/${name_list[$nth]}" || (echo "Error importing patch..."; exit 10)
                fi ;;
  esac
}


import_patches () {
  quilt pop -a || echo "No patch already applied" # Go to clean status
  local_patches=($(quilt series))
  if (( ${#local_patches[*]} > $(backend length) + 1 )) ; then
    echo "Too many patches already locally applied" && exit 1
  fi

  for patch_n in $(seq 0 "$(backend length)")
  do
    echo $patch_n
    if [ -z "${local_patches[$patch_n]}" ]; then
      echo "Adding new patch..."
      backend import $patch_n
      continue
    fi
    if [ "$(basename "${local_patches[$patch_n]}")" != "$(backend name $patch_n)" ]; then
      echo "Patch name mismatch for \"${local_patches[$patch_n]}\" and \"$(backend name $patch_n)\"" && exit 1
    fi
    if diff "${local_patches[$patch_n]}" <(backend content $1) ; then
      echo "Patch already alligned..."
    else
       echo "Patch content mismatch!"
       echo "$(diff "${local_patches[$patch_n]}" <(backend content $1))"
       exit 1
    fi
  done
}

has_local_patches () {
  if [ ! -d "${QUILTPC}" ]; then
    return 1
  fi
  if [ $(quilt series | wc -l ) -eq 0 ]; then
    #echo false
    return 1
  else
    #echo true
    return 0
  fi
}

has_patches_to_import () {
  patches=$(readvar patches)

  if [ -z "$patches" ]; then
    has_local_patches \
      && { echo "No patching required, but locally found a list of patches!"; exit 1 ; } \
      || { echo "No patching required"; exit 0 ; }
  fi
}

quilt_init () {
  # initialize quilt on destination folder
  mkdir -p "${QUILTPC}"
}

push_all () {
  quilt push -a # echo "error to push patches"
}

quilt_init 
has_patches_to_import 
import_patches 
push_all

exit 0
