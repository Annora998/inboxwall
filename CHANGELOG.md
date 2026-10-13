# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-10-13

### Added
- Composite database key (account, folder, uid_validity, uid) to prevent Message-ID overwrite attacks
- Vault deduplication on email reprocessing
- Full text preservation in vault (no truncation)
- API security headers (CSP, X-Frame-Options, nosniff)
- Host header validation to prevent DNS rebinding
- Constant-time token comparison
- pytest-based benchmark with structured corpus
- GitHub Actions CI workflow

### Changed
- Database schema: Added composite unique constraint
- API: Changed from message_id to internal id for lookups
- Sanitizer: Only clear "hard" hides or leaf nodes (preserves wrapper inheritance)
- White-on-white detection: Only flags when background is explicitly light
- Joiner policy: Preserve ZWJ/ZWNJ in non-Latin scripts, strip only in Latin words
- Verdict logic: Weight-0 findings now correctly result in CLEAN verdict

### Fixed
- font-size:0 wrapper no longer wipes visible child content
- White text on dark/unknown backgrounds no longer falsely flagged
- Malayalam, Arabic, Hindi, emoji joiners no longer corrupted
- Vault no longer creates duplicate rows on reprocessing
- Database connections properly closed (no handle leaks)
- Non-rendering tags (<title>, <textarea>, etc.) no longer leak text
- css_inline remote stylesheet fetching disabled

### Security
- Locked mail (LOCKED_AWAY verdict) never shown to AI via API or MCP
- Subject and sender metadata sanitized before storage
- Fail-closed logic on all scanner errors
- ReDoS prevention via bounded substring checks

## [2.0.0] - 2026-10-12

### Added
- Dual-database architecture (safe + vault)
- MCP (Model Context Protocol) server for AI integration
- Threat Wall dashboard with split-screen view
- Bearer token authentication for API
- Read-only database access for AI tools
- CSS class inlining via css-inline library

### Security
- Removed wildcard CORS
- Removed innerHTML usage in dashboard (XSS prevention)
- Added size limits (5MB max HTML)
- Added length truncation (2000 chars for classification)