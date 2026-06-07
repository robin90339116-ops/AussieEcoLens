# D group architecture notes

This diagram is a report-ready draft. The final team report can redraw it with
official AWS and GCP icons.

```mermaid
flowchart LR
    User["Frontend user"] --> FE["Frontend app"]
    FE --> APIGW["A API Gateway"]
    APIGW --> Auth["Cognito Authorizer"]

    APIGW --> Q3["D AWS Lambda Q3\nthumbnail lookup"]
    APIGW --> Q4["D AWS Lambda Q4\nquery file search"]
    APIGW --> Q5["D AWS Lambda Q5\nupdate tags"]
    APIGW --> Q6["D AWS Lambda Q6\ndelete file"]
    APIGW --> NotifyApi["D AWS Lambda\nnotifications API"]

    Q4 --> Oracle["B Oracle tagging endpoint\nprivate backend token"]
    Oracle --> Q4

    Q3 --> DB["DynamoDB files table"]
    Q4 --> DB
    Q5 --> DB
    Q6 --> DB
    Q6 --> S3["S3 original and thumbnail buckets"]
    Q3 --> SignedUrl["Presigned GET media URLs"]
    Q4 --> SignedUrl
    GCPQ1 --> SignedUrl
    GCPQ2 --> SignedUrl

    NotifyApi --> SNS["SNS topic"]
    SNS --> Email["Email subscribers"]
    NotifyApi --> SubDB["DynamoDB notifications_sub table"]

    FE -. optional direct protected HTTPS .-> GCPQ1["GCP Function Q1\nAND tag-count query"]
    FE -. optional direct protected HTTPS .-> GCPQ2["GCP Function Q2\nspecies query"]
    APIGW -. preferred route if proxied .-> GCPQ1
    APIGW -. preferred route if proxied .-> GCPQ2

    GCPQ1 --> GcpJwt["Cognito JWT verification"]
    GCPQ2 --> GcpJwt
    GCPQ1 --> DB
    GCPQ2 --> DB
```

Key boundaries:

- Frontend calls A API Gateway for the formal demo whenever possible.
- D AWS Lambdas are backend handlers behind A API Gateway and Cognito.
- B Oracle token stays private and is used only by backend code.
- GCP Q1/Q2 must verify Cognito JWTs when exposed directly.
- Q1/Q2/Q3/Q4 return short-lived presigned GET URLs for private S3 media.
- Query images for Q4 are not stored in S3 or DynamoDB.
- Notification subscribe saves SNS `subscription_arn`; unsubscribe updates SNS
  filter policy or calls SNS `unsubscribe`.
