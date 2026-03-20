"""Testes da rota de estatísticas — requer AdminUser."""

from unittest.mock import AsyncMock, MagicMock

from faker import Faker

fake = Faker()

ENDPOINT = "/api/v1/stats/counts"


class TestEntityCounts:
    """Testa GET /api/v1/stats/counts."""

    def test_get_entity_counts_success(self, admin_client, mock_db):
        """Deve retornar 200 com contagens de todas as entidades."""
        expected_counts = {
            "users": fake.random_int(min=1, max=100),
            "leaders": fake.random_int(min=1, max=100),
            "gcs": fake.random_int(min=1, max=100),
            "meetings": fake.random_int(min=1, max=100),
            "medias": fake.random_int(min=1, max=100),
            "leader_contacts": fake.random_int(min=1, max=100),
        }

        # A rota faz 6 chamadas a db.execute, cada uma com .scalar_one()
        results = []
        for key in ["users", "leaders", "gcs", "meetings", "medias", "leader_contacts"]:
            result_mock = MagicMock()
            result_mock.scalar_one.return_value = expected_counts[key]
            results.append(result_mock)

        mock_db.execute = AsyncMock(side_effect=results)

        resp = admin_client.get(ENDPOINT)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["users"] == expected_counts["users"]
        assert data["leaders"] == expected_counts["leaders"]
        assert data["gcs"] == expected_counts["gcs"]
        assert data["meetings"] == expected_counts["meetings"]
        assert data["medias"] == expected_counts["medias"]
        assert data["leader_contacts"] == expected_counts["leader_contacts"]
