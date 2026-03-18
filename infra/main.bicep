targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

param backendServiceName string = ''
param storageAccountName string = ''
param documentIntelligenceName string = ''
param openAiName string = ''
param appServicePlanName string = ''

@description('OpenAI model deployment name')
param openAiModelName string = 'gpt-4o'

@description('OpenAI model version')
param openAiModelVersion string = '2024-11-20'

@description('OpenAI deployment capacity')
param openAiDeploymentCapacity int = 10

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    name: !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
    location: location
    tags: tags
  }
}

module documentIntelligence 'modules/document-intelligence.bicep' = {
  name: 'documentIntelligence'
  scope: rg
  params: {
    name: !empty(documentIntelligenceName) ? documentIntelligenceName : '${abbrs.cognitiveServicesFormRecognizer}${resourceToken}'
    location: location
    tags: tags
  }
}

module openAi 'modules/openai.bicep' = {
  name: 'openAi'
  scope: rg
  params: {
    name: !empty(openAiName) ? openAiName : '${abbrs.cognitiveServicesOpenAI}${resourceToken}'
    location: location
    tags: tags
    modelName: openAiModelName
    modelVersion: openAiModelVersion
    deploymentCapacity: openAiDeploymentCapacity
  }
}

module appServicePlan 'modules/app-service-plan.bicep' = {
  name: 'appServicePlan'
  scope: rg
  params: {
    name: !empty(appServicePlanName) ? appServicePlanName : '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
  }
}

module backend 'modules/app-service.bicep' = {
  name: 'backend'
  scope: rg
  params: {
    name: !empty(backendServiceName) ? backendServiceName : '${abbrs.webSitesAppService}backend-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'backend' })
    appServicePlanId: appServicePlan.outputs.id
    runtimeName: 'python'
    runtimeVersion: '3.11'
    appSettings: {
      AZURE_STORAGE_ACCOUNT_NAME: storage.outputs.name
      AZURE_STORAGE_CONTAINER_NAME: storage.outputs.containerName
      AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: documentIntelligence.outputs.endpoint
      AZURE_OPENAI_ENDPOINT: openAi.outputs.endpoint
      AZURE_OPENAI_DEPLOYMENT_NAME: openAi.outputs.deploymentName
      SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
    }
  }
}

// Role assignments
module storageRoleBackend 'modules/role-assignment.bicep' = {
  name: 'storageRoleBackend'
  scope: rg
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    principalType: 'ServicePrincipal'
  }
}

module docIntelligenceRoleBackend 'modules/role-assignment.bicep' = {
  name: 'docIntelligenceRoleBackend'
  scope: rg
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908' // Cognitive Services User
    principalType: 'ServicePrincipal'
  }
}

module openAiRoleBackend 'modules/role-assignment.bicep' = {
  name: 'openAiRoleBackend'
  scope: rg
  params: {
    principalId: backend.outputs.identityPrincipalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    principalType: 'ServicePrincipal'
  }
}

output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.name
output AZURE_STORAGE_CONTAINER_NAME string = storage.outputs.containerName
output AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT string = documentIntelligence.outputs.endpoint
output AZURE_OPENAI_ENDPOINT string = openAi.outputs.endpoint
output AZURE_OPENAI_DEPLOYMENT_NAME string = openAi.outputs.deploymentName
output BACKEND_URL string = backend.outputs.uri
