"""Testes de validação dos campos de endereço no GcUpdate."""

import pytest
from pydantic import ValidationError

from app.schemas.gc import GcUpdate

# Campos obrigatórios quando qualquer campo de endereço é enviado
ADDRESS_FIELDS = {
    "zip_code": "13201-000",
    "street": "Rua Barão de Jundiaí",
    "neighborhood": "Centro",
    "city": "Jundiaí",
    "state": "SP",
}


class TestGcUpdateAddressValidation:
    """Valida que ao enviar qualquer campo de endereço, todos são obrigatórios."""

    def test_update_without_address_fields(self):
        """Atualizar apenas o nome deve funcionar sem campos de endereço."""
        data = GcUpdate(name="Novo nome")
        assert data.name == "Novo nome"
        assert data.zip_code is None

    def test_update_with_all_address_fields(self):
        """Enviar todos os campos de endereço deve passar na validação."""
        data = GcUpdate(**ADDRESS_FIELDS)
        assert data.zip_code == "13201-000"
        assert data.street == "Rua Barão de Jundiaí"
        assert data.neighborhood == "Centro"
        assert data.city == "Jundiaí"
        assert data.state == "SP"

    def test_update_with_all_address_fields_and_other_fields(self):
        """Enviar todos os campos de endereço junto com outros campos deve funcionar."""
        data = GcUpdate(name="GC Atualizado", description="Nova descrição", **ADDRESS_FIELDS)
        assert data.name == "GC Atualizado"
        assert data.zip_code == "13201-000"

    @pytest.mark.parametrize("missing_field", ADDRESS_FIELDS.keys())
    def test_update_missing_one_address_field(self, missing_field: str):
        """Enviar campos de endereço incompletos deve falhar."""
        partial = {k: v for k, v in ADDRESS_FIELDS.items() if k != missing_field}
        with pytest.raises(ValidationError, match="obrigatórios"):
            GcUpdate(**partial)

    def test_update_with_only_zip_code(self):
        """Enviar apenas o CEP sem os outros campos deve falhar."""
        with pytest.raises(ValidationError, match="obrigatórios"):
            GcUpdate(zip_code="13201-000")

    def test_update_with_only_city_and_state(self):
        """Enviar apenas cidade e estado sem os outros campos deve falhar."""
        with pytest.raises(ValidationError, match="obrigatórios"):
            GcUpdate(city="Jundiaí", state="SP")

    def test_update_with_no_fields(self):
        """Enviar payload vazio deve funcionar (nenhum campo alterado)."""
        data = GcUpdate()
        assert data.name is None
        assert data.zip_code is None

    def test_update_number_without_address_fields_should_pass(self):
        """Enviar apenas 'number' não exige os campos de endereço (não faz parte do grupo)."""
        data = GcUpdate(number="123")
        assert data.number == "123"

    def test_update_complement_without_address_fields_should_pass(self):
        """Enviar apenas 'complement' não exige os campos de endereço."""
        data = GcUpdate(complement="Apto 12")
        assert data.complement == "Apto 12"

    def test_update_address_fields_with_number_and_complement(self):
        """Enviar todos os campos de endereço + number e complement deve funcionar."""
        data = GcUpdate(number="500", complement="Bloco A", **ADDRESS_FIELDS)
        assert data.number == "500"
        assert data.complement == "Bloco A"
        assert data.zip_code == "13201-000"

    def test_error_message_lists_missing_fields(self):
        """A mensagem de erro deve listar os campos que faltam."""
        with pytest.raises(ValidationError) as exc_info:
            GcUpdate(zip_code="13201-000", street="Rua X")
        error_msg = str(exc_info.value)
        assert "city" in error_msg
        assert "neighborhood" in error_msg
        assert "state" in error_msg
