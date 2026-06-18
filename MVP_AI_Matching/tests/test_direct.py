import json
import pathlib

from app.schemas import ParsedCV, ParsedJD
from app.services.scorer import calculate_score

_SAMPLE = pathlib.Path(__file__).parent.parent / "sample_data" / "score_request.json"


def test_score():
    with open(_SAMPLE, "r", encoding="utf-8") as f:
        data = json.load(f)

    parsed_cv = ParsedCV(**data["parsed_cv"])
    parsed_jd = ParsedJD(**data["parsed_jd"])
    cv_embedding = data["cv_embedding"]
    jd_embedding = data["jd_embedding"]
    cv_raw_text = data.get("cv_raw_text", "")
    weights = data.get("weights")

    result = calculate_score(
        parsed_cv=parsed_cv,
        parsed_jd=parsed_jd,
        cv_embedding=cv_embedding,
        jd_embedding=jd_embedding,
        cv_raw_text=cv_raw_text,
        weights=weights,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_score()
