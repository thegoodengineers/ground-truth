"""The AWS console proof shot (issue 4): video/supply/console.mp4, 1920x1080, from the real console.

    python video/console_clip.py [--seconds 14] [--profile groundtruth]

A read-only federated console session (STS GetFederationToken with a policy that can only read) opens the real
console in headless Chromium and dwells on three pages: the ingest Lambda's Monitor tab (the hourly invocations),
the EventBridge schedule, and the site bucket's data/ objects with their timestamps. Each page is screenshotted
once it settles and held with a slow push-in, then the shots are cut together with short dissolves. No cursor,
no typing, no account id on screen beyond what the console itself shows in its header (the pages are chosen so
the header's account menu stays collapsed).

Needs: the groundtruth AWS profile (or AWS_PROFILE), Playwright's Chromium, ffmpeg.
"""
import json, os, subprocess, sys, tempfile, urllib.parse, urllib.request

import boto3
from playwright.sync_api import sync_playwright

from frames import FPS, H, HERE, W, launch

OUT = HERE / "supply" / "console.mp4"
STACK = "ground-truth"
HEADER = 48  # px of the console's top bar to crop: it carries the account id and the session name
TALL = 520   # extra viewport height, so the Lambda Monitor charts are on screen without scrolling
# the console's onboarding tooltips ("Service menu", "Tutorials") are noise on a proof shot: take them out
TIDY = """() => {
  // only the small "Service menu" tour bubble: anything larger is page, not tooltip
  for (const el of document.querySelectorAll('[role=dialog], [class*=popover]')) {
    const r = el.getBoundingClientRect();
    if (r.width < 700 && r.height < 400 && /Service menu/.test(el.innerText || '')) el.remove();
  }
}"""
READ_ONLY = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Resource": "*", "Action": [
    "lambda:Get*", "lambda:List*", "cloudwatch:Get*", "cloudwatch:List*", "cloudwatch:Describe*",
    "logs:Describe*", "logs:Get*", "logs:FilterLogEvents", "events:Describe*", "events:List*",
    "scheduler:Get*", "scheduler:List*", "s3:ListBucket", "s3:ListAllMyBuckets", "s3:GetBucketLocation",
    "cloudformation:Describe*", "cloudformation:List*", "cloudformation:Get*", "sns:List*", "sns:Get*",
    "iam:ListAccountAliases", "tag:Get*"]}]}


def outputs(session):
    cfn = session.client("cloudformation")
    return {o["OutputKey"]: o["OutputValue"] for o in cfn.describe_stacks(StackName=STACK)["Stacks"][0]["Outputs"]}


def rule_name(session, function_name):
    """The EventBridge rule that targets the ingest function."""
    ev = session.client("events")
    for r in ev.list_rules()["Rules"]:
        for t in ev.list_targets_by_rule(Rule=r["Name"])["Targets"]:
            if function_name in t["Arn"]:
                return r["Name"]
    return None


def signin_url(session, destination):
    sts = session.client("sts")
    tok = sts.get_federation_token(Name="gt-console-clip", Policy=json.dumps(READ_ONLY), DurationSeconds=900)["Credentials"]
    body = json.dumps({"sessionId": tok["AccessKeyId"], "sessionKey": tok["SecretAccessKey"], "sessionToken": tok["SessionToken"]})
    q = urllib.parse.urlencode({"Action": "getSigninToken", "SessionDuration": "900", "Session": body})
    token = json.load(urllib.request.urlopen("https://signin.aws.amazon.com/federation?" + q))["SigninToken"]
    return "https://signin.aws.amazon.com/federation?" + urllib.parse.urlencode(
        {"Action": "login", "Issuer": "ground-truth", "Destination": destination, "SigninToken": token})


def main(args):
    seconds = float(args[args.index("--seconds") + 1]) if "--seconds" in args else 14.0
    profile = args[args.index("--profile") + 1] if "--profile" in args else os.environ.get("AWS_PROFILE", "groundtruth")
    session = boto3.Session(profile_name=profile, region_name="us-east-1")
    out = outputs(session)
    fn, bucket = out["IngestFunctionName"], out["SiteBucketName"]
    rule = rule_name(session, fn)
    region = "us-east-1"
    # (url, extra settle ms after the page says it is ready, the text that says so)
    console = f"https://{region}.console.aws.amazon.com"
    pages = [
        (f"{console}/lambda/home?region={region}#/functions/{fn}?tab=monitoring", 60000, "text=CloudWatch metrics"),
        (f"{console}/events/home?region={region}#/eventbus/default/rules/{rule}", 3000, "text=Fixed rate of") if rule else None,
        (f"{console}/s3/buckets/{bucket}?region={region}&prefix=data/&showversions=false", 3000, "text=latest.json"),
    ]
    pages = [p for p in pages if p]
    shots = tempfile.mkdtemp(prefix="gt-console-")
    with sync_playwright() as p:
        b = launch(p)
        # a tall viewport: the Lambda metrics draw only unscrolled, so the shot is a clip lower down the page
        ctx = b.new_context(viewport={"width": W, "height": H + TALL}, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(signin_url(session, pages[0][0]), wait_until="domcontentloaded", timeout=60000)
        for i, (url, settle, ready) in enumerate(pages):
            if i:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_selector(ready, timeout=45000)
            except Exception:
                print(f"shot {i}: '{ready}' never appeared, taking the page as it is")
            page.wait_for_timeout(settle)
            page.evaluate(TIDY)
            page.wait_for_timeout(800)
            top = TALL if i == 0 else 0  # the Lambda shot frames the Monitor section, the others the top of the page
            page.screenshot(path=os.path.join(shots, f"shot{i}.png"), clip={"x": 0, "y": top, "width": W, "height": H})
            print(f"shot {i}: {url.split('#')[0].split('?')[0]}")
        b.close()

    each = seconds / len(pages)
    # a slow push-in on each still (zoompan), then dissolves between them
    inputs, filters = [], []
    for i in range(len(pages)):
        inputs += ["-loop", "1", "-t", f"{each + 0.6:.2f}", "-i", os.path.join(shots, f"shot{i}.png")]
        frames = int((each + 0.6) * FPS)
        push = f"zoompan=z='1+0.04*on/{frames}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}"
        crop = f"crop={W}:{H - HEADER}:0:{HEADER}," if i else ""  # the Lambda clip already starts below the header
        filters.append(f"[{i}:v]{crop}scale=2400:-2,{push},format=yuv420p[v{i}]")
    chain, prev = "", "v0"
    for i in range(1, len(pages)):
        nxt = f"x{i}"
        chain += f"[{prev}][v{i}]xfade=transition=fade:duration=0.6:offset={each * i:.2f}[{nxt}];"
        prev = nxt
    filter_complex = ";".join(filters) + ";" + chain.rstrip(";")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", filter_complex, "-map", f"[{prev}]",
                    "-t", f"{seconds:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-an", str(OUT)], check=True)
    print(f"{seconds:.0f}s of the real console, {len(pages)} pages -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:])
