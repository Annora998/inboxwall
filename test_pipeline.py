import sys
import os

sys.path.insert(0, os.getcwd())

from inboxwall.engine.pipeline import WallPipeline

print("=== InBox Wall: Full Pipeline Test ===")
print("Loading sample attack email...")

# Load the attack email we made in Step 5
with open("sample_attack.html", "r", encoding="utf-8") as f:
    html = f.read()

print("Running the full Wall Pipeline...\n")

pipeline = WallPipeline()
result = pipeline.process(html)

print(f"🛡️ FINAL VERDICT: {result['verdict']}")
print(f"🚨 Total Threats Caught: {result['threat_count']}")
print("\nDetailed Report:")
for finding in result['findings']:
    print(f" - [{finding['type'].upper()}] ", end="")
    if finding['type'] == 'hidden_style':
        print(f"Hidden command: '{finding['hidden_text'][:40]}...'")
    elif finding['type'] == 'dangerous_phrase':
        print(f"Phrase caught: '{finding['matched_text']}'")