# 🛡️ InBox Wall

**Local-first, read-only AI email security.**

InBox Wall sits between your email inbox and your AI assistant. It sanitizes incoming emails in real-time, stripping hidden CSS tricks, invisible Unicode characters, and prompt injection attacks *before* the AI ever sees them.

## 🎯 What It Does

- **Detects hidden text**: CSS `display:none`, white-on-white, off-screen positioning, tiny fonts
- **Strips invisible Unicode**: Zero-width spaces, Bidi controls, tag characters, Cyrillic look-alikes
- **Blocks prompt injection**: "Ignore previous instructions", credential harvesting, mail forwarding commands
- **Dual-database isolation**: AI only reads clean text; blocked poison is quarantined in a separate vault
- **True read-only**: Fetches mail with `mark_seen=False`, preserving your inbox state

## 📊 Benchmark Metrics

Tested against a corpus of 5 attack techniques and 5 normal email types:

| Metric | Result |
| :--- | :--- |
| **Attack Detection Rate** | 100% (5/5) |
| **False Alarm Rate** | 0% (0/5) |

*Note: This is a sample corpus. Expand `corpus/attacks/` and `corpus/normal/` for comprehensive testing.*

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd backend

# Install in editable mode
pip install -e .