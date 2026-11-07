def test_get_seeded_artwork(client, seeded_db):
    # Arrange: seeded_db has already loaded the 11 artworks (the Mona Lisa is first)
    expected = {"id": 1, **seeded_db[0]}

    # Act
    response = client.get("/artworks/1")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected


def test_list_artworks_empty(client):
    # Arrange:
    # there will be an empty database..
    
    # Act:
    response = client.get("/artworks/")

    # Assert:
    assert response.status_code == 200
    assert response.json() == []


def test_create_artwork(client, sample_artwork):
    # Arrange:

    # Act:
    response = client.post("/artworks/",json=sample_artwork)

    # Assert:
    assert response.status_code == 201


def test_create_artwork_is_saved(client, created_artwork):
    # Arr.:
    artwork_id = created_artwork["id"]

    # Act:
    response = client.get(f"/artworks/{artwork_id}")
    
    # Assert:
    assert response.status_code == 200
    assert response.json() == created_artwork


def test_update_artwork(client, created_artwork, updated_artwork):

    # Arrange
    artwork_id = created_artwork["id"]

    # Act
    response = client.put(
        f"/artworks/{artwork_id}",
        json=updated_artwork
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "id": artwork_id,
        **updated_artwork
    }

    response = client.get(f"/artworks/{artwork_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": artwork_id,
        **updated_artwork
    }


def test_delete_artwork(client, created_artwork):

    # Arrange
    artwork_id = created_artwork["id"]

    # Act
    response = client.delete(f"/artworks/{artwork_id}")

    # Assert
    assert response.status_code == 204
    response = client.get(f"/artworks/{artwork_id}")
    assert response.status_code == 404



# UNHAPPY-PATH TESTS :(
import pytest

@pytest.mark.parametrize(
    "method, use_body",
    [
        ("get", False),
        ("put", True),
        ("delete", False),
    ],
    ids=["get", "put", "delete"],
)
def test_artwork_not_found(client, sample_artwork, method, use_body):

    kwargs = {"json": sample_artwork} if use_body else {}

    response = client.request(
        method,
        "/artworks/9999",
        **kwargs
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Artwork not found"
    }


def test_non_integer_id(client):

    response = client.get("/artworks/mona-lisa")

    assert response.status_code == 422


def test_create_duplicate(client, created_artwork, sample_artwork):

    response = client.post(
        "/artworks/",
        json=sample_artwork
    )

    assert response.status_code == 409


def test_create_duplicate_ignores_case(
    client,
    created_artwork,
    sample_artwork
):

    duplicate = sample_artwork.copy()

    duplicate["title"] = duplicate["title"].upper()
    duplicate["artist"] = duplicate["artist"].lower()

    response = client.post(
        "/artworks/",
        json=duplicate
    )

    assert response.status_code == 409


def test_update_into_duplicate(client, seeded_db):

    duplicate_data = {
        "title": seeded_db[0]["title"],
        "artist": seeded_db[0]["artist"],
        "year": seeded_db[1]["year"],
        "medium": seeded_db[1]["medium"],
        "museum": seeded_db[1]["museum"],
        "image_url": seeded_db[1]["image_url"]
    }

    response = client.put(
        "/artworks/2",
        json=duplicate_data
    )

    assert response.status_code == 409

    response = client.get("/artworks/2")

    assert response.status_code == 200
    assert response.json()["title"] == seeded_db[1]["title"]
    assert response.json()["artist"] == seeded_db[1]["artist"]


def test_update_same_title_and_artist_is_allowed(
    client,
    created_artwork
):

    artwork_id = created_artwork["id"]

    updated = created_artwork.copy()

    updated["museum"] = "Different Museum"

    response = client.put(
        f"/artworks/{artwork_id}",
        json=updated
    )

    assert response.status_code == 200

    response = client.get(
        f"/artworks/{artwork_id}"
    )

    assert response.status_code == 200
    assert response.json()["museum"] == "Different Museum"


@pytest.mark.parametrize(
    "missing_field",
    [
        "title",
        "artist",
        "year",
        "medium",
        "museum",
        "image_url",
    ]
)
def test_create_missing_field(
    client,
    sample_artwork,
    missing_field,
):

    artwork = sample_artwork.copy()

    del artwork[missing_field]

    response = client.post(
        "/artworks/",
        json=artwork
    )

    assert response.status_code == 422

    assert response.json()["detail"][0]["loc"] == [
        "body",
        missing_field,
    ]


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("year", 3000),
        ("year", "nineteen-oh-seven"),
        ("title", ""),
    ],
    ids=["future-year", "year-not-int", "empty-title"]
)
def test_create_invalid_value(
    client,
    sample_artwork,
    field,
    bad_value,
):

    artwork = sample_artwork.copy()

    artwork[field] = bad_value

    response = client.post(
        "/artworks/",
        json=artwork,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "skip,limit,expected_count",
    [
        (0, 3, 3),
        (0, 1, 1),
        (0, 0, 0),
        (100, 10, 0),
    ],
)
def test_pagination_counts(
    client,
    seeded_db,
    skip,
    limit,
    expected_count,
):

    response = client.get(
        "/artworks/",
        params={
            "skip": skip,
            "limit": limit,
        }
    )

    assert response.status_code == 200
    assert len(response.json()) == expected_count


@pytest.mark.parametrize(
    "params",
    [
        {"skip": -1},
        {"limit": -1},
    ]
)
def test_pagination_invalid(client, params):

    response = client.get(
        "/artworks/",
        params=params,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "artist,expected_count",
    [
        ("Claude Monet", 2),
        ("monet", 2),
        ("artist-does-not-exist", 0),
    ]
)
def test_filter_by_artist(
    client,
    seeded_db,
    artist,
    expected_count,
):

    response = client.get(
        "/artworks/",
        params={"artist": artist},
    )

    assert response.status_code == 200

    assert len(response.json()) == expected_count