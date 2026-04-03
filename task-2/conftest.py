import random
import re
import time
from datetime import datetime

import pytest
import requests


BASE_URL = "https://qa-internship.avito.com"
TIMEOUT = 30


def random_seller_id() -> int:
    return random.randint(111111, 999999)


def unique_name(prefix: str = "QA item") -> str:
    return f"{prefix}-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"


def make_payload(
    seller_id: int | None = None,
    name: str | None = None,
    price: int = 1000,
    likes: int = 1,
    view_count: int = 10,
    contacts: int = 1,
) -> dict:
    return {
        "sellerID": seller_id if seller_id is not None else random_seller_id(),
        "name": name if name is not None else unique_name(),
        "price": price,
        "statistics": {
            "likes": likes,
            "viewCount": view_count,
            "contacts": contacts,
        },
    }


def safe_json(response: requests.Response):
    try:
        return response.json()
    except ValueError:
        return None


def normalize_single_ad(data):
    if isinstance(data, list):
        assert len(data) > 0, "Ответ пустой список"
        return data[0]
    return data


def extract_id_from_status(data: dict) -> str:
    assert isinstance(data, dict), f"Expected dict, got {type(data)}"
    assert "status" in data, f"No 'status' field in response: {data}"

    match = re.search(r"([0-9a-fA-F-]{36})", data["status"])
    assert match is not None, f"Could not extract id from status: {data['status']}"
    return match.group(1)


def assert_ad_contract(ad: dict):
    assert isinstance(ad, dict), f"Ожидался dict, получено {type(ad)}"

    for key in ("id", "sellerId", "name", "price", "statistics", "createdAt"):
        assert key in ad, f"В ответе отсутствует поле {key}"

    assert isinstance(ad["id"], str), "Поле id должно быть строкой"
    assert isinstance(ad["sellerId"], int), "Поле sellerId должно быть int"
    assert isinstance(ad["name"], str), "Поле name должно быть str"
    assert isinstance(ad["price"], int), "Поле price должно быть int"
    assert isinstance(ad["statistics"], dict), "Поле statistics должно быть dict"
    assert isinstance(ad["createdAt"], str), "Поле createdAt должно быть str"

    stats = ad["statistics"]
    for key in ("likes", "viewCount", "contacts"):
        assert key in stats, f"В statistics отсутствует поле {key}"
        assert isinstance(stats[key], int), f"Поле statistics.{key} должно быть int"


def assert_stats_contract(stats_data):
    assert isinstance(stats_data, list), f"Ожидался list, получено {type(stats_data)}"
    assert len(stats_data) > 0, "Список статистики пуст"

    first = stats_data[0]
    assert isinstance(first, dict), "Элемент статистики должен быть dict"

    for key in ("likes", "viewCount", "contacts"):
        assert key in first, f"В статистике отсутствует поле {key}"
        assert isinstance(first[key], int), f"Поле статистики {key} должно быть int"


def parse_created_at(value: str):
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise AssertionError(f"Некорректный формат createdAt: {value}") from exc


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api_session():
    session = requests.Session()
    session.trust_env = False
    session.proxies = {}
    session.headers.update({"Accept": "application/json"})
    return session


@pytest.fixture
def seller_id():
    return random_seller_id()


@pytest.fixture
def ad_payload(seller_id):
    return make_payload(seller_id=seller_id)


@pytest.fixture
def created_ad(base_url, api_session, ad_payload):
    create_response = api_session.post(
        f"{base_url}/api/1/item",
        json=ad_payload,
        timeout=TIMEOUT,
    )
    assert create_response.status_code == 200, (
        f"Не удалось создать объявление. "
        f"status={create_response.status_code}, body={create_response.text}"
    )

    create_data = safe_json(create_response)
    assert create_data is not None, "Ответ создания не JSON"
    assert "status" in create_data, f"В ответе создания нет поля status: {create_data}"

    item_id = extract_id_from_status(create_data)

    get_response = api_session.get(
        f"{base_url}/api/1/item/{item_id}",
        timeout=TIMEOUT,
    )
    assert get_response.status_code == 200, (
        f"Не удалось получить созданное объявление по id={item_id}. "
        f"status={get_response.status_code}, body={get_response.text}"
    )

    get_data = safe_json(get_response)
    assert get_data is not None, "Ответ получения объявления не JSON"
    ad_data = normalize_single_ad(get_data)
    assert_ad_contract(ad_data)

    return {
        "request": ad_payload,
        "create_response": create_data,
        "response": ad_data,
    }


@pytest.fixture
def second_ad_same_seller(base_url, api_session, created_ad):
    payload = make_payload(
        seller_id=created_ad["request"]["sellerID"],
        name=unique_name("Second"),
        price=2222,
        likes=2,
        view_count=20,
        contacts=1,
    )

    create_response = api_session.post(
        f"{base_url}/api/1/item",
        json=payload,
        timeout=TIMEOUT,
    )
    assert create_response.status_code == 200, (
        f"Не удалось создать второе объявление. "
        f"status={create_response.status_code}, body={create_response.text}"
    )

    create_data = safe_json(create_response)
    assert create_data is not None, "Ответ создания второго объявления не JSON"
    assert "status" in create_data, f"В ответе создания нет поля status: {create_data}"

    item_id = extract_id_from_status(create_data)

    get_response = api_session.get(
        f"{base_url}/api/1/item/{item_id}",
        timeout=TIMEOUT,
    )
    assert get_response.status_code == 200, (
        f"Не удалось получить второе объявление по id={item_id}. "
        f"status={get_response.status_code}, body={get_response.text}"
    )

    get_data = safe_json(get_response)
    assert get_data is not None, "Ответ получения второго объявления не JSON"
    ad_data = normalize_single_ad(get_data)
    assert_ad_contract(ad_data)

    return {
        "request": payload,
        "create_response": create_data,
        "response": ad_data,
    }