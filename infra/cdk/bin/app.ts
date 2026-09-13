#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { devConfig } from "../lib/config/dev-config";
import { AuthenticationStack } from "../lib/stacks/authentication-stack";
import { ContainerRegistryStack } from "../lib/stacks/container-registry-stack";
import { DatabaseStack } from "../lib/stacks/database-stack";
import { NetworkStack } from "../lib/stacks/network-stack";
import { StorageStack } from "../lib/stacks/storage-stack";

const app = new cdk.App();

new AuthenticationStack(app, "DevAuthenticationStack", {
  applicationName: devConfig.applicationName,
  customerOAuthCallbackUrls: devConfig.customerOAuthCallbackUrls,
  customerOAuthLogoutUrls: devConfig.customerOAuthLogoutUrls,
  customerUserPoolDomainPrefix: devConfig.customerUserPoolDomainPrefix,
  environmentName: devConfig.environmentName,
  env: {
    region: devConfig.region,
  },
  removalPolicy: devConfig.authenticationRemovalPolicy,
  staffOAuthCallbackUrls: devConfig.staffOAuthCallbackUrls,
  staffOAuthLogoutUrls: devConfig.staffOAuthLogoutUrls,
  staffUserPoolDomainPrefix: devConfig.staffUserPoolDomainPrefix,
  systemAdminOAuthCallbackUrls: devConfig.systemAdminOAuthCallbackUrls,
  systemAdminOAuthLogoutUrls: devConfig.systemAdminOAuthLogoutUrls,
  systemAdminUserPoolDomainPrefix: devConfig.systemAdminUserPoolDomainPrefix,
  userPoolDeletionProtection:
    devConfig.authenticationUserPoolDeletionProtection,
});

new ContainerRegistryStack(app, "DevContainerRegistryStack", {
  applicationName: devConfig.applicationName,
  environmentName: devConfig.environmentName,
  env: {
    region: devConfig.region,
  },
});

const networkStack = new NetworkStack(app, "DevNetworkStack", {
  env: {
    region: devConfig.region,
  },
  applicationName: devConfig.applicationName,
  environmentName: devConfig.environmentName,
  vpcCidr: devConfig.vpcCidr,
  publicSubnets: devConfig.publicSubnets,
  privateIngressSubnets: devConfig.privateIngressSubnets,
  applicationSubnets: devConfig.applicationSubnets,
  databaseSubnets: devConfig.databaseSubnets,
});

new DatabaseStack(app, "DevDatabaseStack", {
  applicationName: devConfig.applicationName,
  databaseAllocatedStorage: devConfig.databaseAllocatedStorage,
  databaseAutoMinorVersionUpgrade: devConfig.databaseAutoMinorVersionUpgrade,
  databaseBackupRetentionPeriod: devConfig.databaseBackupRetentionPeriod,
  databaseDeletionProtection: devConfig.databaseDeletionProtection,
  databaseEngineVersion: devConfig.databaseEngineVersion,
  databaseInstanceClass: devConfig.databaseInstanceClass,
  databaseMaxAllocatedStorage: devConfig.databaseMaxAllocatedStorage,
  databaseMultiAz: devConfig.databaseMultiAz,
  databasePreferredBackupWindow: devConfig.databasePreferredBackupWindow,
  databasePreferredMaintenanceWindow:
    devConfig.databasePreferredMaintenanceWindow,
  databaseRemovalPolicy: devConfig.databaseRemovalPolicy,
  databaseSubnetIds: networkStack.databaseSubnetIds,
  databaseStorageType: devConfig.databaseStorageType,
  env: {
    region: devConfig.region,
  },
  environmentName: devConfig.environmentName,
  rdsSecurityGroup: networkStack.rdsSecurityGroup,
});

new StorageStack(app, "DevStorageStack", {
  applicationName: devConfig.applicationName,
  environmentName: devConfig.environmentName,
  env: {
    region: devConfig.region,
  },
  frontendBucketAutoDeleteObjects:
    devConfig.frontendBucketAutoDeleteObjects,
  frontendBucketRemovalPolicy: devConfig.frontendBucketRemovalPolicy,
  frontendBucketVersioned: devConfig.frontendBucketVersioned,
});

app.synth();
