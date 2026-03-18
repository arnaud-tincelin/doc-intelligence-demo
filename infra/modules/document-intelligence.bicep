@description('Name of the Document Intelligence resource')
param name string

@description('Location for the resource')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  tags: tags
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
  }
}

output endpoint string = documentIntelligence.properties.endpoint
output name string = documentIntelligence.name
output id string = documentIntelligence.id
