#!/usr/bin/env python3
"""
Process ALL raw Acehnese-Indonesian data files.

Handles:
- RAR archives (Syair dan Lagu)
- TAR archives (FLORES-200)
- ZIP archives (translation project, corpus)
- PDFs (Hikayat with OCR)
- CSV/JSON files (lyrics corpus)

Outputs: cleaned_data/combined_pairs.jsonl
"""

import os
import json
import csv
import tarfile
import zipfile
from pathlib import Path
from collections import defaultdict

# Try to import extraction tools
try:
    import pymupdf  # For PDF processing
except ImportError:
    print("⚠️  pymupdf not installed. PDF processing will be limited.")

HOME = Path.home()
DOWNLOADS = HOME / "Downloads"
OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

all_pairs = []
stats = defaultdict(int)

def log(msg):
    print(f"{'✓' if '✓' in msg else '→'} {msg}")

# ============================================================================
# 1. FLORES-200 DATASET (TAR)
# ============================================================================
def process_flores200():
    """Extract and parse FLORES-200 parallel sentences."""
    log("Processing FLORES-200...")

    tar_file = DOWNLOADS / "flores200_dataset.tar"
    if not tar_file.exists():
        log("  ⚠️  flores200_dataset.tar not found")
        return

    extract_dir = Path("/tmp/flores200_extracted")
    extract_dir.mkdir(exist_ok=True)

    try:
        with tarfile.open(tar_file) as tar:
            tar.extractall(extract_dir)

        # Look for ace_Latn and ind files
        flores_pairs = 0
        for split in ["dev", "devtest"]:
            # Find ace_Latn and ind files
            ace_file = None
            ind_file = None

            for f in extract_dir.rglob(f"*.{split}.ace_Latn"):
                ace_file = f
            for f in extract_dir.rglob(f"*.{split}.ind"):
                ind_file = f

            if ace_file and ind_file:
                with open(ace_file, encoding='utf-8') as f_ace, \
                     open(ind_file, encoding='utf-8') as f_ind:
                    for ace_line, ind_line in zip(f_ace, f_ind):
                        pair = {
                            "acehnese": ace_line.strip(),
                            "indonesian": ind_line.strip(),
                            "source": "FLORES-200",
                            "split": split
                        }
                        if pair["acehnese"] and pair["indonesian"]:
                            all_pairs.append(pair)
                            flores_pairs += 1

        log(f"  ✓ FLORES-200: {flores_pairs} pairs")
        stats["flores200"] = flores_pairs
    except Exception as e:
        log(f"  ✗ Error processing FLORES-200: {e}")

# ============================================================================
# 2. HIKAYAT PDFs (with OCR)
# ============================================================================
def process_hikayat_pdfs():
    """Extract text from Hikayat PDFs."""
    log("Processing Hikayat PDFs...")

    pdf_files = list(DOWNLOADS.glob("HIKAYAT*.pdf"))
    if not pdf_files:
        log("  ⚠️  No Hikayat PDFs found")
        return

    hikayat_pairs = 0
    for pdf_file in pdf_files:
        try:
            import pymupdf
            doc = pymupdf.open(pdf_file)
            text = ""
            for page in doc:
                text += page.get_text()

            # Simple sentence splitting (can be improved)
            sentences = [s.strip() for s in text.split('\n') if s.strip()]

            # Try to identify ace/ind pairs (this is heuristic)
            # Hikayat usually has Acehnese on left, Indonesian on right
            # For now, just add as raw text
            for sent in sentences[:100]:  # Sample first 100 lines
                if len(sent) > 10:
                    pair = {
                        "text": sent,
                        "source": pdf_file.name,
                        "type": "raw_hikayat"
                    }
                    all_pairs.append(pair)
                    hikayat_pairs += 1

            log(f"  ✓ {pdf_file.name}: {hikayat_pairs} lines")
            stats[f"hikayat_{pdf_file.name}"] = hikayat_pairs
        except Exception as e:
            log(f"  ✗ Error processing {pdf_file.name}: {e}")

# ============================================================================
# 3. LYRICS CORPUS (CSV + JSON)
# ============================================================================
def process_lyrics_corpus():
    """Parse Acehnese lyrics corpus."""
    log("Processing Acehnese lyrics corpus...")

    lyrics_pairs = 0

    # CSV file
    csv_file = DOWNLOADS / "aceh_lyrics_corpus.csv"
    if csv_file.exists():
        try:
            with open(csv_file, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('acehnese') and row.get('indonesian'):
                        pair = {
                            "acehnese": row['acehnese'].strip(),
                            "indonesian": row['indonesian'].strip(),
                            "source": "lyrics_corpus",
                            "type": "lyrics"
                        }
                        all_pairs.append(pair)
                        lyrics_pairs += 1
            log(f"  ✓ CSV: {lyrics_pairs} pairs")
        except Exception as e:
            log(f"  ✗ Error reading CSV: {e}")

    # JSON file
    json_file = DOWNLOADS / "aceh_lyrics_corpus.json"
    if json_file.exists():
        try:
            with open(json_file, encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            pair = {
                                "acehnese": item.get('acehnese', '').strip(),
                                "indonesian": item.get('indonesian', '').strip(),
                                "source": "lyrics_corpus",
                                "type": "lyrics"
                            }
                            if pair["acehnese"] and pair["indonesian"]:
                                all_pairs.append(pair)
                                lyrics_pairs += 1
            log(f"  ✓ JSON: {lyrics_pairs} pairs")
        except Exception as e:
            log(f"  ✗ Error reading JSON: {e}")

    stats["lyrics_corpus"] = lyrics_pairs

# ============================================================================
# 4. TRANSLATION PROJECT (ZIP)
# ============================================================================
def process_translation_project():
    """Extract Acehnese-Indonesian pairs from translation project ZIP."""
    log("Processing translation project ZIP...")

    zip_file = DOWNLOADS / "aceh_translation_project.zip"
    if not zip_file.exists():
        log("  ⚠️  aceh_translation_project.zip not found")
        return

    extract_dir = Path("/tmp/translation_project")
    extract_dir.mkdir(exist_ok=True)

    try:
        with zipfile.ZipFile(zip_file) as z:
            z.extractall(extract_dir)

        # Look for JSON/CSV files with translations
        project_pairs = 0
        for file in extract_dir.rglob("*.json"):
            try:
                with open(file, encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'acehnese' in item and 'indonesian' in item:
                                pair = {
                                    "acehnese": item['acehnese'].strip(),
                                    "indonesian": item['indonesian'].strip(),
                                    "source": "translation_project",
                                    "type": "project"
                                }
                                if pair["acehnese"] and pair["indonesian"]:
                                    all_pairs.append(pair)
                                    project_pairs += 1
            except:
                pass

        for file in extract_dir.rglob("*.csv"):
            try:
                with open(file, encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('acehnese') and row.get('indonesian'):
                            pair = {
                                "acehnese": row['acehnese'].strip(),
                                "indonesian": row['indonesian'].strip(),
                                "source": "translation_project",
                                "type": "project"
                            }
                            all_pairs.append(pair)
                            project_pairs += 1
            except:
                pass

        log(f"  ✓ Translation project: {project_pairs} pairs")
        stats["translation_project"] = project_pairs
    except Exception as e:
        log(f"  ✗ Error processing translation project: {e}")

# ============================================================================
# 5. CORPUS DATA (ZIP)
# ============================================================================
def process_corpus_archives():
    """Extract from corpus-acehx ZIP files."""
    log("Processing corpus archives...")

    corpus_pairs = 0
    for zip_file in DOWNLOADS.glob("corpus-acehx*.zip"):
        try:
            extract_dir = Path("/tmp/corpus_extracted")
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(zip_file) as z:
                z.extractall(extract_dir)

            # Look for text files with Acehnese content
            for file in extract_dir.rglob("*.txt"):
                try:
                    with open(file, encoding='utf-8') as f:
                        content = f.read()
                        # Split into sentences
                        for line in content.split('\n'):
                            if line.strip() and len(line) > 5:
                                pair = {
                                    "text": line.strip(),
                                    "source": "corpus_acehx",
                                    "type": "corpus"
                                }
                                all_pairs.append(pair)
                                corpus_pairs += 1
                except:
                    pass

            log(f"  ✓ {zip_file.name}: {corpus_pairs} lines")
        except Exception as e:
            log(f"  ✗ Error processing {zip_file.name}: {e}")

    stats["corpus_acehx"] = corpus_pairs

# ============================================================================
# 6. DATA SYAIR DAN LAGU (RAR)
# ============================================================================
def process_syair_dan_lagu():
    """Extract from Syair dan Lagu RAR archive."""
    log("Processing Data Syair dan Lagu RAR...")

    rar_file = DOWNLOADS / "Data Syair dan Lagu.rar"
    if not rar_file.exists():
        log("  ⚠️  Data Syair dan Lagu.rar not found")
        log("  Install unar or unrar: brew install unar")
        return

    extract_dir = Path("/tmp/syair_extracted")
    extract_dir.mkdir(exist_ok=True)

    try:
        import subprocess
        result = subprocess.run(
            ["unar", "-o", str(extract_dir), str(rar_file)],
            capture_output=True
        )

        if result.returncode != 0:
            log(f"  ⚠️  Could not extract RAR. Install: brew install unar")
            return

        syair_pairs = 0
        for file in extract_dir.rglob("*.txt"):
            try:
                with open(file, encoding='utf-8') as f:
                    for line in f:
                        if line.strip() and len(line) > 5:
                            pair = {
                                "text": line.strip(),
                                "source": "syair_dan_lagu",
                                "type": "poetry"
                            }
                            all_pairs.append(pair)
                            syair_pairs += 1
            except:
                pass

        log(f"  ✓ Syair dan Lagu: {syair_pairs} lines")
        stats["syair_dan_lagu"] = syair_pairs
    except Exception as e:
        log(f"  ✗ Error processing Syair dan Lagu: {e}")

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("\n" + "="*70)
    print("ACEHNESE-INDONESIAN DATA PROCESSING")
    print("="*70 + "\n")

    # Process all sources
    process_flores200()
    process_lyrics_corpus()
    process_translation_project()
    process_corpus_archives()
    process_hikayat_pdfs()
    process_syair_dan_lagu()

    # Save results
    output_file = OUTPUT_DIR / "combined_pairs.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"\nTotal pairs extracted: {len(all_pairs)}")
    print("\nBy source:")
    for source, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"  • {source}: {count}")

    print(f"\nOutput: {output_file}")
    print("\n✓ Ready for fine-tuning on Colab!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
