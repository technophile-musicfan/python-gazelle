# python-gazelle — Product Vision

**Date:** 2026-05-30
**Author:** HOZHENWAI

## What Are We Building?

`python-gazelle` is a Python client library for interacting with Gazelle-based music trackers. It provides a comprehensive, typed API wrapper and a set of automation utilities targeting Orpheus and Redacted as primary test targets.

## Who Is It For?

Developers and power users who want to automate workflows against Gazelle trackers — monitoring their uploads, cross-seeding between trackers, and uploading releases across platforms without manual effort.

## What Does "Done" Look Like?

A library that:
1. Covers the full Gazelle API surface with typed response models
2. Works reliably against both Orpheus and Redacted
3. Lets a user know when one of their uploads gets deleted or trumped so they can remove it from their torrent client
4. Enables cross-seeding between trackers (API metadata match + local file verification)
5. Enables cross-uploading a release from one tracker to another with correct metadata mapping

## Constraints

- Library only — no CLI or daemon; users wire up their own scripts and automation
- Python 3.11+
- Must handle tracker-specific API quirks between Orpheus and Redacted
