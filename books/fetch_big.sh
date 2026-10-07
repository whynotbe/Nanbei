#!/bin/bash
# usage: fetch_big.sh <md5> <outfile>
export https_proxy=http://127.0.0.1:7897 http_proxy=http://127.0.0.1:7897
md5=$1; out=$2
for i in $(seq 1 40); do
  curl -sS --max-time 60 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://libgen.li/ads.php?md5=$md5" -o page_tmp.html 2>/dev/null
  get_url=$(py fetch_link.py "$md5" 2>/dev/null)
  [ -z "$get_url" ] && { sleep 6; continue; }
  case "$get_url" in http*) full="$get_url";; /*) full="https://libgen.li$get_url";; *) full="https://libgen.li/$get_url";; esac
  curl -sS --max-time 240 -A "Mozilla/5.0" -L -C - "$full" -o "$out" 2>err_tmp.txt
  rc=$?
  sz=$(stat -c%s "$out" 2>/dev/null || echo 0)
  echo "attempt $i rc=$rc size=$sz"
  if [ $rc -eq 0 ]; then echo "COMPLETE $sz"; exit 0; fi
  grep -q "range" err_tmp.txt && { rm -f "$out"; echo "server no-range, restart"; }
  sleep 5
done
echo "GAVE UP at $sz"; exit 1
