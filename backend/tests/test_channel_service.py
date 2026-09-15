from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from postgrest.exceptions import APIError
from telethon.errors import ChannelPrivateError, UsernameNotOccupiedError
from telethon.tl.types import Channel, User

from app.services import channel_service
from app.services.channel_service import ChannelValidationError
from tests.fakes import FakeSupabaseClient


def make_channel_entity(id=123, username="fresheroffcampus", title="Fresher Off Campus"):
    entity = MagicMock(spec=Channel)
    entity.id = id
    entity.username = username
    entity.title = title
    return entity


def make_user_entity(id=1, username="someuser"):
    entity = MagicMock(spec=User)
    entity.id = id
    entity.username = username
    return entity


# normalize_channel_username ---------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("@fresheroffcampus", "fresheroffcampus"),
        ("fresheroffcampus", "fresheroffcampus"),
        ("https://t.me/fresheroffcampus", "fresheroffcampus"),
        ("https://t.me/s/fresheroffcampus", "fresheroffcampus"),
        ("  @tech_jobs  ", "tech_jobs"),
    ],
)
def test_normalize_channel_username_accepts_all_documented_formats(raw, expected):
    assert channel_service.normalize_channel_username(raw) == expected


def test_normalize_channel_username_rejects_empty_input():
    with pytest.raises(ChannelValidationError):
        channel_service.normalize_channel_username("")


def test_normalize_channel_username_rejects_unparseable_url():
    with pytest.raises(ChannelValidationError):
        channel_service.normalize_channel_username("https://t.me/")


def test_normalize_channel_username_rejects_invalid_format():
    with pytest.raises(ChannelValidationError):
        channel_service.normalize_channel_username("ab")


# resolve_channel ---------------------------------------------------------------------------


def make_fake_telegram_client(*, authorized=True, entity=None, get_entity_exc=None):
    client = MagicMock()
    client.is_connected.return_value = True
    client.connect = AsyncMock()
    client.is_user_authorized = AsyncMock(return_value=authorized)
    if get_entity_exc:
        client.get_entity = AsyncMock(side_effect=get_entity_exc)
    else:
        client.get_entity = AsyncMock(return_value=entity)
    return client


@pytest.mark.asyncio
async def test_resolve_channel_success(monkeypatch):
    entity = make_channel_entity()
    client = make_fake_telegram_client(entity=entity)
    monkeypatch.setattr(channel_service.telegram_client, "get_client", lambda: client)

    result = await channel_service.resolve_channel("fresheroffcampus")

    assert result == {
        "telegram_channel_id": 123,
        "channel_username": "fresheroffcampus",
        "channel_name": "Fresher Off Campus",
    }


@pytest.mark.asyncio
async def test_resolve_channel_not_authenticated(monkeypatch):
    client = make_fake_telegram_client(authorized=False)
    monkeypatch.setattr(channel_service.telegram_client, "get_client", lambda: client)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.resolve_channel("somechannel")
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_resolve_channel_telegram_unconfigured(monkeypatch):
    def raise_runtime_error():
        raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in the environment.")

    monkeypatch.setattr(channel_service.telegram_client, "get_client", raise_runtime_error)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.resolve_channel("somechannel")
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_resolve_channel_not_found(monkeypatch):
    client = make_fake_telegram_client(get_entity_exc=UsernameNotOccupiedError(request=None))
    monkeypatch.setattr(channel_service.telegram_client, "get_client", lambda: client)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.resolve_channel("doesnotexist")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_resolve_channel_private(monkeypatch):
    client = make_fake_telegram_client(get_entity_exc=ChannelPrivateError(request=None))
    monkeypatch.setattr(channel_service.telegram_client, "get_client", lambda: client)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.resolve_channel("privatechannel")
    assert "inaccessible" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_resolve_channel_rejects_non_channel_entity(monkeypatch):
    user_entity = make_user_entity()
    client = make_fake_telegram_client(entity=user_entity)
    monkeypatch.setattr(channel_service.telegram_client, "get_client", lambda: client)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.resolve_channel("someuser")
    assert "not a supported" in exc_info.value.message.lower()


# create_channel ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_channel_duplicate_returns_409(monkeypatch):
    entity = make_channel_entity(id=1, username="dupechannel", title="Dupe")
    client = make_fake_telegram_client(entity=entity)
    monkeypatch.setattr(channel_service.telegram_client, "get_client", lambda: client)

    duplicate_error = APIError({"message": "duplicate key value", "code": "23505"})
    fake_supabase = FakeSupabaseClient(duplicate_error)
    monkeypatch.setattr(channel_service, "get_supabase_client", lambda: fake_supabase)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.create_channel("@dupechannel")
    assert exc_info.value.status_code == 409


# list_channels / update / delete / revalidate: Supabase error handling -----------------------


@pytest.mark.asyncio
async def test_list_channels_wraps_api_error(monkeypatch):
    fake_supabase = FakeSupabaseClient(APIError({"message": "network blip", "code": "500"}))
    monkeypatch.setattr(channel_service, "get_supabase_client", lambda: fake_supabase)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.list_channels()
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_update_channel_enabled_wraps_api_error(monkeypatch):
    fake_supabase = FakeSupabaseClient(APIError({"message": "network blip", "code": "500"}))
    monkeypatch.setattr(channel_service, "get_supabase_client", lambda: fake_supabase)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.update_channel_enabled("some-id", False)
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_update_channel_enabled_not_found(monkeypatch):
    fake_supabase = FakeSupabaseClient(SimpleNamespace(data=[]))
    monkeypatch.setattr(channel_service, "get_supabase_client", lambda: fake_supabase)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.update_channel_enabled("missing-id", True)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_channel_wraps_api_error(monkeypatch):
    fake_supabase = FakeSupabaseClient(APIError({"message": "network blip", "code": "500"}))
    monkeypatch.setattr(channel_service, "get_supabase_client", lambda: fake_supabase)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.delete_channel("some-id")
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_revalidate_channel_not_found(monkeypatch):
    fake_supabase = FakeSupabaseClient(SimpleNamespace(data=[]))
    monkeypatch.setattr(channel_service, "get_supabase_client", lambda: fake_supabase)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.revalidate_channel("missing-id")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_revalidate_channel_reports_inaccessible_without_raising(monkeypatch):
    existing_channel = {
        "id": "abc",
        "channel_username": "goneaway",
        "channel_name": "Gone Away",
        "telegram_channel_id": 999,
    }
    fake_supabase = FakeSupabaseClient(SimpleNamespace(data=[existing_channel]))
    monkeypatch.setattr(channel_service, "get_supabase_client", lambda: fake_supabase)

    async def fake_resolve_channel(username):
        raise ChannelValidationError("Telegram channel not found.", status_code=400)

    monkeypatch.setattr(channel_service, "resolve_channel", fake_resolve_channel)

    result = await channel_service.revalidate_channel("abc")

    assert result["accessible"] is False
    assert result["detail"] == "Telegram channel not found."
    assert result["channel"] == existing_channel


@pytest.mark.asyncio
async def test_update_channel_enabled_invalid_id_returns_400_not_502(monkeypatch):
    malformed_uuid_error = APIError({"message": "invalid input syntax for type uuid", "code": "22P02"})
    fake_supabase = FakeSupabaseClient(malformed_uuid_error)
    monkeypatch.setattr(channel_service, "get_supabase_client", lambda: fake_supabase)

    with pytest.raises(ChannelValidationError) as exc_info:
        await channel_service.update_channel_enabled("not-a-uuid", True)
    assert exc_info.value.status_code == 400
