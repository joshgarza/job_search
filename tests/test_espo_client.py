import pytest
import respx
from httpx import Response


@pytest.fixture
def espo_client(espo_config):
    from src.espo_client import EspoClient

    return EspoClient(**espo_config)


class TestEspoClientAuth:
    def test_client_initialization(self, espo_config):
        from src.espo_client import EspoClient

        client = EspoClient(**espo_config)
        assert client.base_url == espo_config["base_url"]


class TestAccountOperations:
    @respx.mock
    def test_find_account_exists(self, espo_client):
        """find_account returns dict when account exists"""
        respx.get("http://192.168.68.68:8080/api/v1/Account").mock(
            return_value=Response(
                200, json={"total": 1, "list": [{"id": "abc123", "name": "Acme Corp"}]}
            )
        )
        result = espo_client.find_account("Acme Corp")
        assert result is not None
        assert result["id"] == "abc123"

    @respx.mock
    def test_find_account_not_exists(self, espo_client):
        """find_account returns None when account doesn't exist"""
        respx.get("http://192.168.68.68:8080/api/v1/Account").mock(
            return_value=Response(200, json={"total": 0, "list": []})
        )
        result = espo_client.find_account("Nonexistent")
        assert result is None

    @respx.mock
    def test_create_account(self, espo_client):
        """create_account returns new account ID"""
        from src.models import Company

        respx.post("http://192.168.68.68:8080/api/v1/Account").mock(
            return_value=Response(200, json={"id": "new123"})
        )
        company = Company(name="New Corp", website="https://new.com")
        result = espo_client.create_account(company)
        assert result == "new123"


class TestContactOperations:
    @respx.mock
    def test_create_contact_with_cold_status(self, espo_client):
        """create_contact sets cStatus=Cold and cRelationshipStrength=1/10"""
        from src.models import Person
        import json

        route = respx.post("http://192.168.68.68:8080/api/v1/Contact").mock(
            return_value=Response(200, json={"id": "contact123"})
        )
        person = Person(
            first_name="John",
            last_name="Doe",
            title="Engineer",
            source_url="https://hn.com/123",
        )
        result = espo_client.create_contact(person, account_id="acc123")
        assert result == "contact123"

        # Verify request body included Cold status
        request_body = json.loads(route.calls[0].request.content)
        assert request_body["cStatus"] == "Cold"
        assert request_body["cRelationshipStrength"] == "1/10"
