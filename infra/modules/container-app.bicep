@description('Name of the Container App')
param name string

@description('Location for the resource')
param location string = resourceGroup().location

@description('Tags for the resource')
param tags object = {}

@description('Container App Environment ID')
param containerAppEnvId string

@description('Container image to deploy')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('App settings as environment variables')
param appSettings object = {}

@description('Target port for ingress')
param targetPort int = 8000

var envVars = [for key in objectKeys(appSettings): {
  name: key
  value: appSettings[key]
}]

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppEnvId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: name
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: envVars
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-rule'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

output uri string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output name string = containerApp.name
output identityPrincipalId string = containerApp.identity.principalId
