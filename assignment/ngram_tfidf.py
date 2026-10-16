"""AcehX assignment: extract 10k sentences, unigram/trigram LM, perplexity, TF-IDF.
Pure Python (no external deps)."""
import csv, math, random, re
from collections import Counter

N_SENT, SEED, K = 10000, 42, 0.1
random.seed(SEED)

# 1. Extract 10,000 sentences (clean, non-empty, 3+ tokens, de-duplicated)
def tok(s): return re.findall(r"[a-zA-Z0-9']+", s.lower())
seen, sents = set(), []
for line in open("AcehX_Corpus.txt", encoding="utf-8"):
    t = tok(line)
    key = " ".join(t)
    if len(t) >= 3 and key not in seen:
        seen.add(key); sents.append(t)
random.shuffle(sents)
sents = sents[:N_SENT]
with open("sentences_10k.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(" ".join(s) for s in sents))
split = int(0.9 * len(sents))
train, test = sents[:split], sents[split:]
print(f"sentences: {len(sents)}  train: {len(train)}  test: {len(test)}")

# 2. Unigrams and trigrams (with <s> <s> ... </s> padding for trigrams)
uni = Counter(w for s in train for w in s)
uni["</s>"] = len(train)
tri, bi = Counter(), Counter()
for s in train:
    p = ["<s>", "<s>"] + s + ["</s>"]
    for i in range(2, len(p)):
        tri[tuple(p[i-2:i+1])] += 1
        bi[tuple(p[i-2:i])] += 1
V = len(uni) + 1  # +1 for <unk>
total = sum(uni.values())
print(f"vocab: {len(uni)}  unique trigrams: {len(tri)}")

def p_uni(w): return (uni.get(w, 0) + K) / (total + K * V)
def p_tri(a, b, w): return (tri.get((a, b, w), 0) + K) / (bi.get((a, b), 0) + K * V)

def perplexity(prob_fn, data):
    ll, n = 0.0, 0
    for s in data:
        p = ["<s>", "<s>"] + s + ["</s>"]
        for i in range(2, len(p)):
            ll += math.log(prob_fn(p, i)); n += 1
    return math.exp(-ll / n)

# interpolated trigram (0.6 tri + 0.3 bi + 0.1 uni) to handle sparsity
b1, b0 = Counter(), Counter()
for s_ in train:
    p = ["<s>"] + s_ + ["</s>"]
    for i in range(1, len(p)):
        b1[(p[i-1], p[i])] += 1; b0[p[i-1]] += 1
def p_interp(a, b, w):
    pt = tri.get((a, b, w), 0) / bi[(a, b)] if bi.get((a, b)) else 0
    pb = b1.get((b, w), 0) / b0[b] if b0.get(b) else 0
    return 0.6 * pt + 0.3 * pb + 0.1 * p_uni(w)

# 3. Perplexity (unigram/trigram add-k k=0.1; interpolated trigram)
pp_uni = perplexity(lambda p, i: p_uni(p[i]), test)
pp_tri = perplexity(lambda p, i: p_tri(p[i-2], p[i-1], p[i]), test)
pp_int = perplexity(lambda p, i: p_interp(p[i-2], p[i-1], p[i]), test)
print(f"Perplexity unigram: {pp_uni:.2f}\nPerplexity trigram (add-k): {pp_tri:.2f}\nPerplexity trigram (interpolated): {pp_int:.2f}")

for name, c in (("unigrams", uni), ("trigrams", tri)):
    with open(f"top_{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["ngram", "count"])
        for g, n in c.most_common(50):
            w.writerow([g if isinstance(g, str) else " ".join(g), n])

# 4. TF-IDF (each sentence = a document; tf = count/len, idf = ln(N/df)+1... smooth)
N = len(sents)
df = Counter(w for s in sents for w in set(s))
idf = {w: math.log((1 + N) / (1 + d)) + 1 for w, d in df.items()}
best = {}  # word -> max tf-idf over docs
for s in sents:
    c = Counter(s)
    for w, n in c.items():
        v = (n / len(s)) * idf[w]
        if v > best.get(w, 0): best[w] = v
with open("tfidf_top_terms.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["term", "df", "idf", "max_tfidf"])
    for t, v in sorted(best.items(), key=lambda x: -x[1])[:100]:
        w.writerow([t, df[t], round(idf[t], 4), round(v, 4)])
with open("tfidf_first_sentences.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["sentence_id", "sentence", "top_terms(tfidf)"])
    for i, s in enumerate(sents[:20]):
        c = Counter(s)
        top = sorted(((x, n / len(s) * idf[x]) for x, n in c.items()), key=lambda x: -x[1])[:5]
        w.writerow([i, " ".join(s), "; ".join(f"{x}:{v:.3f}" for x, v in top)])
print("Top TF-IDF terms:", [t for t, _ in sorted(best.items(), key=lambda x: -x[1])[:10]])
