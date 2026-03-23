"""Testes das rotas de reuniões do GC."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from faker import Faker

from app.models.gc_meeting import GcMeeting

fake = Faker()


def _meetings_url(gc_id, meeting_id=None):
    base = f"/api/v1/gcs/{gc_id}/meetings"
    return f"{base}/{meeting_id}" if meeting_id else f"{base}/"


def _make_fake_meeting(gc_id=None, **overrides):
    """Cria mock de GcMeeting compatível com GcMeetingResponse.model_validate()."""
    meeting = MagicMock(spec=GcMeeting)
    meeting.id = overrides.get("id", uuid.uuid4())
    meeting.gc_id = gc_id or uuid.uuid4()
    meeting.weekday = overrides.get("weekday", fake.random_int(min=0, max=6))
    meeting.start_time = overrides.get("start_time", "19:30")
    meeting.notes = overrides.get("notes", fake.sentence())
    meeting.created_at = overrides.get("created_at", datetime.now())
    return meeting


class TestListMeetings:
    """Testa GET /api/v1/gcs/{gc_id}/meetings/ (pública)."""

    @patch("app.routers.gc_meetings.GcService")
    def test_list_meetings_success(self, MockService, client):
        """Deve retornar 200 com lista de reuniões."""
        gc_id = uuid.uuid4()
        mock_service = MockService.return_value
        mock_service.list_meetings = AsyncMock(return_value=[
            _make_fake_meeting(gc_id), _make_fake_meeting(gc_id),
        ])
        resp = client.get(_meetings_url(gc_id))
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2


class TestCreateMeeting:
    """Testa POST /api/v1/gcs/{gc_id}/meetings/ (autenticada)."""

    @patch("app.routers.gc_meetings.GcService")
    def test_create_meeting_success(self, MockService, client):
        """Payload válido deve retornar 201."""
        gc_id = uuid.uuid4()
        meeting = _make_fake_meeting(gc_id)
        mock_service = MockService.return_value
        mock_service.create_meeting = AsyncMock(return_value=meeting)
        resp = client.post(_meetings_url(gc_id), json={
            "weekday": 3,
            "start_time": "20:00",
            "notes": fake.sentence(),
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["id"] == str(meeting.id)


class TestUpdateMeeting:
    """Testa PUT /api/v1/gcs/{gc_id}/meetings/{meeting_id} (autenticada)."""

    @patch("app.routers.gc_meetings.GcService")
    def test_update_meeting_success(self, MockService, client):
        """Atualização deve retornar 200."""
        gc_id = uuid.uuid4()
        meeting = _make_fake_meeting(gc_id)
        mock_service = MockService.return_value
        mock_service.update_meeting = AsyncMock(return_value=meeting)
        resp = client.put(_meetings_url(gc_id, meeting.id), json={
            "start_time": "21:00",
        })
        assert resp.status_code == 200


class TestDeleteMeeting:
    """Testa DELETE /api/v1/gcs/{gc_id}/meetings/{meeting_id} (autenticada)."""

    @patch("app.routers.gc_meetings.GcService")
    def test_delete_meeting_success(self, MockService, client):
        """Remoção deve retornar 200."""
        gc_id = uuid.uuid4()
        meeting_id = uuid.uuid4()
        mock_service = MockService.return_value
        mock_service.delete_meeting = AsyncMock()
        resp = client.delete(_meetings_url(gc_id, meeting_id))
        assert resp.status_code == 200
        assert resp.json()["message"]
