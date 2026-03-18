@description('Name of the Container App Environment')
param name string

@description('Location for the resource')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    zoneRedundant: false
  }
}

output id string = containerAppEnv.id
output name string = containerAppEnv.name
