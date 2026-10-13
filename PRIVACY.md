# Privacy Policy

## Data Collection

**InBox Wall collects zero data.**

- No telemetry
- No analytics
- No cloud uploads
- No external API calls
- No user tracking

## Local-First Architecture

All processing happens on your machine:

- Email fetching uses your local IMAP credentials
- Sanitization runs locally via Python
- Storage uses local SQLite databases
- Dashboard runs on `127.0.0.1` only

## What Stays on Your Machine

- Raw email content (temporarily, during processing)
- Cleaned email text (in `safemail.db`)
- Blocked threats (in `vault.db`)
- API tokens (in memory, printed to console)

## What Leaves Your Machine

**Nothing.**

The only network activity is:
- Fetching emails from your IMAP server (encrypted via TLS)
- Loading the dashboard in your browser (localhost only)

## Your Responsibility

- Keep your API token secret
- Secure your local machine
- Back up your databases if needed
- Review the source code (it's open source)
