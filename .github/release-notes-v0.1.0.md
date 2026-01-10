# v0.1.0 - Initial Production Release

## 🚀 Deployment

**Frontend**: https://dedwt6o9pc0lp.cloudfront.net  
**Backend API**: https://jlht5nxlh8.execute-api.us-east-1.amazonaws.com  
**API Docs**: https://jlht5nxlh8.execute-api.us-east-1.amazonaws.com/docs

## ✨ Features

### Backend Infrastructure
- **AWS Lambda** with container image deployment (Python 3.11)
- **API Gateway** HTTP API with FastAPI
- **DynamoDB** persistence for transactions, audit trails, and HITL cases
- **S3** input bucket for data ingestion
- **CloudWatch** logging and alarms with X-Ray tracing
- **Systems Manager Parameter Store** for secure OpenAI API key storage

### Multi-Agent System
- **Data Analysis Agent**: Extracts signals and metrics from transaction data
- **Policy RAG Agent**: Retrieves relevant fraud policies using vector search
- **Risk Evaluation Agent**: Assesses fraud risk with policy guidance
- **Web Research Agent**: Searches allowlisted domains for fraud patterns
- **Decision Agent**: Makes final fraud determination with explanations
- **HITL Escalation**: Routes complex cases to human review

### Vector Search (RAG)
- **ChromaDB** vector store with HNSW algorithm
- **Cosine similarity** search for policy retrieval
- **SQLite compatibility shim** for Lambda environment (pysqlite3-binary)
- Embeddings stored in Lambda `/tmp/` (ephemeral, fast queries)

### Frontend
- **React 18** with TypeScript and Vite
- **Material-UI** components
- **CloudFront + S3** hosting with global CDN
- Transaction list, analysis view, audit trails, and HITL dashboard

### Security & Operations
- OpenAI API key encrypted in Parameter Store (KMS)
- Runtime key fetch from SSM in Lambda
- IAM least-privilege policies
- Structured logging with transaction correlation
- Health check and metrics endpoints

## 📁 Repository Structure

```
├── backend/
│   ├── backend-infrastructure.yaml    # SAM CloudFormation template
│   ├── samconfig.toml                 # SAM CLI configuration
│   ├── Dockerfile                     # Lambda container image
│   ├── app/
│   │   ├── agents/                    # Multi-agent implementations
│   │   ├── rag/                       # Vector store and embeddings
│   │   ├── orchestration/             # LangGraph workflow
│   │   └── api/                       # FastAPI routes
│   └── requirements.txt
├── frontend/
│   ├── frontend-infrastructure.yaml   # CloudFormation for S3 + CloudFront
│   ├── src/                           # React application
│   └── deploy-frontend.sh
├── data/
│   ├── transactions.csv
│   ├── customer_behavior.csv
│   └── fraud_policies.json
└── docs/
    └── architecture/
        └── aws-architecture.png       # AWS architecture diagram
```

## 🔧 Configuration

### Backend Environment
- `APP_ENV=aws`
- `STORAGE_BACKEND=dynamodb`
- `EMBEDDINGS_PROVIDER=mock` (or `openai` with API key)
- `LLM_PROVIDER=mock` (or `openai`)
- `OPENAI_KEY_PARAMETER_NAME=/fraud-detection/openai-api-key`

### Frontend Environment
- `VITE_API_BASE_URL=https://jlht5nxlh8.execute-api.us-east-1.amazonaws.com`

## 📊 Cost Estimate

Estimated monthly cost for 1,000 transactions/day: **~$7-10/month**
- Lambda: ~$2-3 (with free tier)
- DynamoDB: ~$1-2 (on-demand pricing)
- API Gateway: ~$1
- CloudFront: ~$1-2
- S3: <$1

## 🎯 Status

**Production deployment verified and operational** ✅
- All endpoints responding
- Frontend connected to backend
- DynamoDB persistence working
- Vector search operational
- CloudWatch monitoring active

## 📝 Known Limitations

- Vector store rebuilt on Lambda cold starts (~2-5 sec)
- Mock providers by default (OpenAI requires API key setup)
- Single AWS region deployment (us-east-1)

## 🔜 Future Enhancements

- Amazon EFS for persistent vector storage
- Amazon OpenSearch Serverless for vector search
- Multi-region deployment
- Enhanced HITL workflow UI
- Real-time fraud detection webhooks
