@description('Name of the storage account')
param name string

@description('Location for the storage account')
param location string = resourceGroup().location

@description('Tags for the storage account')
param tags object = {}

@description('Name of the blob container')
param containerName string = 'uploads'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }

  resource blobServices 'blobServices' = {
    name: 'default'

    resource container 'containers' = {
      name: containerName
      properties: {
        publicAccess: 'None'
      }
    }
  }
}

output name string = storageAccount.name
output containerName string = containerName
output id string = storageAccount.id
