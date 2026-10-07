#!/usr/bin/env python3
"""
Integrate all available Acehnese-Indonesian data sources.

Sources to integrate:
1. NusaX-MT (1K pairs) - DONE ✓
2. FLORES-200 (3K sentences, ace_Latn) - Available from GitHub/HuggingFace
3. NusaX-Lexicon (1K words) - Available from IndoNLP
4. Hikayat Abu Sammah PDF (user provided) - Pending
5. Bible translations (150K+ phrases) - Available via research papers
6. OPUS corpus - NLLB multilingual corpus
"""

import os
import json
from pathlib import Path
from acehid.common import read_jsonl, write_jsonl

def integrate_sources():
    # Load NusaX (already done)
    nusax_train = json.load(open('data/final/nusax/train.json'))
    nusax_val = json.load(open('data/final/nusax/validation.json'))
    nusax_test = json.load(open('data/final/nusax/test.json'))
    
    print(f"✓ NusaX: {len(nusax_train)} train + {len(nusax_val)} val + {len(nusax_test)} test")
    
    all_pairs = nusax_train + nusax_val + nusax_test
    
    # TODO: Load FLORES-200 once downloaded
    # TODO: Load NusaX-Lexicon once available
    # TODO: Load Hikayat PDF pairs once extracted
    
    print(f"\nTotal pairs collected so far: {len(all_pairs)}")
    print(f"Target: ~2-5K pairs for optimal fine-tuning")
    print(f"Coverage: {(len(all_pairs) / 5000 * 100):.1f}% of target")
    
    return all_pairs

if __name__ == '__main__':
    pairs = integrate_sources()
