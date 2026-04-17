# PII Detection Comparison: Rule-based vs LLM-based

ECHR(유럽인권재판소) 법률 문서에서 **Rule-based 정규표현식**과 **LLM(Large Language Model)** 두 가지 방법으로 개인식별정보(PII)를 탐지하고, 성능을 정량 비교하는 실험 프로젝트입니다.

## 프로젝트 구조

```
pii_comparison/
├── run_experiment.py          # 실험 메인 스크립트
├── src/
│   ├── pii_patterns.py        # Rule-based 정규표현식 패턴 정의
│   ├── llm_based.py           # LLM 기반 PII 탐지 (Ollama + llama3.2:3b)
│   └── evaluate.py            # Precision / Recall / F1 평가 및 CSV 저장
├── data/
│   └── text-anonymization-benchmark/
│       ├── echr_train.json    # TAB 데이터셋 (학습용, 1014문서)
│       ├── echr_dev.json      # TAB 데이터셋 (검증용)
│       └── echr_test.json     # TAB 데이터셋 (테스트용)
├── results/                   # 실험 결과 CSV 자동 저장
├── logs/                      # 실험 로그 자동 저장
└── README.md
```

## 데이터셋

[Text Anonymization Benchmark (TAB)](https://github.com/NorskRegnesentral/text-anonymization-benchmark) 데이터셋을 사용합니다.

- **출처**: 유럽인권재판소(ECHR) 판례 문서
- **포맷**: JSON (문서별 다수 어노테이터의 entity mention 라벨 포함)
- **엔티티 유형**: `PERSON`, `ORG`, `LOC`, `DATETIME`, `CODE`, `DEM`, `QUANTITY`, `MISC`

### 데이터 구조

```json
{
  "text": "PROCEDURE\nThe case originated in...",
  "annotations": {
    "annotator1": {
      "entity_mentions": [
        {
          "entity_type": "PERSON",
          "start_offset": 253,
          "end_offset": 271,
          "span_text": "Mr Henrik Hasslund"
        }
      ]
    }
  }
}
```

## 탐지 방법

### 1. Rule-based (정규표현식)

`src/pii_patterns.py`에 정의된 6가지 패턴으로 탐지합니다:

| 패턴 | 설명 | 예시 |
|------|------|------|
| `NAME_CONTEXT` | 호칭+이름, 이니셜 | Mr John Smith, E.K., G. Nicolaides |
| `DATE` | 날짜, 연도, 연대, 계절+연도 | 31 August 2006, 1990s, summer of 1993 |
| `SSN` | 미국 사회보장번호 | 123-45-6789 |
| `PHONE` | 미국 휴대폰 번호 | +1 (555) 123-4567 |
| `TEL` | 수신자부담 전화번호 | 800-123-4567 |
| `EMAIL` | 이메일 주소 | user@example.com |

### 2. LLM-based (Ollama + llama3.2:3b)

로컬 Ollama 서버에서 `llama3.2:3b` 모델을 사용하여 NER 스타일로 PII를 탐지합니다.

- ECHR 문서에 특화된 프롬프트 사용
- 긴 텍스트는 2000자 단위로 청킹 (200자 오버랩)
- LLM 반환 텍스트를 원문에서 `find()`로 재검증하여 정확한 span 위치 확보

## 평가 방식

- **Exact span matching**: `(start, end, normalized_type)` 기준으로 gold 라벨과 비교
- **타입 정규화**: 예측/라벨 타입을 공통 카테고리로 매핑 (예: `DATETIME` → `DATE`, `NAME_CONTEXT` → `PERSON`)
- **문서별 Precision / Recall / F1** 계산 후 전체 평균

## 실행 방법

### 사전 요구사항

- Python 3.10+
- [Ollama](https://ollama.com/) 설치 및 실행
- `llama3.2:3b` 모델 다운로드

```bash
ollama pull llama3.2:3b
```

### 의존성 설치

```bash
pip install ollama
```

### 실험 실행

```bash
python run_experiment.py
```

`run_experiment.py` 상단의 `N_SAMPLES` 값을 조절하여 실험 규모를 변경할 수 있습니다.

## 실험 결과 (N=100, echr_train.json)

| 방법 | Precision | Recall | F1 |
|------|-----------|--------|-----|
| **Rule-based** | 0.858 | 0.448 | 0.580 |
| **LLM-based** | 0.312 | 0.451 | 0.362 |

### 분석

- **Rule-based**는 높은 정밀도(0.858)를 보입니다. 정규표현식이 매칭하는 대상은 거의 정확하지만, 커버하는 엔티티 유형이 DATE와 PERSON(호칭 포함)에 한정되어 Recall이 제한적입니다.
- **LLM-based**는 더 높은 재현율(0.451)을 달성합니다. ORG, LOC, DEM 등 규칙으로 포착하기 어려운 유형까지 탐지하지만, span 경계 불일치와 과잉 탐지로 인해 Precision이 낮습니다.
- 두 방법은 상호 보완적이며, Rule-based의 높은 정밀도와 LLM-based의 넓은 커버리지를 결합하면 더 나은 성능을 기대할 수 있습니다.

## 출력 파일

- `results/pii_comparison_YYYYMMDD_HHMMSS.csv` — 문서별 / 방법별 상세 점수
- `logs/experiment_YYYYMMDD_HHMMSS.log` — 실행 로그

## 라이선스

본 프로젝트의 코드는 자유롭게 사용할 수 있습니다. TAB 데이터셋의 라이선스는 [원본 저장소](https://github.com/NorskRegnesentral/text-anonymization-benchmark)를 참조하세요.
