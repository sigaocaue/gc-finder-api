"""Unit tests for GC meetings router endpoints."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.routers import gc_meetings
from app.schemas.gc_meeting import GcMeetingCreate, GcMeetingUpdate


def build_meeting():
    return SimpleNamespace(
        id=uuid.uuid4(),
        gc_id=uuid.uuid4(),
        weekday=2,
        start_time="19:30",
        notes="Weekly",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:01",
    )


@pytest.mark.asyncio
@patch("app.routers.gc_meetings.GcService")
async def test_list_meetings_returns_response(mock_service):
    service = mock_service.return_value
    meetings = [build_meeting()]
    service.list_meetings = AsyncMock(return_value=meetings)

    response = await gc_meetings.list_meetings("gc-id", db=SimpleNamespace())

    assert response.message == "Lista de reuniões"
    assert response.data[0].start_time == "19:30"
    service.list_meetings.assert_awaited_once_with("gc-id")


@pytest.mark.asyncio
@patch("app.routers.gc_meetings.GcService")
async def test_create_meeting_success(mock_service):
    service = mock_service.return_value
    meeting = build_meeting()
    service.create_meeting = AsyncMock(return_value=meeting)
    body = GcMeetingCreate(weekday=2, start_time="19:30")

    response = await gc_meetings.create_meeting("gc-id", body, current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Reunião criada com sucesso"
    assert response.data.id == meeting.id
    service.create_meeting.assert_awaited_once_with("gc-id", body)


@pytest.mark.asyncio
@patch("app.routers.gc_meetings.GcService")
async def test_update_meeting_success(mock_service):
    service = mock_service.return_value
    meeting = build_meeting()
    service.update_meeting = AsyncMock(return_value=meeting)
    body = GcMeetingUpdate(notes="Updated")

    response = await gc_meetings.update_meeting("gc-id", "meeting-id", body, current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Reunião atualizada com sucesso"
    assert response.data.notes == "Weekly"
    service.update_meeting.assert_awaited_once_with("gc-id", "meeting-id", body)


@pytest.mark.asyncio
@patch("app.routers.gc_meetings.GcService")
async def test_delete_meeting_success(mock_service):
    service = mock_service.return_value
    service.delete_meeting = AsyncMock(return_value=None)

    response = await gc_meetings.delete_meeting("gc-id", "meeting-id", current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Reunião removida com sucesso"
    service.delete_meeting.assert_awaited_once_with("gc-id", "meeting-id")
