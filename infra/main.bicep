targetScope = 'subscription'

@description('Azure region for all ClosedLoop OS resources.')
param location string = 'eastus'

@description('Resource group name.')
param resourceGroupName string = 'closedloop-os-rg'

@description('Cosmos DB account name.')
param cosmosAccountName string = 'closedloop-events'

@description('Cosmos DB SQL database name. Assumption: required because the request specified the container but not the database.')
param cosmosDatabaseName string = 'closedloop-os'

@description('Cosmos DB container name.')
param cosmosContainerName string = 'events'

@description('Key Vault name.')
param keyVaultName string = 'closedloop-secrets'

@description('Service Bus namespace name.')
param serviceBusNamespaceName string = 'closedloop-bus'

@description('Service Bus queue name.')
param serviceBusQueueName string = 'raw-events'

@description('Container Apps environment name.')
param containerAppsEnvironmentName string = 'closedloop-env'

@description('Azure OpenAI account name.')
param azureOpenAIAccountName string = 'closedloop-openai'

@description('Azure OpenAI deployment name for classification.')
param azureOpenAIDeploymentName string = 'gpt-4o-mini'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
}

module closedloop './modules/closedloop-resources.bicep' = {
  name: 'closedloop-phase1'
  scope: rg
  params: {
    location: location
    cosmosAccountName: cosmosAccountName
    cosmosDatabaseName: cosmosDatabaseName
    cosmosContainerName: cosmosContainerName
    keyVaultName: keyVaultName
    serviceBusNamespaceName: serviceBusNamespaceName
    serviceBusQueueName: serviceBusQueueName
    containerAppsEnvironmentName: containerAppsEnvironmentName
    azureOpenAIAccountName: azureOpenAIAccountName
    azureOpenAIDeploymentName: azureOpenAIDeploymentName
  }
}

output resourceGroup string = rg.name
output cosmosEndpoint string = closedloop.outputs.cosmosEndpoint
output keyVaultUri string = closedloop.outputs.keyVaultUri
output serviceBusNamespace string = closedloop.outputs.serviceBusNamespace
output azureOpenAIEndpoint string = closedloop.outputs.azureOpenAIEndpoint
