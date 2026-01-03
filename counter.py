import json
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("visitor-counts")


def lambda_handler(event, context):
    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)

    try:
        path = body.get("path", "/")

        if not path:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing path parameter"}),
            }
        if path == "/":
            path = "/index.html"
        response = table.update_item(
            Key={"path": path},
            UpdateExpression="SET visit_count = if_not_exists(visit_count, :start) + :inc",
            ExpressionAttributeValues={":inc": 1, ":start": 0},
            ReturnValues="UPDATED_NEW",
        )

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json",
            },
            "body": json.dumps(
                {
                    "path": path,
                    "visit_count": int(response["Attributes"]["visit_count"]),
                }
            ),
        }

    except ClientError as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
