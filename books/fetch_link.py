import re, sys
md5 = sys.argv[1]
h = open('page_tmp.html', encoding='utf-8', errors='replace').read()
m = re.search(r'href="([^"]*get\.php\?md5=' + md5 + r'&key=[^"]+)"', h)
print(m.group(1) if m else '')
