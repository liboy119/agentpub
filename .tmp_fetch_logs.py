"""Fetch a GitHub Actions job log through the tunnel's flaky DNS.

The log endpoint redirects to a blob storage host that the local resolver
cannot reach. Resolve it via 1.1.1.1 and pin the address with curl --resolve.
"""
import json
import re
import subprocess
import sys
import urllib.request

TOKEN = ""
for line in open(r"G:\AgentPub\.env.tokens", encoding="utf-8"):
    if line.startswith("GITHUB_TOKEN="):
        TOKEN = line.strip().split("=", 1)[1]


def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "agentpub",
                 "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def resolve(host):
    for server in ("1.1.1.1", "8.8.8.8", "223.5.5.5"):
        try:
            out = subprocess.run(
                ["nslookup", host, server], capture_output=True, text=True, timeout=40
            ).stdout
        except Exception:
            continue
        ips = re.findall(r"Addresses?: (\d+\.\d+\.\d+\.\d+)", out)
        ips = [ip for ip in ips if ip != server]
        if ips:
            return ips[-1]
    return None


def fetch_job_log(run_id):
    jobs = api(f"/repos/liboy119/agentpub/actions/runs/{run_id}/jobs")["jobs"]
    for job in jobs:
        print("=" * 70)
        print(f"run {run_id} | job: {job['name']} | {job['conclusion']}")
        print("=" * 70)
        url = f"https://api.github.com/repos/liboy119/agentpub/actions/jobs/{job['id']}/logs"

        # capture the redirect target without following it
        opener = urllib.request.build_opener(NoRedirect)
        try:
            opener.open(urllib.request.Request(url, headers={
                "Authorization": f"Bearer {TOKEN}", "User-Agent": "agentpub"}), timeout=40)
            location = None
        except urllib.error.HTTPError as e:
            location = e.headers.get("Location")
        except Exception as e:
            print(f"redirect lookup failed: {e}")
            location = None

        if location:
            host = urllib.parse.urlparse(location).hostname
            ip = resolve(host)
            print(f"blob host {host} -> {ip}")
            if ip:
                p = urllib.parse.urlparse(location)
                result = subprocess.run(
                    ["curl.exe", "-sS", "-m", "90", "--resolve", f"{host}:443:{ip}",
                     f"https://{host}{p.path}?{p.query}"],
                    capture_output=True, text=True, timeout=120,
                )
                text = result.stdout
            else:
                text = ""
        else:
            result = subprocess.run(
                ["curl.exe", "-sSL", "-m", "90", "-H", f"Authorization: Bearer {TOKEN}",
                 "-H", "User-Agent: agentpub", url],
                capture_output=True, text=True, timeout=120,
            )
            text = result.stdout

        lines = [ln for ln in text.splitlines() if ln.strip()]
        for ln in lines[-60:]:
            print(ln)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


import urllib.error
import urllib.parse

if __name__ == "__main__":
    for rid in sys.argv[1:]:
        fetch_job_log(int(rid))
