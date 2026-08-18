# AI_UFC_PREDICTION

## What this project is
A prediction web app that tracks UFC fight cards and combines two fundamentally different
kinds of data to generate predictions: (1) qualitative sentiment from fans and analysts,
retrieved via RAG, and (2) quantitative fighter stats/records, pulled from a structured
database. When a new card is officially announced on the UFC website, the app
automatically scrapes both kinds of data for each fight, and surfaces it through a
Sleeper-app-style UI: clean, card-based, showing crowd/analyst sentiment with cited real
posts per fight, alongside hard stats. There's also an AI chatbot grounded in the RAG
content so users can ask questions about what people are saying.

### The three data pipelines (important — don't collapse into one)
1. **RAG pipeline (unstructured/qualitative)** — Reddit (PRAW), X (free/unofficial
   scraping workaround), and analyst/professional sources (ESPN, Sherdog, MMA Junkie).
   This content is chunked, embedded, and retrieved semantically — used for opinion and
   commentary, where semantic search is genuinely needed.
2. **Structured stats pipeline (factual/quantitative)** — scraped from UFCStats.com.
   Stored in a normal SQL table, queried directly (NOT embedded/chunked — this is exact
   data, not something to semantically search for). Includes: fight history (→ derive
   win streak, record), height, reach, stance, strikes landed per minute, takedown
   average, submission average, date of birth (→ experience/age), weight class history.
3. **Derived features (computed, not scraped)** — built from pipeline #2, fully
   automated (no manual per-fighter work, scales to every fighter every week):
   - **Primary method — rule-based, from UFCStats numbers:** a fighting-style
     classification (wrestler / striker / grappler-leaning / balanced) inferred from
     takedown average, striking accuracy, submission average, etc. Always available
     since every fighter has UFCStats numbers — this is the reliable fallback.
   - **Secondary method — bio text scraping:** scrape fighter bio text (e.g. "a
     wrestling-based fighter," "BJJ background") and either keyword-match it or feed it
     into the RAG pipeline as an additional source, so the LLM can cite it directly in a
     prediction. Richer when available, but not every fighter has a detailed bio, so it
     supplements rather than replaces the rule-based method. **Confirmed 2026-08-15:**
     ESPN and Sherdog fighter pages no longer have prose bio text, just structured stat
     widgets (duplicating UFCStats) — Wikipedia is the only remaining candidate source
     for this. Currently deferred/out of scope; the rule-based primary method is the
     only style-classification signal actually implemented so far.

The final prediction combines all three: hard stats + derived features (direct DB query)
+ retrieved fan/analyst commentary (RAG) fed into the LLM together — not just "here's
what Reddit thinks," but a take grounded in both fact and sentiment.

**Key principle to remember:** structured, exact data (records, stats) belongs in
Postgres tables queried directly. RAG/embeddings are only for unstructured text where
semantic search is actually needed. Don't embed things that should be a SQL lookup.

## Why this project exists (context for how you help)
This is a portfolio project for job applications in **Software Engineering** and
**AI Engineering** roles. The two things the builder is explicitly trying to learn and
put on their resume are:
1. **RAG systems** — chunking, embeddings, retrieval, grounded generation
2. **AWS cloud deployment** — real, hands-on experience, not just theory

**Important working style:** The builder wants to *understand* everything well enough to
explain it in a technical interview — not just have working code. Prefer explaining new
concepts (what it is, why we're using it, how it fits the bigger picture) before or while
writing code for it, especially for anything AWS-related or a new RAG concept. It's fine
and expected that many pieces (Docker, EventBridge, pgvector, ECS, etc.) are being learned
from scratch during this project — treat unfamiliarity as the default, not the exception.

Builder's existing skill background (so you can calibrate explanations — not a beginner
in general, just new to AWS and some RAG-adjacent tooling): prior RAG pipelines (parsing,
chunking, embedding, retrieval), LangChain, ChromaDB, FastAPI, React/React Native, Figma,
LLM orchestration via Groq/OpenRouter. Prior projects: PathReview, RepairSafe, UFit.

## Architecture decisions (already made — don't re-litigate without a reason)
- **Vector DB:** pgvector on AWS RDS (Postgres) — chosen over OpenSearch Serverless for
  learnability (builds on SQL knowledge) and broad resume recognizability.
- **Backend hosting:** ECS/Fargate with Docker — chosen over Lambda (bad fit for
  long-running scraping jobs, 15-min timeout) and EC2 (least transferable skill).
- **Scheduling:** AWS EventBridge triggers scraping jobs on a timer.
- **Update pattern:** Polling + diffing. Scraper runs on a schedule, compares newly
  scraped content against a stored snapshot/state table, and only triggers the full
  ingestion pipeline (chunk, embed, notify frontend) when genuinely new content is found.
- **X/Twitter data:** Free/unofficial scraping workaround (not paid API) — specifically
  `twikit` (logs into a real X account, talks to X's internal API), since Nitter (the
  old no-login scraping option) is effectively dead as of 2024. Known to be fragile and
  ToS gray-area — acceptable for a personal portfolio project, not for production use.
  Uses a **dedicated burner X account**, never the builder's personal one, since the
  account doing the scraping risks suspension.
- **Analyst sites (ESPN/Sherdog/MMA Junkie):** ESPN and MMA Junkie's robots.txt
  explicitly disallow AI crawlers by name (Claude, anthropic-ai, GPTBot). Decided
  2026-08-15 to scrape all three anyway, using the same portfolio-project gray-area
  reasoning already applied to X above — a considered choice, not an oversight.
- **Reddit data (PRAW):** Reddit's Data API Terms explicitly restrict using scraped
  data "to train machine learning or AI models" without approval — a gray area for
  our RAG use (retrieval + LLM prompting, not literal model training, but close
  enough to the spirit of that clause to take seriously). Decided 2026-08-15 to
  register the Reddit API app under a **dedicated secondary/throwaway Reddit
  account**, not the builder's main personal account — same risk-isolation pattern
  as the X burner account above.
- **LLM calls:** Groq/OpenRouter (builder already has experience with these).

## Build order (do not skip ahead without reason)
1. Local data ingestion scripts:
   - [x] Fight cards (UFC.com) — done. `ingestion/fight_cards/scrape_fight_cards.py`,
     14 events in `data/raw/fight_cards/`.
   - [ ] RAG sources: Reddit (PRAW), X (scraping workaround), analyst sites (ESPN/Sherdog/MMA
     Junkie) → save to local JSON — **in progress, see status below**
   - [x] Structured stats: UFCStats.com scrape → fighter records/height/reach/stance/striking
     & grappling averages → save to local JSON/CSV — done.
     `ingestion/ufcstats/scrape_fighter_stats.py`, 304/306 fighters in
     `data/raw/ufcstats/` (2 unmatched are genuine cross-site name-spelling
     mismatches, a documented gap, not a bug).
2. Chunking + embeddings pipeline for RAG sources only (local, sentence-transformers)
   — **done, currently here.** 632 chunks embedded across Sherdog/MMA Junkie/ESPN (384-dim,
   `data/processed/chunks.jsonl`). Verified with real semantic-search
   queries, not just "it ran" — e.g. "trash talk before the fight" correctly
   surfaced actual trash-talk quotes at 0.53 cosine similarity. Reddit chunks
   will flow through the same pipeline automatically once that source is
   unblocked (`collect_reddit_chunks()` already handles it, just no data yet).
   `processing/chunk_and_embed.py`: sentence-grouped chunking
   (~150 words/chunk, 1-sentence overlap between consecutive chunks) + local
   embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim). Reads
   every source under `data/raw/` (articles' `body_text`, Reddit
   submissions/comments once that source is unblocked) and writes one combined
   `data/processed/chunks.jsonl` (gitignored, regenerable like `data/raw/`).
   Article chunks are embedded as `"{title}. {chunk_text}"` (title prefixed for
   topical context) but stored with the clean `text` field alone for citation
   display. **Found and fixed real data-quality bugs before embedding anything**:
   MMA Junkie's article body extraction was pulling in a trailing "related
   stories" `<aside>` widget (fixed: extract only `<p>` tags within the body
   container, not its full textContent); Sherdog's was pulling in raw Twitter/
   Instagram embed fallback HTML and live-scoring `<table>` widgets (fixed:
   strip `blockquote`/`table` before extracting text). Both scrapers were
   re-run after the fix — always re-scrape (don't just re-chunk old data) after
   a scraper-level text-extraction fix like this.
3. Local Postgres: pgvector table for RAG embeddings + a separate plain SQL table for
   structured fighter stats. Write derived-feature logic (style classification, streak,
   experience) on top of the stats table. — not started
4. FastAPI backend (endpoints: fight cards, predictions combining stats + derived
   features + RAG-retrieved commentary w/ citations, RAG chatbot) — not started
5. React frontend (Sleeper-style card UI) — not started
6. Dockerize backend + ingestion jobs — not started
7. Deploy to AWS: RDS (pgvector + stats tables), ECR + ECS/Fargate, EventBridge schedule — not started
8. Frontend hosting (S3/CloudFront or Amplify) — not started

Rationale for this order: get the whole RAG loop working locally and cheaply before any
AWS cost/complexity enters the picture; Docker is the bridge step that makes AWS
deployment tractable instead of overwhelming.

### RAG sources status (step 1, part 2 — in progress)
All scrapers live under `ingestion/rag_sources/`, one file per source, following the
scraper conventions below. Each reads matchups from `data/raw/fight_cards/*.json` and
saves one JSON file per fight to `data/raw/<source>/<event_slug>/<fighter>-vs-<fighter>.json`.

- [x] **Sherdog** — done, `scrape_sherdog.py`, 159/159 fights processed. No anti-bot,
  plain requests+BeautifulSoup works. Its own site search (`/search.php`) is
  **non-functional** — confirmed by diffing responses, it returns byte-identical
  content to the homepage regardless of query. The per-fighter "related news" module
  on fighter pages is also generic/mislabeled, not real fighter tagging. Working
  approach instead: pull a pool of recent articles from `/tag/ufc` (paginated), match
  against each fight by checking both fighters' last names appear in the article title.
- [x] **MMA Junkie** — done, `scrape_mmajunkie.py`, 159/159 fights processed, 95 fights
  matched with real articles (268 total) — the richest of the three analyst sources.
  Its `/search/?q=` endpoint genuinely works, but **both search results and article
  bodies render inside Shadow DOM** — invisible to plain HTML parsing, and invisible
  to Playwright's `page.content()` too (`outerHTML` doesn't serialize shadow roots).
  Needed a JS shadow-root walker (`querySelectorAll` + recurse into `el.shadowRoot`)
  to find real content; body-copy classes are Gannett's own (`gnt_ar_hl`/`gnt_ar_by`/
  `gnt_ar_b`). Full-name combined search queries work fine here (unlike UFCStats).
- [x] **ESPN** — done, `scrape_espn.py`, 159/159 fights processed, 12 fights matched
  (smallest hit rate of the three — its fighter-specific "Latest News" list is short).
  Sits behind an AWS WAF JS challenge (same category of problem as UFCStats) →
  Playwright required for every page. Unlike UFCStats, ESPN's page never reaches
  `networkidle` (constant ad/analytics polling) — timed empirically and found real
  content is present ~500ms after `domcontentloaded`, so uses
  `wait_until="domcontentloaded"` + a 1.5s fixed settle wait, not networkidle.
- [ ] **X/Twitter** — **not functional, parked 2026-08-15.** Tried four
  approaches, all failed differently:
  1. `twikit` (mainstream, latest PyPI 2.3.3) — login fails with "Couldn't get
     KEY_BYTE indices". Confirmed via GitHub issue #408: X changed their
     `ondemand.s.js` webpack bundle around 2026-03-18, breaking twikit's
     client-transaction-id parsing for everyone. Not fixed upstream as of
     2026-08-15.
  2. `twifork` (github.com/PawiX25/twifork, MIT, drop-in replacement fork that
     specifically patches issue #408) — hit the **identical** error. Whatever
     changed on X's side has apparently moved again since twifork's patch.
  3. `twscrape` (different codebase entirely, needs `email_password` for IMAP
     verification-code retrieval — did NOT use the builder's real email
     password, tested with a placeholder since it's only used if X challenges
     with an email code) — blocked outright by **Cloudflare 403** at the login
     request, before even reaching X's own logic.
  4. Direct Playwright login (drive real Chromium to x.com/i/flow/login,
     matching the pattern already used for ESPN/MMA Junkie) — got further
     (found the real `input[name="username_or_email"]` field, submitted it)
     but X's own login system responded "We've temporarily limited your
     login. Please try again later." — likely triggered by the rapid
     succession of login attempts across approaches 1-4 against the same
     fresh account. **Do not retry login attempts back-to-back** — risks
     extending or worsening the restriction.
  Burner account + `.env` credentials are already in place (`X_USERNAME`,
  `X_EMAIL`, `X_PASSWORD`) for whenever this gets revisited. Next time: wait
  a while before retrying (hours-to-days, unknown exact duration), check
  whether twikit/twifork have caught up to X's latest change before
  re-attempting, and go easy on login attempts (one at a time, spaced out).
- [ ] **Reddit** — code complete (`scrape_reddit.py`), blocked on Reddit API app
  creation. Uses PRAW (official API), searches `r/mma+ufc` by
  `"<fighter1 last> <fighter2 last>"` — full "First Last" queries don't work reliably
  (same lesson as UFCStats' search). Keeps top-level comments only
  (`replace_more(limit=0)`). Decision: store real Reddit usernames (public info,
  matches the "cited real posts" product vision); whether to *display* them is a
  separate, later frontend decision. **Currently stuck (2026-08-15):** creating the
  Reddit "script" app under the dedicated throwaway account (see gray-area decision
  above) hangs on Reddit's reCAPTCHA — fails silently across multiple browsers and an
  incognito window, which rules out a local extension/cookie problem. Leading theory:
  Reddit restricts API app creation for new/low-karma accounts (anti-abuse measure),
  and the throwaway account is triggering it. Next diagnostic step: try app creation
  on the builder's established main account to confirm; if that works, the throwaway
  account likely needs to age (some activity, a few days) before Reddit trusts it with
  API access. **Update:** ruled out — app creation also hung on the builder's
  established main account, so it isn't account-age/trust related. Leading theory now:
  a genuine Reddit-side reCAPTCHA issue, or a network-level block (ISP/router filtering
  Google's recaptcha domains) that persists across browsers/incognito. Parked for now;
  revisit later (try again after some time, try a different network). Moved on to X in
  the meantime.
- [ ] **X/Twitter** — last, blocked on the builder creating a dedicated burner X account
  (credentials go in `.env`). See `twikit` note in Architecture decisions above — do a
  live install+login spike before building the rest, since this library's freshness
  isn't fully certain and the unofficial-X-scraping landscape shifts often.

### Scraper conventions (established across fight_cards, ufcstats, rag_sources)
Keep new ingestion scripts consistent with this shape rather than inventing a new one:
- `collect_X()` — gather targets to scrape (often by reading fight_cards JSON)
- `scrape_X()` / `search_X()` — fetch + parse one item
- `slugify(name)` — filename-safe id; always run names through `_normalize()`
  (unicodedata NFKD + a manual letter map for ł/ø/ß/đ, which don't decompose via plain
  NFKD) before regex-stripping to `a-z0-9`, or accented names get silently mangled
- `main()` — creates `Path(__file__).resolve().parents[N] / "data" / "raw" / "<source>"`,
  loops, writes one `json.dumps(..., indent=2)` file per entity, prints
  `Saved X -> path` / `Skipping ... -- reason`, `time.sleep(1)` between requests
- Idempotent: `if out_path.exists(): continue` so reruns only fill gaps, never redo work
- requests+BeautifulSoup by default; only reach for Playwright when a site is actually
  **confirmed** (not assumed) to need JS execution — UFCStats and ESPN both sit behind
  real anti-bot JS challenges, Sherdog/MMA Junkie/UFC.com don't.
- Before writing selectors or a search/discovery strategy, fetch the real page (curl or
  a throwaway Playwright script) and inspect actual HTML/behavior. Assumed behavior
  (a site's search working, a class name meaning what it sounds like) has repeatedly not
  held up — e.g. Sherdog's `/search.php` silently returning unfiltered homepage content.

## Conventions / notes
- Repo name: AI_UFC_PREDICTION
- No production security requirements yet — this is a learning/portfolio project, but
  don't casually hardcode secrets; use .env files and explain why.
- When introducing a new AWS service or infra concept for the first time in a session,
  give a short explanation before or alongside the implementation.
- **Python env:** venv + pip + `requirements.txt` (builder's choice — simplest, least
  new tooling given AWS/RAG are already new this project). `./venv/bin/python` /
  `./venv/bin/pip`, not global Python.
- **Secrets:** live in `.env` (gitignored), with a checked-in `.env.example`
  documenting required keys as blank placeholders. Current keys: `REDDIT_CLIENT_ID`,
  `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`; X/twikit credentials to be added the
  same way when that scraper is built.
- **Scraped data:** lives under `data/raw/<source>/`, gitignored (regenerable, not
  source code — same reasoning as not committing build artifacts).