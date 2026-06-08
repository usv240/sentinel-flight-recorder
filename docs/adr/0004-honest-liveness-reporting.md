# ADR-0004: Every integration has to say, out loud, whether it's actually live

**Status:** Accepted
**Date:** 2026-06-03

---

Demo systems have a familiar failure mode: they look identical whether they're running on real data or canned fixtures, and the gap only becomes visible when someone who needed the real thing finds out the hard way. SENTINEL touches six external systems (Gemini, Fivetran, BigQuery, MongoDB, Slack, and Google's ADK), and each one can be sitting anywhere between "fully configured and working" and "not set up at all" at any given moment.

The tempting shortcut is to make the fallback data convincing enough that nobody asks. We didn't want to build that habit into the codebase, because the gap between "looks live" and "is live" is exactly where trust quietly erodes, whether that's in a demo, a pilot, or production. Once one screen shows fake data without saying so, every other screen becomes suspect too.

So `GET /api/health/integrations` makes SENTINEL say, plainly, what's actually happening. Each integration reports one of five honest states: `live` (configured, and a real call just succeeded), `configured` (credentials present but not verified this request), `demo` (no credentials, so here is clearly labelled sample data instead), `unavailable` (the library isn't even installed), or `error` (configured, but the last real call failed, with the reason why). Every Fivetran tool result carries a `_source: mcp|rest|demo` tag and a `_live: true|false` flag. Every metrics snapshot names the BigQuery table it came from, or admits that it didn't come from one.

The result is a system that tells on itself. Set up half your credentials, and SENTINEL won't pretend to be fully wired. It'll tell you exactly which half is missing and what to add to close the gap. That's a small amount of extra plumbing in exchange for never having to wonder whether what's on screen is real.
