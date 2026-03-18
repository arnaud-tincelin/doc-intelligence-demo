@description('Name of the AI Foundry hub')
param hubName string

@description('Name of the AI Foundry project')
param projectName string

@description('Location for the resource')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

@description('Storage account ID for the hub')
param storageAccountId string

@description('OpenAI model name')
param modelName string = 'gpt-4o'

@description('OpenAI model version')
param modelVersion string = '2024-11-20'

@description('Deployment capacity in TPM (thousands)')
param deploymentCapacity int = 10

// AI Services account (hosts the model deployments)
resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${hubName}-aiservices'
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: '${hubName}-aiservices'
    publicNetworkAccess: 'Enabled'
  }

  resource deployment 'deployments' = {
    name: modelName
    sku: {
      name: 'Standard'
      capacity: deploymentCapacity
    }
    properties: {
      model: {
        format: 'OpenAI'
        name: modelName
        version: modelVersion
      }
    }
  }
}

// AI Foundry Hub
resource hub 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: hubName
  location: location
  tags: tags
  kind: 'Hub'
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: hubName
    storageAccount: storageAccountId
    publicNetworkAccess: 'Enabled'
  }
}

// Connect AI Services to the hub
resource aiServicesConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-10-01' = {
  parent: hub
  name: 'aiservices-connection'
  properties: {
    category: 'AIServices'
    authType: 'AAD'
    isSharedToAll: true
    target: aiServices.properties.endpoint
    metadata: {
      ApiType: 'Azure'
      ResourceId: aiServices.id
    }
  }
}

// AI Foundry Project
resource project 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: projectName
  location: location
  tags: tags
  kind: 'Project'
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: projectName
    hubResourceId: hub.id
    publicNetworkAccess: 'Enabled'
  }
  dependsOn: [
    aiServicesConnection
  ]
}

output aiServicesEndpoint string = aiServices.properties.endpoint
output aiServicesName string = aiServices.name
output aiServicesId string = aiServices.id
output deploymentName string = modelName
output hubName string = hub.name
output hubPrincipalId string = hub.identity.principalId
output projectName string = project.name
output projectId string = project.id
