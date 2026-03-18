@description('Name of the App Service')
param name string

@description('Location for the resource')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

@description('App Service Plan ID')
param appServicePlanId string

@description('Runtime name')
param runtimeName string = 'python'

@description('Runtime version')
param runtimeVersion string = '3.11'

@description('App settings')
param appSettings object = {}

var appSettingsArray = [for key in objectKeys(appSettings): {
  name: key
  value: appSettings[key]
}]

resource appService 'Microsoft.Web/sites@2023-12-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlanId
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: '${toUpper(runtimeName)}|${runtimeVersion}'
      appSettings: appSettingsArray
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
  }
}

output uri string = 'https://${appService.properties.defaultHostName}'
output name string = appService.name
output identityPrincipalId string = appService.identity.principalId
