#!/usr/bin/env bash
#
# LICENSE: GPLv3+
# Author: risca (Riccardo Scartozzi)
# Version: 0.0.1
#
set -e
ROOT="$1"  # working directory
CONF="$2"  # repository configuration (as json)

conf() {
  printf '%s' ${CONF} | jq -r "$1"
}
readvar() {
  printf '%s' $(conf ". | select(.$1) | .$1")
}
echo "Cloning $(conf .name)"

dest=$(readvar destination)
origin=$(readvar origin)
upstream=$(readvar upstream)
if [ -n "$origin" ]; then
  repo="$origin"
elif [ -n "$upstream" ]; then
  repo="$upstream"
else
  echo "Required at list an \"origin\" or \"upstream\" option!"
  exit 1
fi

if [ -d "$dest" ]; then
  cd "$dest"
  if [ -n "$(readvar ref)" -a "$(git symbolic-ref -q --short HEAD || git describe --tags --exact-match)" == "$(readvar ref)" ]; then
    echo "Up to date"
    exit 0
  else
    exit 1
  fi
fi

if [ -n "$(readvar ref)" ]; then
  git clone --depth 1 --branch "$(readvar ref)" --single-branch $repo $dest
  if [ -n "$(readvar sha)" ]; then
    if [ "$(readvar sha)" != "$(bash -c "cd \"$dest\" && git show-ref -s \"$(readvar ref)\"")" ] ; then
      echo "Sha mismatch! Wanted $(readvar sha), found $(bash -c "cd \"$dest\" && git show-ref -s \"$(readvar ref)\"")"
      rm -r $dest
      exit 1
    fi
  fi
else
  git clone $repo $dest
fi

exit 0
