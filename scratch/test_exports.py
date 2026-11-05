"""Test script to verify all live PDF and Excel export routes over HTTP."""

import http.cookiejar
import re
import urllib.parse
import urllib.request

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Fetch login page and extract CSRF token
login_page = opener.open("http://127.0.0.1:5000/login").read().decode("utf-8")
match = re.search(r'name="csrf_token" value="([^"]+)"', login_page)
token = match.group(1) if match else ""

# 2. Authenticate as admin
login_data = urllib.parse.urlencode({
    "username": "admin",
    "password": "AdminPassword123!",
    "csrf_token": token,
}).encode("utf-8")
login_resp = opener.open("http://127.0.0.1:5000/login", data=login_data)
print("Login status:", login_resp.getcode())

# 3. Test all export endpoints
endpoints = [
    ("/reports/department/excel?department=all&period=2026-09", "Organization Excel (All Depts, Sep 2026)"),
    ("/reports/department/excel?department=Engineering&period=2026-09", "Engineering Excel (Sep 2026)"),
    ("/reports/department/excel", "Default Department Excel"),
    ("/reports/department/pdf?department=all&period=2026-09", "Organization PDF (All Depts, Sep 2026)"),
    ("/reports/department/pdf?department=Engineering&period=2026-09", "Engineering PDF (Sep 2026)"),
    ("/reports/department/pdf", "Default Department PDF"),
    ("/employees/1/report/pdf?period=2026-09", "Employee 1 PDF (Sep 2026)"),
    ("/employees/1/report/excel?period=2026-09", "Employee 1 Excel (Sep 2026)"),
    ("/employees/1/report/pdf", "Employee 1 PDF (All Time)"),
    ("/employees/1/report/excel", "Employee 1 Excel (All Time)"),
]

for url_path, label in endpoints:
    full_url = "http://127.0.0.1:5000" + url_path
    resp = opener.open(full_url)
    status = resp.getcode()
    ctype = resp.headers.get("Content-Type")
    cdisp = resp.headers.get("Content-Disposition", "")
    content = resp.read()
    print(f"SUCCESS: {label} -> HTTP {status} | {ctype} | {len(content)} bytes | {cdisp[:40]}")

