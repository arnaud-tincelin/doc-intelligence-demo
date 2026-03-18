@description('Name of the OpenAI resource')
param name string

@description('Location for the resource')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

@description('OpenAI model name')
param modelName string = 'gpt-4o'

@description('OpenAI model version')
param modelVersion string = '2024-11-20'

@description('Deployment capacity in TPM (thousands)')
param deploymentCapacity int = 10

resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
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

output endpoint string = openAi.properties.endpoint
output deploymentName string = modelName
output name string = openAi.name
output id string = openAi.id
