PROFILE ?= groundtruth
REGION  ?= us-east-1
STACK   ?= ground-truth
# Alarms and the budget email go here (issue 23, 36). Empty = no email subscription.
ALERT_EMAIL ?=
# "true" once AWS Support has verified the account for CloudFront (issue 2); until then a function URL serves HTTPS.
USE_CLOUDFRONT ?= false
# Which city: a file in src/regions/ (delhi, mumbai). Not REGION, which is the AWS region above; the Lambda's REGION is set in template.yaml.
CITY ?= delhi
AWS      = aws --profile $(PROFILE) --region $(REGION)
OUT      = $(AWS) cloudformation describe-stacks --stack-name $(STACK) --query "Stacks[0].Outputs[?OutputKey=='$(1)'].OutputValue" --output text

.PHONY: setup local test lint deploy stack site sample seed run url

# One-time: dev tools (tests, lint, video). The backend itself has no dependencies.
setup:
	pip install -r requirements-dev.txt

# The site on http://localhost:8000 with the committed sample data; no AWS needed.
local:
	rm -rf site/data && cp -r sample/data site/data
	python -m http.server 8000 -d site

test:
	pytest -q tests

lint:
	ruff check src tests video
	cfn-lint template.yaml

# Everything: infra + code, then the static site.
deploy: stack site

stack:
	sam build
	sam deploy --stack-name $(STACK) --profile $(PROFILE) --region $(REGION) \
		--capabilities CAPABILITY_IAM --resolve-s3 --no-confirm-changeset --no-fail-on-empty-changeset \
		--tags project=ground-truth \
		--parameter-overrides AlertEmail=$(ALERT_EMAIL) UseCloudFront=$(USE_CLOUDFRONT)

# Upload site/ without touching data/ (the Lambda owns it), then refresh CloudFront when there is one.
site:
	$(AWS) s3 sync site/ s3://$$($(call OUT,SiteBucketName))/ --delete --exclude "data/*" --cache-control "public, max-age=300"
	$(AWS) s3 sync site/vendor/ s3://$$($(call OUT,SiteBucketName))/vendor/ --cache-control "public, max-age=604800"
	@dist=$$($(call OUT,DistributionId)); if [ -n "$$dist" ]; then \
		$(AWS) cloudfront create-invalidation --distribution-id $$dist --paths "/*" >/dev/null && echo "CloudFront invalidated"; fi
	@echo "site uploaded to $$($(call OUT,SiteUrl))"

# Until the first live run: publish the committed sample (real scorer output) as data/ so the site has something to show.
sample:
	$(AWS) s3 sync sample/data/ s3://$$($(call OUT,SiteBucketName))/data/ --exclude "raw/*" --cache-control "public, max-age=300"

# One-off: seed the 28-day cache from the public archive so the first run has history.
seed:
	python src/backfill.py .cache/hourly.json --days 29 --cache .cache/archive --region $(CITY)
	$(AWS) s3 cp .cache/hourly.json s3://$$($(call OUT,SiteBucketName))/data/raw/hourly.json

# Run the ingest now instead of waiting for the hour; prints the run's summary.
run:
	$(AWS) lambda invoke --function-name $$($(call OUT,IngestFunctionName)) --cli-read-timeout 700 /dev/stdout

url:
	@$(call OUT,SiteUrl)
	@$(call OUT,SiteWebsiteUrl)

# The demo video (video/script.md): narration, HTML scenes, the site captured on a fake clock, cut with captions.
# Needs the site served with data on SITE_URL (default: make local in another terminal), ffmpeg, Playwright's Chromium.
SITE_URL ?= http://localhost:8000
video:
	python video/narrate.py
	python -m pytest -q tests --ignore=tests/site -p no:cacheprovider > video/assets/pytest.txt || true
	python video/record.py
	python video/capture_demo.py --url $(SITE_URL)
	python video/assemble.py
