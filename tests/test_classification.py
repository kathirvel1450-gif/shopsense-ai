from app.guardrails.classification import classify_few_shot, classify_zero_shot
from app.guardrails.model_gateway import GuardrailGateway, _DeterministicMockProvider
from app.guardrails.schemas import validate_classification_output


def test_zero_shot_and_few_shot_use_allowed_structured_categories():
    gateway = GuardrailGateway(provider=_DeterministicMockProvider())
    zero = classify_zero_shot("Please refund my delivery", gateway)
    few = classify_few_shot("The app crashes when I login", gateway)
    assert zero.category == "REFUND"
    assert few.category == "APP_ISSUE"
    assert zero.status == few.status == "classified"


def test_invalid_model_output_categories_and_confidence_are_rejected():
    for invalid in ({"category": "UNKNOWN_CATEGORY", "confidence": 0.5, "rationale": "x"}, {"category": "OTHER", "confidence": 5, "rationale": "x"}, "not json"):
        try:
            validate_classification_output(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid classification output was accepted")
