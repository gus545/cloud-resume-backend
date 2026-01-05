# Cloud Resume Backend

Serverless visitor counter API for my cloud resume.

## Architecture
- API Gateway → Lambda (Python) → DynamoDB
- Deployed via SAM (template.yml)

## What it does
Increments and returns a visitor count each time the resume is loaded.

## Files
- `counter.py` - Lambda function
- `test_counter.py` - Unit tests
- `template.yml` - SAM template for deployment
- `requirements.txt` - Dependencies

## Deployment
`sam build && sam deploy`
