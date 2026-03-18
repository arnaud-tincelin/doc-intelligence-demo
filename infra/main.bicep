@minLength(1)
@maxLength(64)
@description('Name of the environment')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param backendContainerAppName string = ''
param storageAccountName string = ''
param documentIntelligenceName string = ''
param aiFoundryHubName string = ''
param aiFoundryProjectName string = ''
param containerAppEnvName string = ''
param containerRegistryName string = ''

@description('OpenAI model deployment name')
param openAiModelName string = 'gpt-4o'

@description('OpenAI model version')
param openAiModelVersion string = '2024-11-20'

@description('OpenAI deployment capacity')
param openAiDeploymentCapacity int = 10

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(resourceGroup().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    name: !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
    location: location
    tags: tags
  }
}

module documentIntelligence 'modules/document-intelligence.bicep' = {
  name: 'documentIntelligence'
  params: {
    name: !empty(documentIntelligenceName) ? documentIntelligenceName : '${abbrs.cognitiveServicesFormRecognizer}${resourceToken}'
    location: location
    tags: tags
  }
}

module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'aiFoundry'
  params: {
    hubName: !empty(aiFoundryHubName) ? aiFoundryHubName : '${abbrs.aiFoundryHub}${resourceToken}'
    projectName: !empty(aiFoundryProjectName) ? aiFoundryProjectName : '${abbrs.aiFoundryProject}${resourceToken}'
    location: location
    tags: tags
    storageAccountId: storage.outputs.id
    modelName: openAiModelName
    modelVersion: openAiModelVersion
    deploymentCapacity: openAiDeploymentCapacity
  }
}

module containerRegistry 'modules/container-registry.bicep' = {
  name: 'containerRegistry'
  params: {
    name: !empty(containerRegistryName) ? containerRegistryName : '${abbrs.containerRegistry}${resourceToken}'
    location: location
    tags: tags
  }
}

module containerAppEnv 'modules/container-app-environment.bicep' = {
  name: 'containerAppEnv'
  params: {
    name: !empty(containerAppEnvName) ? containerAppEnvName : '${abbrs.containerAppsEnvironment}${resourceToken}'
    location: location
    tags: tags
  }
}

module backend 'modules/container-app.bicep' = {
  name: 'backend'
  params: {
    name: !empty(backendContainerAppName) ? backendContainerAppName : '${abbrs.containerApps}backend-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'backend' })
    containerAppEnvId: containerAppEnv.outputs.id
    registryServer: containerRegistry.outputs.loginServer
    registryName: containerRegistry.outputs.name
    appSettings: {
      AZURE_STORAGE_ACCOUNT_NAME: storage.outputs.name
      AZURE_STORAGE_CONTAINER_NAME: storage.outputs.containerName
      AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: documentIntelligence.outputs.endpoint
      AZURE_AI_INFERENCE_ENDPOINT: aiFoundry.outputs.aiServicesEndpoint
      AZURE_AI_MODEL_DEPLOYMENT: aiFoundry.outputs.deploymentName
    }
  }
}

// Role assignments
module storageRoleBackend 'modules/role-assignment.bicep' = {
  name: 'storageRoleBackend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
  }
}

module docIntelligenceRoleBackend 'modules/role-assignment.bicep' = {
  name: 'docIntelligenceRoleBackend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User
    principalType: 'ServicePrincipal'
  }
}

module aiFoundryRoleBackend 'modules/role-assignment.bicep' = {
  name: 'aiFoundryRoleBackend'
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    principalType: 'ServicePrincipal'
  }
}

output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.name
output AZURE_STORAGE_CONTAINER_NAME string = storage.outputs.containerName
output AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT string = documentIntelligence.outputs.endpoint
output AZURE_AI_INFERENCE_ENDPOINT string = aiFoundry.outputs.aiServicesEndpoint
output AZURE_AI_MODEL_DEPLOYMENT string = aiFoundry.outputs.deploymentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
output BACKEND_URL string = backend.outputs.uri
