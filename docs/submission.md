# Submission

The text for the Environmental Hacks form. Every number traces to `spike/RESULTS.md`, `docs/LEARNINGS.md`, a test, or the live data. Fill the three [brackets] on Sunday.

**Project name:** Ground Truth

**Track:** Air

**One line:** Which of Delhi's air-quality numbers can you trust? Every monitor, checked every hour against its neighbours, its own past and physics.

**Links:** live site [CloudFront URL] · repo https://github.com/thegoodengineers/ground-truth · demo video [YouTube URL] · blog [Builder Center URL]

---

## The problem (Idea and Impact)

Delhi makes real decisions on air-quality readings: whether a school keeps assembly outdoors, whether a parent takes a child to the park, when construction stops. But a published reading tells you nothing about the monitor behind it. Sensors drift, break and get moved, and in October 2025 water tankers were filmed near a Delhi monitor.

**Who it's for:** the school principal deciding at 7:30, the parent planning a walk, and the reporter or official checking a claim.

**What changes for them:** Ground Truth tells them in plain words whether their monitor agrees with the monitors around it. When it doesn't, it shows what the four nearest monitors read right now, so they have a number they can act on instead of one they can't trust.

## What we built

Every hour, each of the 52 monitors in Delhi and the NCR gets three checks:
- **Physics:** can the reading be real? Fine dust (PM2.5) can never exceed all dust (PM10); we also catch out-of-range values and stuck sensors.
- **Neighbours:** does it agree, hour by hour, with the four nearest monitors? We correct for daytime air mixing, which otherwise makes every polluted hotspot look cleaner by day.
- **History:** has it suddenly changed against its own last three weeks?

Each monitor gets one answer: agrees with neighbours, worth a look, or doesn't add up, with the evidence one click away. The site explains this in ten seconds with one real monitor, then lets you explore Delhi in 3D. Each monitor is a mast whose column is as tall as its PM2.5 reading, with smog that thickens where the air is worse.

**What we found, honestly:** in Oct-Nov 2025, Vikas Sadan (Gurugram) reported more fine dust than total dust in 31% of hours. We also tested whether the monitors named in the October 2025 news show a spraying pattern. On a method fixed before looking, they don't stand out (Anand Vihar ranked 6th, Jahangirpuri 13th of 38), and we say so on the site.

## Where AWS fits (Built on AWS)

- **Amazon EventBridge** runs the check every hour.
- **AWS Lambda** (Python 3.11) reads new readings from the OpenAQ API, runs the three checks and writes the results as JSON.
- **AWS Systems Manager Parameter Store** holds the OpenAQ API key, encrypted.
- **Amazon S3** keeps a 29-day history cache and the results.
- **Amazon CloudFront** serves the site and the data from a private bucket.
- **AWS SAM** deploys all of it from one template. History is seeded from the public OpenAQ archive on the **Registry of Open Data on AWS**, in the same region.

The video shows the running stack in the AWS console.

## Design and usability

Plain words instead of scores, and every state shown with a shape and a word, never colour alone. The answer comes first and the evidence one click later. The site works on a phone, explains itself before asking anything of the visitor, and has a self-playing tour.

## Does it work? (The execution)

- **The live site** updates every hour. [Data through: time on the live site at submission.]
- **The planted test:** we lowered one quiet monitor's daytime PM10 by 40% in real data, one monitor at a time. It was caught 30 times out of 30, and wrongly flagged another monitor only 3 times across all 30 runs.
- **62 automated tests** run on every change.

## Challenges

- The public archive runs about four days behind, so live hours come from the OpenAQ API.
- The API averages over UTC hours, which are half an hour off Indian hours. We group the raw readings into IST hours ourselves, so live data matches the archive.
- Daytime air mixing makes any hotspot look cleaner by day. We nearly mistook that for a spraying signal.

## What's next

Other Indian cities, a history page per monitor that reporters can cite, and Hindi copy.

## Team

Chirag (Chirag6722), Abhijeet (thegoodengineer), Bhumika (Bhumika-1432006), Ayush (AyushVUpadhye).
