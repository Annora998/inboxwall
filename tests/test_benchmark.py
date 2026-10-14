"""InBox Wall v2 - Leak-Based Benchmark with pytest."""
import json, pytest
from pathlib import Path
from inboxwall.engine.pipeline import WallPipeline

@pytest.fixture
def pipeline(): return WallPipeline()

@pytest.fixture
def attack_corpus():
    attacks = []
    for p in Path("corpus/attacks").glob("*.json"):
        with open(p, "r", encoding="utf-8") as f:
            attacks.extend(json.load(f))
    return attacks

@pytest.fixture
def normal_corpus():
    normals = []
    for p in Path("corpus/normal").glob("*.json"):
        with open(p, "r", encoding="utf-8") as f:
            normals.extend(json.load(f))
    return normals

def test_leak_based_metrics(pipeline, attack_corpus, normal_corpus):
    """
    Measures by leak, not by label. 
    'Caught' means the unique payload token is ABSENT from the AI's clean text.
    """
    leaks = 0
    for a in attack_corpus:
        result = pipeline.process(a["html"])
        token = a.get("payload_token")
        if token and token in result["clean_text"]:
            leaks += 1
            
    leak_rate = (leaks / len(attack_corpus) * 100) if attack_corpus else 0
    
    false_removals = 0
    false_locks = 0
    for n in normal_corpus:
        result = pipeline.process(n["html"])
        if result["verdict"].value == "LOCKED_AWAY":
            false_locks += 1
        for preserve in n.get("should_preserve", []):
            if preserve not in result["clean_text"]:
                false_removals += 1
                break
                
    total_normal = len(normal_corpus)
    false_removal_rate = (false_removals / total_normal * 100) if total_normal else 0
    false_lock_rate = (false_locks / total_normal * 100) if total_normal else 0
    
    print(f"\n{'='*60}")
    print(f"LEAK-BASED BENCHMARK METRICS ({len(attack_corpus)} attacks, {total_normal} normal)")
    print(f"{'='*60}")
    print(f"Leak Rate (payload token in clean text): {leaks}/{len(attack_corpus)} ({leak_rate:.2f}%)")
    print(f"False Removal Rate (normal text lost): {false_removals}/{total_normal} ({false_removal_rate:.2f}%)")
    print(f"False Lock Rate (normal mail locked): {false_locks}/{total_normal} ({false_lock_rate:.2f}%)")
    print(f"{'='*60}\n")
    
    # Strict thresholds for a production security tool
    assert leak_rate == 0.0, f"Leak rate must be 0%, got {leak_rate:.2f}%"
    assert false_lock_rate <= 5.0, f"False lock rate too high: {false_lock_rate:.2f}%"
    assert false_removal_rate <= 5.0, f"False removal rate too high: {false_removal_rate:.2f}%"