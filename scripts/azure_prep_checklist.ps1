$ErrorActionPreference = "Stop"

Write-Host "ClosedLoop OS Azure prep checklist" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script does not create Azure resources." -ForegroundColor Yellow
Write-Host "It lists the Azure Portal tasks and values you need to collect." -ForegroundColor Yellow
Write-Host ""
Write-Host "Manual Azure Portal setup:" -ForegroundColor Green
Write-Host "  1. Create resource group: closedloop-os-rg"
Write-Host "  2. Create Cosmos DB account, database, and containers"
Write-Host "     - database: closedloop-os"
Write-Host "     - events partition key: /source_tool"
Write-Host "     - relationships partition key: /relationship_type"
Write-Host "  3. Create Key Vault and add connector secrets"
Write-Host "  4. Create Service Bus namespace and raw-events queue"
Write-Host "  5. Create Azure OpenAI account and model deployments"
Write-Host "  6. Create Azure AI Search service"
Write-Host "  7. Create Storage Account for Azure Functions"
Write-Host "  8. Create Python 3.11 Function App"
Write-Host "  9. Add Function App environment variables"
Write-Host " 10. Enable Function App managed identity"
Write-Host " 11. Grant identity Key Vault secret read access"
Write-Host " 12. Deploy code and verify /healthz"
Write-Host ""
Write-Host "Values to copy into Function App settings:" -ForegroundColor Green
Write-Host "  - COSMOS_ENDPOINT"
Write-Host "  - COSMOS_KEY"
Write-Host "  - SERVICE_BUS_CONNECTION_STRING"
Write-Host "  - KEY_VAULT_URI"
Write-Host "  - AZURE_OPENAI_ENDPOINT"
Write-Host "  - AZURE_OPENAI_API_KEY"
Write-Host "  - AZURE_SEARCH_ENDPOINT"
Write-Host "  - AZURE_SEARCH_API_KEY"
Write-Host ""
Write-Host "See AZURE_SETUP.md for the full manual portal guide." -ForegroundColor Green
