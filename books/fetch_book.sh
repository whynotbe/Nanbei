#!/bin/bash
# usage: fetch_book.sh <md5> <outfile>
md5=$1; out=$2
for i in 1 2 3; do
  curl -sS --max-time 60 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://libgen.li/ads.php?md5=$md5" -o page_tmp.html 2>/dev/null
  get_url=$(py fetch_link.py "$md5" 2>/dev/null)
  if [ -n "$get_url" ]; then
    case "$get_url" in http*) full="$get_url";; /*) full="https://libgen.li$get_url";; *) full="https://libgen.li/$get_url";; esac
    echo "[$out] GET: $full"
    curl -sS --max-time 600 -A "Mozilla/5.0" -L "$full" -o "$out" && { echo "[$out] done $(stat -c%s "$out") bytes"; exit 0; }
  fi
  echo "[$out] attempt $i failed, retry in 8s"; sleep 8
done
exit 1
