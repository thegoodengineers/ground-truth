"""The Makefile's settings: `make seed` must hand backfill.py a city from src/regions/, not the AWS region."""
import os, re, shutil, subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def makefile():
    return open(os.path.join(ROOT, "Makefile"), encoding="utf-8").read()


def defaults():
    """{NAME: [values]} for every top-level `NAME ?= value` line."""
    out = {}
    for name, value in re.findall(r"^([A-Z_]+)\s*\?=[ \t]*(.*?)\s*$", makefile(), re.M):
        out.setdefault(name, []).append(value)
    return out


def test_each_setting_is_defined_once():
    # with ?= the first line wins, so a second one is silently ignored
    assert {k: v for k, v in defaults().items() if len(v) > 1} == {}


def test_seed_backfills_a_city_and_talks_to_aws_in_an_aws_region():
    seed = re.search(r"^seed:\n((?:\t.*\n)+)", makefile(), re.M).group(1)
    city_var = re.search(r"backfill\.py .*--region \$\((\w+)\)", seed).group(1)
    aws_var = re.search(r"^AWS\s*=.*--region \$\((\w+)\)", makefile(), re.M).group(1)
    assert city_var != aws_var
    city = defaults()[city_var][0]
    assert os.path.exists(os.path.join(ROOT, "src", "regions", f"{city}.json"))
    assert re.fullmatch(r"[a-z]{2}(-[a-z]+)+-\d", defaults()[aws_var][0])


def dry_run(*args):
    """`make -n seed` (prints the commands, runs none: the Makefile has no $(shell) or $(MAKE)), with no REGION
    or CITY from the environment, so the Makefile's own defaults are what's tested."""
    env = {k: v for k, v in os.environ.items() if k not in ("REGION", "CITY")}
    out = subprocess.run(["make", "-n", "seed", *args], cwd=ROOT, env=env, capture_output=True, text=True, check=True).stdout
    backfill = next(line for line in out.splitlines() if "backfill.py" in line)
    aws = next(line for line in out.splitlines() if line.startswith("aws "))
    return backfill, aws


@pytest.mark.skipif(shutil.which("make") is None, reason="needs GNU make (CI has it)")
def test_make_seed_expands_the_city_and_the_aws_region():
    backfill, aws = dry_run()
    assert "--region delhi" in backfill
    assert "--region us-east-1" in aws
    backfill, aws = dry_run("CITY=mumbai")
    assert "--region mumbai" in backfill
    assert "--region us-east-1" in aws
