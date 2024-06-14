#!/usr/bin/env bash
. .default.env
[ -f .env ] && . .env

#set -x
set -euo pipefail

function erase() {
  echo "Erasing flash..."
  esptool.py --chip $CHIP --port /dev/$PORT erase_flash
}

function flash() {
  echo "Flashing $1..."
  esptool.py --chip $CHIP --port /dev/$PORT write_flash -z 0 $1
}

function upload() {
  for file in ./src/*.py; do
    if [ -f "$file" ]; then
      echo "Uploading $file to $(basename "$file")..."
      ampy --port /dev/$PORT put "$file" "$(basename "$file")"
      if [ $? -ne 0 ]; then
        echo "Failed to upload $file"
      else
        echo "Successfully uploaded $file"
      fi
    fi
  done
}

# ---

main() {
  local cmd=$1
  shift

  if [ "$(type -t "$cmd")" != "function" ]; then
    die "Usage: stack <command> [options]"
  fi

  $cmd "$@"
}

# shellcheck disable=SC2120
indent() {
  local prefix=${1:-"   "}

  # See: https://stackoverflow.com/a/11287641/537407
  LANG=C sed "s/^/$prefix/g"
}

die() {
  echo "$@"
  exit 1
}

# ---

main "$@"
