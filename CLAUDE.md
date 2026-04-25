# deals-tracker

A lean deal-curation site for specialty coffee (and potentially other hard-to-find products). The goal is to be a trusted friend who already did the research: open it when you're running low, find the best current deal, see the unit-price math, buy in one click.

## Problem

The best coffee deals are hidden. Amazon has options but most are overpriced. Real value emerges from bulk buying (e.g., 10 boxes vs. 1 changes the unit price dramatically). Finding these deals takes time. This site does that research once and makes it available.

## Core experience

**Not a newsletter. Not alerts.** A simple reference page. The user opens it when running low on coffee, finds the best deal at a glance, and clicks buy. Every deal shows:
- Product name and why it's a good deal
- Unit price math (e.g., "$0.42/pod vs. $0.68 buying 1 box")
- Bulk context (minimum quantity for the deal to apply)
- Freshness indicator (when last checked, stale warning if price may have changed)
- One-click affiliate buy button (Amazon Associates)

## Constraints

- **Free hosting** — Netlify free tier or GitHub Pages. No paid servers.
- **Minimal maintenance** — owner spends minutes, not hours, per week.
- **Non-dev curator** — the product list must be editable via a simple YAML file without touching code.
- **No over-engineering** — personal project, not a startup. Build only what's needed.
- **Primary audience** — owner, family, small niche community.

## Tech stack

> **Pending user approval** — see proposal in initial conversation.

Proposed:
- **Site**: Astro (static site generator) — fast, file-based, zero runtime cost
- **Data**: `products.yaml` — human-editable, version-controlled
- **Hosting**: Netlify (free tier) — git-push deploys, no config
- **Price automation**: Python script + GitHub Actions (free) on daily cron
- **Affiliate**: Amazon Associates — tag injected from config, never hard-coded

## Data schema (`products.yaml`)

```yaml
- id: nespresso-vertuo-pods-colombia
  name: "Nespresso Vertuo Colombia Pods"
  asin: "B07NQKX67P"                     # Amazon ASIN (from URL: amazon.com/dp/<ASIN>)
  deal_price: 89.99                       # price you verified the deal at
  unit_price: 0.43                        # deal_price / unit_count (compute manually)
  unit_count: 210
  unit_label: "pod"
  typical_unit_price: 0.68               # single-box per-unit price (for comparison)
  bulk_note: "210-count bundle (3 boxes of 70)"
  why_good: "Best per-pod price on Vertuo format. Single box runs $0.68/pod..."
  last_checked: "2026-04-25T00:00:00Z"   # set by price-checker, don't edit
  stale: false                            # set by price-checker, don't edit
  current_price: null                     # set by price-checker, don't edit
```

The affiliate URL is generated automatically from the ASIN + `AMAZON_ASSOCIATES_TAG` env var.
Never store the Associates tag in `products.yaml`.

## Agents

### developer
Builds and maintains the site. Owns: Astro components, affiliate link wiring, deployment config, UI for freshness indicators. **Does not touch price-check scripts.**

### price-checker
Owns all price automation. Owns: `scripts/check_prices.py`, `.github/workflows/price-check.yml`. Reads and writes only `last_checked`, `stale`, and `current_price` in `products.yaml`. **Does not touch site components.**

### You (the owner)
Product strategist and deal curator. You decide what products to add, what counts as a good deal, and what to do when the price-checker flags something stale. Edit `products.yaml` directly.

## Collaboration model

1. Owner edits `products.yaml` to add/remove/update deals
2. Git push triggers Netlify deploy automatically
3. GitHub Actions runs price-checker daily; if a deal goes stale it commits a flag and (optionally) opens a GitHub issue
4. Owner reviews flagged deals and either updates the price or removes the product
5. Developer agent is invoked for site changes; price-checker agent for automation changes

## Environment variables / secrets

| Name | Where | Purpose |
|------|--------|---------|
| `AMAZON_ASSOCIATES_TAG` | Netlify env / GH secret | Affiliate tag appended to all buy links |
| `AMAZON_ACCESS_KEY` | GH secret | PA API (optional, improves price checking) |
| `AMAZON_SECRET_KEY` | GH secret | PA API (optional) |
| `AMAZON_PARTNER_TAG` | GH secret | PA API partner tag |

## What this is NOT

- Not a price-alert service
- Not a newsletter
- Not a marketplace
- Not a startup — do not add features speculatively
