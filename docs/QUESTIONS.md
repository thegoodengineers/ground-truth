# Open questions

Each question has a default we proceed on until someone answers. Answer in place, with a name and date.

## Blockers

1. **Bhumika has read-only access to the repo.** *Default:* she works from a fork and opens PRs from it. Fix: Chirag raises her to Write (Settings -> Collaborators).
2. **Ayush isn't a collaborator yet.** *Default:* he helps with QA and review without pushing. Fix: invite AyushVUpadhye with Write.
3. **The exact deadline hour on Sun 11 Oct.** The schedule page says the hours are "being finalised"; the countdown on 8 Oct pointed to about Sunday evening IST. *Default:* the video is made and the form submitted on Sunday, early in the day, so the hour doesn't matter. Check every link in a signed-out browser before submitting.
4. ~~CloudFront on the account's plan~~ **Answered (Abhijeet, 9 Oct):** blocked. CloudFront answers `Your account must be verified before you can add new CloudFront resources` (a support case is needed). The stack keeps CloudFront behind `UseCloudFront=false`; a Lambda function URL serves the site over HTTPS with the same security headers, and the S3 website endpoint is the HTTP fallback. Flip the parameter once Support verifies the account.

## Rules and judging (answered from wemakedevs.org/aws/env, 8 Oct)

5. ~~Judging criteria~~ **Answered:** Idea and Impact, Built on AWS, Design and usability, The execution, The demo video. Marks per line are not published. The rubric table is in `docs/PLAN.md`.
6. ~~What a submission is~~ **Answered:** a public repo, a YouTube video under 3 minutes (public or unlisted), and a short writeup covering the problem, the build and where AWS fits. No live demo; judges only see what's submitted.
7. ~~Pre-event work~~ **Answered:** project work starts when the clock does, and the repo history must match the event dates. Every commit in this repo is dated 8 Oct 2026 or later.
8. ~~AWS account~~ **Answered:** any account; the free tier counts in full. AWS services or AWS open source are mandatory for prizes, and the video must show it.

## Data and product

9. **First live run (`make run`):** the `datetime_from`, `limit` and `page` query names on `/sensors/{id}/measurements` come from the docs and haven't been called with a key yet. *Default:* they work; check that `overlap_ratio` is about 1.0. The free limit is 60/min and 2,000/hour; a run makes about 260 calls in about 5 min.
10. **NCR stations on the map?** *Default:* yes, labelled NCR; they hold the clearest physics failures (Vikas Sadan, Arya Nagar).
11. **Watch/flag thresholds** are v1 (`docs/PLAN.md`). *Default:* frozen as they are; never tuned to make a particular station light up.
12. **Wording for flagged stations.** *Default:* "agrees with neighbours", "worth a look", "doesn't add up", "no data". Never "fake", "tampered" or "sprayed" (enforced by `test_copy_never_accuses`).
13. **Which number to show a person when their station is in doubt.** *Default:* the median PM2.5 of the 4 nearest stations right now (`neighbours_latest`), labelled as such, never presented as an official reading.
