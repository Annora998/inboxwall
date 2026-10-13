"""InBox Wall v2 - Professional Benchmark with pytest."""
import json
import pytest
from pathlib import Path
from inboxwall.engine.pipeline import WallPipeline

@pytest.fixture
def pipeline():
    return WallPipeline()

@pytest.fixture
def attack_corpus():
    corpus_path = Path(__file__).parent.parent / "corpus" / "attacks" / "sample_attacks.json"
    with open(corpus_path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def normal_corpus():
    corpus_path = Path(__file__).parent.parent / "corpus" / "normal" / "sample_normal.json"
    with open(corpus_path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_attacks_are_caught(pipeline, attack_corpus):
    """Verify that all attack emails are detected and blocked."""
    for attack in attack_corpus:
        result = pipeline.process(attack["html"])
        
        # Check verdict
        assert result["verdict"].value in ["CLEANED", "LOCKED_AWAY"], \
            f"Attack {attack['id']} not caught: {attack['description']}"
        
        # Check that poison did not leak
        if not attack["expected_leak"]:
            # Extract unique markers from the attack HTML
            # For now, we check that the verdict is not CLEAN
            assert result["verdict"].value != "CLEAN", \
                f"Attack {attack['id']} leaked: {attack['description']}"

def test_normal_emails_pass(pipeline, normal_corpus):
    """Verify that normal emails are not falsely flagged."""
    for normal in normal_corpus:
        result = pipeline.process(normal["html"])
        
        # Check verdict
        assert result["verdict"].value == normal["expected_verdict"], \
            f"Normal email {normal['id']} incorrectly flagged as {result['verdict'].value}: {normal['description']}"
        
        # Check that important text is preserved
        for preserved_text in normal.get("should_preserve", []):
            assert preserved_text in result["clean_text"], \
                f"Normal email {normal['id']} lost text '{preserved_text}': {normal['description']}"

def test_benchmark_metrics(pipeline, attack_corpus, normal_corpus):
    """Calculate and display benchmark metrics."""
    attacks_caught = 0
    attacks_total = len(attack_corpus)
    
    for attack in attack_corpus:
        result = pipeline.process(attack["html"])
        if result["verdict"].value in ["CLEANED", "LOCKED_AWAY"]:
            attacks_caught += 1
    
    normal_passed = 0
    normal_total = len(normal_corpus)
    
    for normal in normal_corpus:
        result = pipeline.process(normal["html"])
        if result["verdict"].value == normal["expected_verdict"]:
            normal_passed += 1
    
    attack_rate = (attacks_caught / attacks_total * 100) if attacks_total > 0 else 0
    false_alarm_rate = ((normal_total - normal_passed) / normal_total * 100) if normal_total > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"BENCHMARK METRICS")
    print(f"{'='*60}")
    print(f"Attack Detection Rate: {attacks_caught}/{attacks_total} ({attack_rate:.1f}%)")
    print(f"False Alarm Rate: {normal_total - normal_passed}/{normal_total} ({false_alarm_rate:.1f}%)")
    print(f"{'='*60}\n")
    
    # Assert minimum thresholds (adjust based on your corpus)
    assert attack_rate >= 80.0, f"Attack detection rate too low: {attack_rate:.1f}%"
    assert false_alarm_rate <= 20.0, f"False alarm rate too high: {false_alarm_rate:.1f}%"