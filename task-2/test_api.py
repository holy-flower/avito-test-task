import time

import pytest
import requests

from conftest import (
    TIMEOUT,
    assert_ad_contract,
    assert_stats_contract,
    extract_id_from_status,
    make_payload,
    normalize_single_ad,
    parse_created_at,
    random_seller_id,
    safe_json,
    unique_name,
)

def test_tc001_create_ad_with_valid_data(base_url, api_session, ad_payload):
    response = api_session.post(
        f"{base_url}/api/1/item",
        json=ad_payload,
        timeout=TIMEOUT,
    )

    assert response.status_code == 200
    assert "application/json" in response.headers.get("Content-Type", "")

    data = safe_json(response)
    assert data is not None
    assert "status" in data

    item_id = extract_id_from_status(data)
    assert item_id

    get_response = api_session.get(
        f"{base_url}/api/1/item/{item_id}",
        timeout=TIMEOUT,
    )
    assert get_response.status_code == 200

    ad_data = normalize_single_ad(safe_json(get_response))
    assert_ad_contract(ad_data)
    assert ad_data["id"] == item_id
    assert ad_data["sellerId"] == ad_payload["sellerID"]
    assert ad_data["name"] == ad_payload["name"]
    assert ad_data["price"] == ad_payload["price"]
    assert ad_data["statistics"] == ad_payload["statistics"]


def test_tc002_get_ad_by_existing_id(base_url, api_session, created_ad):
    item_id = created_ad["response"]["id"]

    response = api_session.get(f"{base_url}/api/1/item/{item_id}", timeout=TIMEOUT)

    assert response.status_code == 200
    data = safe_json(response)
    assert data is not None

    ad = normalize_single_ad(data)
    assert_ad_contract(ad)

    assert ad["id"] == item_id
    assert ad["sellerId"] == created_ad["request"]["sellerID"]
    assert ad["name"] == created_ad["request"]["name"]
    assert ad["price"] == created_ad["request"]["price"]
    assert ad["statistics"] == created_ad["request"]["statistics"]


def test_tc003_get_ads_by_seller_id(base_url, api_session, created_ad, second_ad_same_seller):
    seller_id = created_ad["request"]["sellerID"]
    first_id = created_ad["response"]["id"]
    second_id = second_ad_same_seller["response"]["id"]

    response = api_session.get(f"{base_url}/api/1/{seller_id}/item", timeout=TIMEOUT)

    assert response.status_code == 200
    assert "application/json" in response.headers.get("Content-Type", "")

    data = safe_json(response)
    assert isinstance(data, list)
    assert len(data) > 0

    ids = []
    for ad in data:
        assert_ad_contract(ad)
        assert ad["sellerId"] == seller_id
        ids.append(ad["id"])

    assert first_id in ids
    assert second_id in ids


def test_tc004_get_statistics_by_existing_item_id(base_url, api_session, created_ad):
    item_id = created_ad["response"]["id"]

    response = api_session.get(f"{base_url}/api/1/statistic/{item_id}", timeout=TIMEOUT)

    assert response.status_code == 200
    assert "application/json" in response.headers.get("Content-Type", "")

    data = safe_json(response)
    assert data is not None
    assert_stats_contract(data)

    first = data[0]
    expected = created_ad["request"]["statistics"]
    assert first["likes"] == expected["likes"]
    assert first["viewCount"] == expected["viewCount"]
    assert first["contacts"] == expected["contacts"]


def test_tc005_create_ad_without_name(base_url, api_session, seller_id):
    payload = {
        "sellerID": seller_id,
        "price": 1000,
        "statistics": {"likes": 1, "viewCount": 10, "contacts": 1},
    }

    response = api_session.post(
        f"{base_url}/api/1/item",
        json=payload,
        timeout=TIMEOUT,
    )

    assert response.status_code in (400, 422)


def test_tc006_create_ad_without_price(base_url, api_session, seller_id):
    payload = {
        "sellerID": seller_id,
        "name": unique_name(),
        "statistics": {"likes": 1, "viewCount": 10, "contacts": 1},
    }

    response = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)

    assert response.status_code in (400, 422)
    assert "application/json" in response.headers.get("Content-Type", "")


def test_tc007_create_ad_with_invalid_seller_id(base_url, api_session):
    payload = {
        "sellerID": "invalid",
        "name": unique_name(),
        "price": 1000,
        "statistics": {"likes": 1, "viewCount": 10, "contacts": 1},
    }

    response = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)

    assert response.status_code in (400, 422)
    assert "application/json" in response.headers.get("Content-Type", "")


def test_tc008_get_ad_by_nonexistent_id(base_url, api_session):
    nonexistent_id = "00000000-0000-0000-0000-000000000000"

    response = api_session.get(
        f"{base_url}/api/1/item/{nonexistent_id}",
        timeout=TIMEOUT,
    )

    assert response.status_code == 404
    assert "application/json" in response.headers.get("Content-Type", "")


def test_tc009_get_statistics_by_nonexistent_item_id(base_url, api_session):
    nonexistent_id = "00000000-0000-0000-0000-000000000000"

    response = api_session.get(
        f"{base_url}/api/1/statistic/{nonexistent_id}",
        timeout=TIMEOUT,
    )

    assert response.status_code == 404
    assert "application/json" in response.headers.get("Content-Type", "")


def test_tc010_get_ad_by_invalid_id_format(base_url, api_session):
    response = api_session.get(
        f"{base_url}/api/1/item/%20%20%20",
        timeout=TIMEOUT,
    )

    assert response.status_code in (400, 404)
    assert "application/json" in response.headers.get("Content-Type", "")


def test_tc011_get_statistics_by_invalid_id_format(base_url, api_session):
    response = api_session.get(
        f"{base_url}/api/1/statistic/@@@",
        timeout=TIMEOUT,
    )

    assert response.status_code in (400, 404)
    assert "application/json" in response.headers.get("Content-Type", "")


def test_tc012_create_ad_without_statistics(base_url, api_session, seller_id):
    payload = {
        "sellerID": seller_id,
        "name": unique_name(),
        "price": 1000,
    }

    response = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)

    assert response.status_code in (400, 422)
    assert "application/json" in response.headers.get("Content-Type", "")


def test_tc013_create_ad_with_invalid_price(base_url, api_session, seller_id):
    payload = {
        "sellerID": seller_id,
        "name": unique_name(),
        "price": "wrong-price",
        "statistics": {"likes": 1, "viewCount": 10, "contacts": 1},
    }

    response = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)

    assert response.status_code in (400, 422)
    assert "application/json" in response.headers.get("Content-Type", "")


def test_tc014_create_ad_with_invalid_statistics_structure(base_url, api_session, seller_id):
    payload = {
        "sellerID": seller_id,
        "name": unique_name(),
        "price": 1000,
        "statistics": {
            "likes": "one",
            "viewCount": "ten",
            "contacts": "zero",
        },
    }

    response = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)

    assert response.status_code in (400, 422)
    assert "application/json" in response.headers.get("Content-Type", "")


def test_tc015_get_ads_for_seller_without_ads(base_url, api_session):
    for _ in range(5):
        seller_id = random_seller_id()
        response = api_session.get(f"{base_url}/api/1/{seller_id}/item", timeout=TIMEOUT)

        assert response.status_code in (200, 404)
        assert response.status_code != 500

        if response.status_code == 200:
            data = safe_json(response)
            assert isinstance(data, list)


def test_tc016_repeat_same_post_request_behavior(base_url, api_session):
    payload = make_payload(
        seller_id=random_seller_id(),
        name=unique_name("duplicate"),
        price=5555,
        likes=5,
        view_count=50,
        contacts=3,
    )

    response1 = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)
    response2 = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = safe_json(response1)
    data2 = safe_json(response2)

    id1 = extract_id_from_status(data1)
    id2 = extract_id_from_status(data2)

    assert id1 != id2, (
        "Одинаковые POST-запросы вернули одинаковый id. "
        "Если это ожидаемая идемпотентность, она должна быть явно задокументирована."
    )


def test_tc017_create_ad_with_minimally_reasonable_valid_values(base_url, api_session):
    payload = {
        "sellerID": 111111,
        "name": "a",
        "price": 1,
        "statistics": {"likes": 1, "viewCount": 1, "contacts": 1},
    }

    response = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)

    assert response.status_code == 200, (
        f"Минимально разумно валидный payload должен создаваться. "
        f"status={response.status_code}, body={response.text}"
    )

    data = safe_json(response)
    item_id = extract_id_from_status(data)

    get_response = api_session.get(f"{base_url}/api/1/item/{item_id}", timeout=TIMEOUT)
    assert get_response.status_code == 200

    ad = normalize_single_ad(safe_json(get_response))
    assert_ad_contract(ad)
    assert ad["sellerId"] == payload["sellerID"]
    assert ad["name"] == payload["name"]
    assert ad["price"] == payload["price"]


def test_tc018_create_ad_with_large_values_no_500(base_url, api_session):
    payload = {
        "sellerID": 999999,
        "name": "X" * 256,
        "price": 2_147_483_647,
        "statistics": {
            "likes": 999_999,
            "viewCount": 9_999_999,
            "contacts": 999_999,
        },
    }

    response = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)

    assert response.status_code != 500
    assert response.status_code in (200, 400, 422)

    if response.status_code == 200:
        data = safe_json(response)
        item_id = extract_id_from_status(data)

        get_response = api_session.get(f"{base_url}/api/1/item/{item_id}", timeout=TIMEOUT)
        assert get_response.status_code == 200

        ad = normalize_single_ad(safe_json(get_response))
        assert_ad_contract(ad)
    else:
        assert "application/json" in response.headers.get("Content-Type", "")


@pytest.mark.parametrize("boundary_seller_id", [111111, 999999])
def test_tc019_seller_id_boundaries(base_url, api_session, boundary_seller_id):
    payload = make_payload(
        seller_id=boundary_seller_id,
        name=unique_name(f"boundary-{boundary_seller_id}"),
        price=1500,
        likes=1,
        view_count=5,
        contacts=1,
    )

    response = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)

    assert response.status_code == 200
    data = safe_json(response)
    item_id = extract_id_from_status(data)

    get_response = api_session.get(f"{base_url}/api/1/item/{item_id}", timeout=TIMEOUT)
    assert get_response.status_code == 200

    ad = normalize_single_ad(safe_json(get_response))
    assert_ad_contract(ad)
    assert ad["sellerId"] == boundary_seller_id


def test_tc020_create_ad_response_time(base_url, api_session):
    payload = make_payload(
        seller_id=random_seller_id(),
        name=unique_name("perf"),
        price=1200,
        likes=1,
        view_count=1,
        contacts=1,
    )

    start = time.perf_counter()
    response = api_session.post(f"{base_url}/api/1/item", json=payload, timeout=TIMEOUT)
    duration = time.perf_counter() - start

    assert response.status_code == 200
    assert duration < 5, f"Время ответа превышает 5 секунд: {duration:.3f}"


@pytest.mark.parametrize(
    "method, path",
    [
        ("POST", "/api/1/item"),
        ("GET", "created_item"),
        ("GET", "seller_items"),
        ("GET", "stats"),
    ],
)
def test_tc021_content_type(base_url, api_session, created_ad, method, path):
    if method == "POST":
        response = api_session.post(
            f"{base_url}/api/1/item",
            json=make_payload(
                seller_id=random_seller_id(),
                name=unique_name("content-type"),
                price=1300,
                contacts=1,
            ),
            timeout=TIMEOUT,
        )
    elif path == "created_item":
        response = api_session.get(
            f"{base_url}/api/1/item/{created_ad['response']['id']}",
            timeout=TIMEOUT,
        )
    elif path == "seller_items":
        response = api_session.get(
            f"{base_url}/api/1/{created_ad['request']['sellerID']}/item",
            timeout=TIMEOUT,
        )
    else:
        response = api_session.get(
            f"{base_url}/api/1/statistic/{created_ad['response']['id']}",
            timeout=TIMEOUT,
        )

    assert response.status_code == 200
    assert "application/json" in response.headers.get("Content-Type", "")


def test_tc022_response_contract(base_url, api_session, created_ad):
    item_id = created_ad["response"]["id"]
    seller_id = created_ad["request"]["sellerID"]

    create_response = api_session.post(
        f"{base_url}/api/1/item",
        json=make_payload(
            seller_id=random_seller_id(),
            name=unique_name("contract"),
            price=1400,
            likes=4,
            view_count=40,
            contacts=2,
        ),
        timeout=TIMEOUT,
    )
    assert create_response.status_code == 200
    create_data = safe_json(create_response)
    assert create_data is not None
    assert "status" in create_data
    create_item_id = extract_id_from_status(create_data)

    create_get_response = api_session.get(
        f"{base_url}/api/1/item/{create_item_id}",
        timeout=TIMEOUT,
    )
    assert create_get_response.status_code == 200
    create_get_data = normalize_single_ad(safe_json(create_get_response))
    assert_ad_contract(create_get_data)

    get_response = api_session.get(f"{base_url}/api/1/item/{item_id}", timeout=TIMEOUT)
    assert get_response.status_code == 200
    get_data = normalize_single_ad(safe_json(get_response))
    assert_ad_contract(get_data)

    seller_response = api_session.get(f"{base_url}/api/1/{seller_id}/item", timeout=TIMEOUT)
    assert seller_response.status_code == 200
    seller_data = safe_json(seller_response)
    assert isinstance(seller_data, list)
    assert len(seller_data) > 0
    for ad in seller_data:
        assert_ad_contract(ad)

    stats_response = api_session.get(f"{base_url}/api/1/statistic/{item_id}", timeout=TIMEOUT)
    assert stats_response.status_code == 200
    stats_data = safe_json(stats_response)
    assert_stats_contract(stats_data)


@pytest.mark.xfail(reason="BUG-003: createdAt has invalid datetime format")
def test_tc023_created_at_format(base_url, api_session, created_ad):
    item_id = created_ad["response"]["id"]
    seller_id = created_ad["request"]["sellerID"]

    get_response = api_session.get(f"{base_url}/api/1/item/{item_id}", timeout=TIMEOUT)
    assert get_response.status_code == 200
    get_data = normalize_single_ad(safe_json(get_response))
    assert "createdAt" in get_data
    assert isinstance(get_data["createdAt"], str)
    parse_created_at(get_data["createdAt"])

    seller_response = api_session.get(f"{base_url}/api/1/{seller_id}/item", timeout=TIMEOUT)
    assert seller_response.status_code == 200
    seller_data = safe_json(seller_response)
    assert isinstance(seller_data, list)
    assert len(seller_data) > 0

    for ad in seller_data:
        assert "createdAt" in ad
        assert isinstance(ad["createdAt"], str)
        parse_created_at(ad["createdAt"])