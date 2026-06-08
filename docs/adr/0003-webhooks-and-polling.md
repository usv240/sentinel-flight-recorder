# ADR-0003: Webhooks for speed, polling for certainty: run both, not one

**Status:** Accepted
**Date:** 2026-06-01

---

The autonomous monitor needs to know when fresh data lands in BigQuery so it can analyze it. There are two ways to find that out: ask Fivetran "did anything finish syncing?" on a schedule, or have Fivetran call SENTINEL the moment it happens.

Polling alone is simple and reliable, but slow. On a 30-minute schedule, a sync that finishes one minute after the last check won't get analyzed for nearly half an hour. For a system whose entire premise is "catch the warning signs early," that gap matters.

Webhooks alone are fast (Fivetran can notify SENTINEL within seconds of a sync completing), but they fail quietly. A webhook is a promise from an external system to call you back, and if that promise breaks (a misconfigured endpoint, a rotated secret, a network blip on Fivetran's side, a Cloud Run cold start that drops the first request), nothing tells you. The system just stops reacting to new data and looks perfectly healthy while doing it.

So SENTINEL does both. `POST /api/fivetran/webhook` receives Fivetran's sync events, each one verified with an HMAC-SHA256 signature so nobody can forge one, and fires an immediate analysis cycle the moment a `sync_end` event lands. Independently, the 30-minute scheduled loop keeps running no matter what. If the webhook fires, the analysis happens in seconds. If it doesn't, for any reason on either side, the poll catches it within half an hour, and nobody has to first notice that the webhook went quiet.

It's the same logic as a smoke detector with a battery backup. The mains-powered path responds faster, but you keep the battery because mains power fails in ways you won't notice until it's too late. Belt and suspenders is the right call when the cost of "we missed it" is a business decision nobody got to reconsider in time.
