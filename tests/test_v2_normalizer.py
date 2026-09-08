from v2.normalizer import TurkishTextNormalizer, number_to_turkish


def test_number_to_turkish_core_cases():
    assert number_to_turkish(0) == "sıfır"
    assert number_to_turkish(12) == "on iki"
    assert number_to_turkish(1250) == "bin iki yüz elli"
    assert number_to_turkish(2024) == "iki bin yirmi dört"


def test_normalizes_date_percentage_currency_and_abbreviation():
    normalizer = TurkishTextNormalizer()
    result = normalizer.normalize("Dr. Ahmet 12.03.2024 tarihinde %25 indirimle 1.250 TL ödedi.")

    assert "Doktor Ahmet" in result.spoken_text
    assert "on iki Mart iki bin yirmi dört" in result.spoken_text
    assert "yüzde yirmi beş" in result.spoken_text
    assert "bin iki yüz elli Türk lirası" in result.spoken_text

    kinds = {event.kind for event in result.events}
    assert {"abbreviation", "date", "percentage", "currency_try"}.issubset(kinds)


def test_does_not_needlessly_rewrite_plain_literary_text():
    normalizer = TurkishTextNormalizer()
    source = "Kapının arkasından bir ses geldi. Ahmet donup kaldı."
    result = normalizer.normalize(source)
    assert result.spoken_text == source
