import sys
import os

# Tell Python where our project folders are
sys.path.insert(0, os.getcwd())

from inboxwall.engine.cheap_cut.hidden_style_finder import HiddenStyleFinder

print("=== InBox Wall Test ===")
print("Loading the sample attack email...")

# Read the fake email we made in Step 5
with open("sample_attack.html", "r", encoding="utf-8") as f:
    html = f.read()

print("Scanning with the Wall (HiddenStyleFinder)...\n")
finder = HiddenStyleFinder()
findings = finder.scan(html)

if findings:
    print(f"🚨 ALERT: Found {len(findings)} hidden threat(s)!")
    for i, f in enumerate(findings, 1):
        print(f"--- Threat {i} ---")
        print(f"Hidden Command: {f['hidden_text']}")
else:
    print("No threats found.")