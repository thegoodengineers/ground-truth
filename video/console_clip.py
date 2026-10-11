"""The AWS console proof shot: video/supply/console.mp4, 1920x1080, about 15 s, from the real console.

    python video/console_clip.py [--seconds 15] [--profile groundtruth]

A read-only federated console session (STS GetFederationToken with a policy that can only read) opens the real
console in headless Chromium and films, slowly and steadily:
  1. CloudWatch → Dashboards → ground-truth, scrolled smoothly from top to bottom (every hourly run and the city's answers)
  2. CloudWatch → Alarms (the four ground-truth alarms, the site-down probe among them), held with a slow push-in
  3. Lambda → Functions, filtered to the three ground-truth functions, held with a slow push-in
then cut together with short dissolves. No cursor, no typing. The console's top bar (account id, session name) is
outside every frame: the viewport is 48 px taller and each frame is clipped below it. The pages chosen show names,
states and graphs, never ARNs.

Needs: the groundtruth AWS profile (or AWS_PROFILE), Playwright's Chromium, ffmpeg.
"""
import json, os, shutil, subprocess, sys, tempfile, urllib.parse, urllib.request

import boto3
from playwright.sync_api import sync_playwright

from frames import FPS, H, HERE, W, launch

OUT = HERE / "supply" / "console.mp4"
DASHBOARD = "ground-truth"
HEADER = 48  # px of the console's top bar, kept out of every frame
FADE = 0.6
READ_ONLY = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Resource": "*", "Action": [
    "cloudwatch:Get*", "cloudwatch:List*", "cloudwatch:Describe*", "logs:Describe*", "logs:Get*", "logs:FilterLogEvents",
    "logs:StartQuery", "logs:StopQuery", "lambda:Get*", "lambda:List*", "sns:List*", "sns:Get*", "tag:Get*",
    "iam:ListAccountAliases", "oam:List*", "events:Describe*", "events:List*"]}]}
# the console's onboarding bubbles and help drawers are noise on a proof shot
TIDY = """() => {
  for (const el of document.querySelectorAll('[role=dialog], [class*=popover]')) {
    const r = el.getBoundingClientRect();
    if (r.width < 700 && r.height < 400) el.remove();
  }
}"""
# the element that actually scrolls (the console scrolls an inner container, not the window)
SCROLLER = """() => {
  let best = document.scrollingElement, room = best.scrollHeight - best.clientHeight;
  for (const el of document.querySelectorAll('*')) {
    const st = getComputedStyle(el);
    if (!/(auto|scroll)/.test(st.overflowY)) continue;
    const r = el.scrollHeight - el.clientHeight;
    if (r > room + 50 && el.clientHeight > 400) { best = el; room = r; }
  }
  best.setAttribute('data-gt-scroller', '1');
  return room;
}"""


def signin_url(session, destination):
    sts = session.client("sts")
    tok = sts.get_federation_token(Name="gt-console-clip", Policy=json.dumps(READ_ONLY), DurationSeconds=900)["Credentials"]
    body = json.dumps({"sessionId": tok["AccessKeyId"], "sessionKey": tok["SecretAccessKey"], "sessionToken": tok["SessionToken"]})
    q = urllib.parse.urlencode({"Action": "getSigninToken", "SessionDuration": "900", "Session": body})
    token = json.load(urllib.request.urlopen("https://signin.aws.amazon.com/federation?" + q))["SigninToken"]
    return "https://signin.aws.amazon.com/federation?" + urllib.parse.urlencode(
        {"Action": "login", "Issuer": "ground-truth", "Destination": destination, "SigninToken": token})


def encode(frames_dir, pattern, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(frames_dir, pattern),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out)], check=True)


def still(png, seconds, out):
    """A still held with a slow push-in (4%), centred."""
    n = int(seconds * FPS)
    push = f"zoompan=z='1+0.04*on/{n}':d={n}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", f"{seconds:.2f}", "-i", str(png),
                    "-vf", f"scale={W * 2}:-2,{push},format=yuv420p", "-t", f"{seconds:.2f}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(out)], check=True)


def main(args):
    seconds = float(args[args.index("--seconds") + 1]) if "--seconds" in args else 15.0
    profile = args[args.index("--profile") + 1] if "--profile" in args else os.environ.get("AWS_PROFILE", "groundtruth")
    session = boto3.Session(profile_name=profile, region_name="us-east-1")
    region, console = "us-east-1", "https://us-east-1.console.aws.amazon.com"
    dash = f"{console}/cloudwatch/home?region={region}#dashboards/dashboard/{DASHBOARD}"
    alarms = f"{console}/cloudwatch/home?region={region}#alarmsV2:"  # filtered by typing below: the URL filter matches whole names only
    funcs = f"{console}/lambda/home?region={region}#/functions?fo=and&o0=%3A&v0=ground-truth"
    t_dash = seconds * 0.46  # the dashboard scroll is the longest part
    t_still = (seconds - t_dash + 2 * FADE) / 2
    work = tempfile.mkdtemp(prefix="gt-console-")
    clip = lambda name: os.path.join(work, name)  # noqa: E731
    clip_area = {"x": 0, "y": HEADER, "width": W, "height": H}

    with sync_playwright() as p:
        b = launch(p)
        page = b.new_context(viewport={"width": W, "height": H + HEADER}, device_scale_factor=1).new_page()
        page.goto(signin_url(session, dash), wait_until="domcontentloaded", timeout=90000)
        # 1. the dashboard: let every widget load (a first pass down and back), then film a smooth scroll
        try:  # a widget title, so we know the dashboard itself (not only the breadcrumb) is there
            page.wait_for_selector("text=Hours since the newest scored hour", timeout=90000)
        except Exception:
            print("dashboard: the first widget never appeared, filming the page as it is")
        page.wait_for_timeout(12000)
        room = page.evaluate(SCROLLER)
        scroll = "(y) => document.querySelector('[data-gt-scroller]').scrollTop = y"
        for k in range(1, 11):
            page.evaluate(scroll, room * k / 10)
            page.wait_for_timeout(1500)
        page.evaluate(scroll, 0)
        page.wait_for_timeout(4000)
        page.evaluate(TIDY)
        n = int(t_dash * FPS)
        hold = int(0.8 * FPS)  # a beat at the top and at the bottom
        for i in range(n):
            f = min(1.0, max(0.0, (i - hold) / max(1, n - 2 * hold)))
            ease = f * f * (3 - 2 * f)
            page.evaluate(scroll, room * ease)
            page.screenshot(path=clip(f"d{i:04d}.jpg"), type="jpeg", quality=92, clip=clip_area)
        print(f"dashboard: {n} frames over {room}px of scroll")
        # 2. the alarms, 3. the functions: stills
        stills = (("alarms", alarms, "text=ground-truth-site-down"), ("functions", funcs, "text=ground-truth-ProbeFunction"))
        for name, url, ready in stills:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            if name == "alarms":
                try:
                    page.wait_for_selector("text=ground-truth-site-down", timeout=45000)  # the list is there
                    box = page.locator("input[type=search], input[placeholder*='ilter']").first
                    box.fill("ground-truth")
                    box.press("Enter")
                except Exception:
                    print("alarms: the filter box never appeared")
            try:
                page.wait_for_selector(ready, timeout=45000)
            except Exception:
                print(f"{name}: '{ready}' never appeared, taking the page as it is")
            page.wait_for_timeout(5000)
            page.evaluate(TIDY)
            page.wait_for_timeout(600)
            page.screenshot(path=clip(f"{name}.png"), clip=clip_area)
            print(f"{name}: {url.split('#')[0]}")
        b.close()

    encode(work, "d%04d.jpg", clip("dash.mp4"))
    still(clip("alarms.png"), t_still, clip("alarms.mp4"))
    still(clip("functions.png"), t_still, clip("functions.mp4"))
    a = t_dash - FADE
    c = a + t_still - FADE
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", clip("dash.mp4"), "-i", clip("alarms.mp4"), "-i", clip("functions.mp4"),
                    "-filter_complex", f"[0][1]xfade=transition=fade:duration={FADE}:offset={a:.2f}[x];"
                                       f"[x][2]xfade=transition=fade:duration={FADE}:offset={c:.2f},format=yuv420p[v]",
                    "-map", "[v]", "-t", f"{seconds:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-an", str(OUT)],
                   check=True)
    for src, dst in (("d0000.jpg", "console-dash.jpg"), ("alarms.png", "console-alarms.png"), ("functions.png", "console-functions.png")):
        shutil.copy(clip(src), HERE / "build" / dst)  # for a look before the cut
    shutil.rmtree(work, ignore_errors=True)
    print(f"{seconds:.0f}s of the real console -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:])
