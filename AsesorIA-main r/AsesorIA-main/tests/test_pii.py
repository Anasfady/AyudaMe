from src.privacy.pii import redact_pii


def test_redacts_email():
    text, found = redact_pii("Contacto: persona@example.com")

    assert text == "Contacto: [EMAIL]"
    assert found == ["EMAIL"]


def test_redacts_nif():
    text, found = redact_pii("NIF: 12345678Z")

    assert text == "NIF: [NIF]"
    assert found == ["NIF"]


def test_redacts_nie():
    text, found = redact_pii("NIE: X1234567L")

    assert text == "NIE: [NIE]"
    assert found == ["NIE"]


def test_redacts_iban():
    text, found = redact_pii("Cuenta: ES12 1234 5678 9012 3456 7890")

    assert text == "Cuenta: [IBAN]"
    assert found == ["IBAN"]


def test_redacts_phone():
    text, found = redact_pii("Teléfono: +34 612 345 678")

    assert text == "Teléfono: [PHONE]"
    assert found == ["PHONE"]


def test_redacts_multiple_pii_values():
    text, found = redact_pii("NIF 12345678Z, email persona@example.com")

    assert "[NIF]" in text
    assert "[EMAIL]" in text
    assert set(found) == {"NIF", "EMAIL"}


def test_does_not_modify_text_without_detected_pii():
    text = "La cuota de RETA es deducible en IRPF."

    redacted, found = redact_pii(text)

    assert redacted == text
    assert found == []


def test_iban_is_redacted_before_phone_pattern_can_match_digits():
    text, found = redact_pii("IBAN ES12 1234 5678 9012 3456 7890")

    assert text == "IBAN [IBAN]"
    assert found == ["IBAN"]
