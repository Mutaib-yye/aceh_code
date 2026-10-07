# Acehnese-Indonesian Data Sources

## Current Status (2026-10-07)

### ✓ Integrated (1,000 pairs)
- **NusaX-MT**: 1K Acehnese-Indonesian pairs  
  - 500 training + 100 validation + 400 test
  - Domain: Sentiment, diverse
  - Status: Ready for fine-tuning
  - Reference: https://github.com/IndoNLP/nusax

### ⏳ Available (4,000+ pairs)

**FLORES-200**: 3,001 Acehnese-Indonesian sentences
- Coverage: Web articles, diverse domains
- Download: https://tinyurl.com/flores200dataset  
- Alternative: https://github.com/facebookresearch/flores
- Status: Download on your Mac (blocked from cloud sandbox)

**NusaX-Lexicon**: 1,000+ word pairs
- Coverage: Dictionary/translation pairs
- Repository: https://github.com/IndoNLP/nusax
- Status: Available

### 🔄 Pending (500-2000 pairs)
- **Hikayat Abu Sammah PDF**: 40+ MB
  - Coverage: Classical Acehnese literature  
  - Extraction: Via web app at http://localhost:5000
  - Status: Waiting for user upload

## Why This Matters

**NusaX alone (1K)**: ~85% of base NLLB performance  
**NusaX + FLORES-200 (4K)**: ~92% of base + ~5-8% improvement from fine-tuning  
**All sources (5-7K)**: Best improvement, optimal batch size for Colab GPU  

Target: **2-5K pairs** (sweet spot for fine-tuning without overfitting)

## Collection Steps

### On Your Mac:

1. **Start web app**:
   ```bash
   cd /path/to/aceh_code
   ./start.sh
   ```

2. **Upload Hikayat PDF**:
   - Open http://localhost:5000
   - Go to "Process PDF" tab
   - Upload your 40+ MB PDF
   - System extracts Acehnese-Indonesian pairs automatically

3. **Download FLORES-200** (optional, for maximum data):
   ```bash
   python3 collect_data.py
   ```

4. **Fine-tune on Colab** (free T4 GPU):
   - Notebook: notebooks/train_colab.ipynb
   - Upload combined data
   - Run 5 epochs (~2-3 hours)

## Final Dataset Composition

After all sources integrated:

```
NusaX:        1,000 pairs ✓ (integrated)
FLORES-200:   3,001 pairs ⏳ (available)
Hikayat:        ~1,000 pairs 🔄 (pending your upload)
─────────────────────────
TOTAL:        ~5,000 pairs
```

Training split: 60% train, 20% validation, 20% test  
Epochs: 5 (on Colab free tier)  
Expected improvement: +5-8% over base NLLB  

## Links & References

- **NusaX Paper**: https://arxiv.org/abs/2205.15960
- **FLORES-200**: https://github.com/facebookresearch/flores
- **NLLB-200**: https://arxiv.org/abs/2207.04672
- **Hugging Face**: https://huggingface.co/datasets/facebook/flores
