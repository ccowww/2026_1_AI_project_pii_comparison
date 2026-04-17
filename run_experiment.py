# run_experiment.py
"""
PII 탐지 비교 실험: Rule-based vs LLM-based
"""
import json, logging, sys
from datetime import datetime
from pathlib import Path

from src.pii_patterns import PII_PATTERNS, EXCLUDED_WORDS
from src.llm_based     import detect_llm
from src.evaluate      import evaluate_all

RESULTS_DIR = Path("results")
LOGS_DIR    = Path("logs")
RESULTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

N_SAMPLES = 100

# ── 로깅 설정 ────────────────────────────────────────
def setup_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path  = LOGS_DIR / f"experiment_{timestamp}.log"
    logger    = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s',
                            datefmt='%H:%M:%S')
    ch  = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    fh  = logging.FileHandler(log_path, encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(ch)
    logger.addHandler(fh)
    return log_path

# ── Rule-based 탐지 ──────────────────────────────────
def scan_text_for_pii(text: str) -> list:
    found = []
    for pii_type, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            found_text = match.group(0)
            if pii_type == "NAME_CONTEXT" and found_text in EXCLUDED_WORDS:
                continue
            found.append({
                "start": match.start(),
                "end":   match.end(),
                "type":  pii_type,
                "text":  found_text,
            })
    return found

# ── TAB 데이터 로드 ──────────────────────────────────
def load_tab(path: str, n: int) -> list:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    samples = []
    for doc in data[:n]:
        text   = doc["text"]
        labels = []
        seen   = set()  # 여러 어노테이터 중복 제거용
        # annotations는 dict {"annotator1": {...}, "annotator2": {...}}
        for annotator_data in doc.get("annotations", {}).values():
            for span in annotator_data.get("entity_mentions", []):
                key = (span["start_offset"], span["end_offset"])
                if key in seen:
                    continue
                seen.add(key)
                labels.append({
                    "start": span["start_offset"],
                    "end":   span["end_offset"],
                    "type":  span["entity_type"],  # span 레벨에 있음
                    "text":  span.get("span_text",
                                      text[span["start_offset"]:span["end_offset"]]),
                })
        samples.append({"text": text, "labels": labels})
    return samples

# ── 메인 ─────────────────────────────────────────────
def main():
    log_path = setup_logging()
    logging.info("=" * 60)
    logging.info("PII 탐지 비교 실험: Rule-based vs LLM-based")
    logging.info(f"샘플 수: {N_SAMPLES}")
    logging.info("=" * 60)

    # 1. 데이터 로드
    samples = load_tab("data/text-anonymization-benchmark/echr_train.json", n=N_SAMPLES)
    logging.info(f"데이터 로드 완료: {len(samples)}개 샘플")

    # 2. Rule-based
    logging.info("Rule-based 탐지 시작...")
    rule_preds = [scan_text_for_pii(s["text"]) for s in samples]
    logging.info("Rule-based 완료")

    # 3. LLM-based
    logging.info("LLM-based 탐지 시작... (시간 소요)")
    llm_preds = []
    for i, s in enumerate(samples):
        try:
            llm_preds.append(detect_llm(s["text"]))
        except Exception as e:
            logging.warning(f"  샘플 {i} LLM 오류 (빈 결과로 대체): {e}")
            llm_preds.append([])
        if (i + 1) % 5 == 0:
            logging.info(f"  {i+1}/{N_SAMPLES} 완료")
    logging.info("LLM-based 완료")

    # 4. 평가 및 저장
    evaluate_all(samples, rule_preds, llm_preds, RESULTS_DIR)
    logging.info(f"로그 파일: {log_path}")
    logging.info("실험 완료")

if __name__ == "__main__":
    main()