import json
import sys
from unittest.mock import patch, MagicMock

import pytest
from botocore.exceptions import ClientError

# Mock boto3 before importing counter module
mock_dynamodb = MagicMock()
mock_table = MagicMock()
mock_dynamodb.Table.return_value = mock_table

with patch.dict(sys.modules, {"boto3": MagicMock()}):
    with patch("boto3.resource", return_value=mock_dynamodb):
        from counter import lambda_handler


@pytest.fixture(autouse=True)
def reset_mock_table():
    """Reset the mock DynamoDB table before each test."""
    mock_table.reset_mock(side_effect=True, return_value=True)
    yield mock_table


class TestLambdaHandler:
    """Tests for the lambda_handler function."""

    def test_default_path_becomes_index_html(self):
        """Test that default/root path becomes /index.html."""
        mock_table.update_item.return_value = {"Attributes": {"visit_count": 1}}

        event = {"body": "{}"}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["path"] == "/index.html"
        assert body["visit_count"] == 1

    def test_root_path_becomes_index_html(self):
        """Test that '/' path is converted to /index.html."""
        mock_table.update_item.return_value = {"Attributes": {"visit_count": 1}}

        event = {"body": json.dumps({"path": "/"})}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["path"] == "/index.html"

    def test_custom_path(self):
        """Test with a custom path."""
        mock_table.update_item.return_value = {"Attributes": {"visit_count": 5}}

        event = {"body": json.dumps({"path": "/about"})}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["path"] == "/about"
        assert body["visit_count"] == 5

    def test_body_as_dict(self):
        """Test when body is already a dict (not JSON string)."""
        mock_table.update_item.return_value = {"Attributes": {"visit_count": 3}}

        event = {"body": {"path": "/contact"}}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["path"] == "/contact"
        assert body["visit_count"] == 3

    def test_missing_body_uses_default(self):
        """Test with no body in event uses default path."""
        mock_table.update_item.return_value = {"Attributes": {"visit_count": 1}}

        event = {}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["path"] == "/index.html"

    def test_empty_path_returns_400(self):
        """Test that empty string path returns 400 error."""
        event = {"body": json.dumps({"path": ""})}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Missing path parameter"

    def test_cors_headers_present(self):
        """Test that CORS headers are present in response."""
        mock_table.update_item.return_value = {"Attributes": {"visit_count": 1}}

        event = {"body": "{}"}
        response = lambda_handler(event, None)

        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert response["headers"]["Content-Type"] == "application/json"

    def test_dynamodb_client_error(self):
        """Test DynamoDB ClientError handling."""
        mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "DynamoDB error"}}, "UpdateItem"
        )

        event = {"body": json.dumps({"path": "/test"})}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body

    def test_generic_exception_handling(self):
        """Test generic exception handling."""
        mock_table.update_item.side_effect = Exception("Unexpected error")

        event = {"body": json.dumps({"path": "/test"})}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body
        assert "Unexpected error" in body["error"]

    def test_dynamodb_update_item_called_correctly(self):
        """Test that DynamoDB update_item is called with correct parameters."""
        mock_table.update_item.return_value = {"Attributes": {"visit_count": 1}}

        event = {"body": json.dumps({"path": "/projects"})}
        lambda_handler(event, None)

        mock_table.update_item.assert_called_once_with(
            Key={"path": "/projects"},
            UpdateExpression="SET visit_count = if_not_exists(visit_count, :start) + :inc",
            ExpressionAttributeValues={":inc": 1, ":start": 0},
            ReturnValues="UPDATED_NEW",
        )

    def test_visit_count_returned_as_int(self):
        """Test that visit_count is returned as an integer."""
        from decimal import Decimal

        # DynamoDB returns Decimal type
        mock_table.update_item.return_value = {"Attributes": {"visit_count": Decimal("42")}}

        event = {"body": json.dumps({"path": "/test"})}
        response = lambda_handler(event, None)

        body = json.loads(response["body"])
        assert body["visit_count"] == 42
        assert isinstance(body["visit_count"], int)

    def test_json_body_parsing(self):
        """Test JSON body string is correctly parsed."""
        mock_table.update_item.return_value = {"Attributes": {"visit_count": 1}}

        event = {"body": '{"path": "/blog/post-1"}'}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["path"] == "/blog/post-1"

    def test_nested_path(self):
        """Test with a deeply nested path."""
        mock_table.update_item.return_value = {"Attributes": {"visit_count": 10}}

        event = {"body": json.dumps({"path": "/blog/2024/01/my-post"})}
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["path"] == "/blog/2024/01/my-post"
        assert body["visit_count"] == 10
