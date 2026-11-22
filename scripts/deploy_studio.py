#!/usr/bin/env python3
"""一键部署到魔搭创空间（ModelScope Studio，Docker 类型）。

前置条件：
  1. 设置 MODELSCOPE_API_KEY（ms-xxx，从 https://modelscope.cn/my/myaccesstoken 获取）
  2. Docker 类型创空间需先完成「阿里云账号绑定 + 实名认证」：
     https://modelscope.cn/docs/studios/docker
  3. 本机能访问 modelscope.cn（推送代码用 HTTPS + token）

用法：
  export MODELSCOPE_API_KEY=ms-xxxxxxxx
  python3 scripts/deploy_studio.py --owner <你的用户名> --repo interrogation-room

脚本流程：查用户 → 建 Studio(docker) → 推送代码(main→master) → 写密钥 → 触发部署 → 跟踪日志。
只用标准库，无需额外依赖。
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ENDPOINT = os.environ.get("MODELSCOPE_ENDPOINT", "https://modelscope.cn").rstrip("/")
API = f"{ENDPOINT}/openapi/v1"
TOKEN = os.environ.get("MODELSCOPE_API_KEY", "")
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api(method, path, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        print(f"  HTTP {e.code} {method} {path}: {txt[:300]}")
        raise


def main():
    ap = argparse.ArgumentParser(description="Deploy to ModelScope Studio (Docker)")
    ap.add_argument("--owner", required=True, help="ModelScope 用户名")
    ap.add_argument("--repo", default="interrogation-room", help="创空间仓库名")
    ap.add_argument("--visibility", default="public", choices=["public", "private", "protected"])
    ap.add_argument("--hardware", default="platform/2v-cpu-8g-mem",
                    help="规格；免费为 platform/2v-cpu-8g-mem，paid/* 会计费需单独授权")
    ap.add_argument("--display-name", default="审讯室 · 谎言侦探")
    ap.add_argument("--model", default="Qwen/Qwen2.5-72B-Instruct", help="MODELSPACE_MODEL")
    ap.add_argument("--skip-push", action="store_true", help="跳过代码推送，仅重建/重部署")
    ap.add_argument("--no-wait", action="store_true", help="触发部署后不跟踪日志")
    args = ap.parse_args()

    if not TOKEN:
        sys.exit("❌ 请先 export MODELSCOPE_API_KEY=ms-xxx")

    owner, repo = args.owner, args.repo

    print("→ 1/6 查询用户")
    me = api("GET", "/users/me")
    print("  user:", me.get("data", me))

    print("→ 2/6 检查/创建 Studio")
    try:
        api("GET", f"/studios/{owner}/{repo}")
        print("  Studio 已存在，跳过创建")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("  创建中（sdk_type=docker）...")
            api("POST", "/studios", {
                "owner": owner,
                "repo_name": repo,
                "sdk_type": "docker",
                "visibility": args.visibility,
                "hardware": args.hardware,
                "display_name": args.display_name,
            })
            print("  ✅ 已创建")
        else:
            raise

    if not args.skip_push:
        print("→ 3/6 推送代码到 Studio（本地 main → 远端 master）")
        subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, check=False)
        subprocess.run(["git", "commit", "-m", "Deploy to ModelScope Studio"],
                       cwd=REPO_DIR, check=False)
        subprocess.run(["git", "remote", "remove", "modelscope"], cwd=REPO_DIR, check=False)
        ms_host = ENDPOINT.split("://", 1)[-1]
        remote = f"https://oauth2:{TOKEN}@{ms_host}/studios/{owner}/{repo}.git"
        subprocess.run(["git", "remote", "add", "modelscope", remote], cwd=REPO_DIR, check=True)
        # 若远端已有 master（二次部署），先合并避免 non-fast-forward
        subprocess.run(["git", "fetch", "modelscope", "master"], cwd=REPO_DIR, check=False)
        subprocess.run(["git", "merge", "modelscope/master", "--allow-unrelated-histories",
                        "-m", "Merge studio master"], cwd=REPO_DIR, check=False)
        subprocess.run(["git", "push", "modelscope", "main:master"], cwd=REPO_DIR, check=True)
        print("  ✅ 已推送")

    print("→ 4/6 配置密钥")
    api("POST", f"/studios/{owner}/{repo}/secrets", {"key": "MODELSPACE_API_KEY", "value": TOKEN})
    api("POST", f"/studios/{owner}/{repo}/secrets", {"key": "MODELSPACE_MODEL", "value": args.model})
    print("  ✅ secrets 已设置（MODELSPACE_API_KEY / MODELSPACE_MODEL）")

    print("→ 5/6 触发部署")
    api("POST", f"/studios/{owner}/{repo}/deploy")
    print("  ✅ 已触发")

    if not args.no_wait:
        print("→ 6/6 跟踪构建/运行日志（Ctrl+C 可中断）")
        for _ in range(60):
            time.sleep(10)
            try:
                build = api("GET", f"/studios/{owner}/{repo}/logs/build")
                run = api("GET", f"/studios/{owner}/{repo}/logs/run")
                b = str(build.get("data", ""))
                r = str(run.get("data", ""))
                print(f"  --- build tail ---\n{b[-400:]}")
                print(f"  --- run tail ---\n{r[-400:]}")
                if "uvicorn running" in r.lower() or "application startup complete" in r.lower():
                    print("  ✅ 服务已启动")
                    break
            except urllib.error.HTTPError:
                pass
            except Exception as e:  # noqa: BLE001
                print("  log err:", e)

    print(f"\n🎉 Studio 地址：{ENDPOINT}/studios/{owner}/{repo}")


if __name__ == "__main__":
    main()